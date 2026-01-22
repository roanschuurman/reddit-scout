"""Hacker News scanner service."""

import logging
import re
from dataclasses import dataclass

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from community_scout.hn.client import HNClient, HNItemData
from community_scout.models import (
    AlertStatus,
    ContentSource,
    HNItem,
    UserAlert,
    UserKeyword,
)
from community_scout.scanner.state import get_scanner_state, update_scanner_state

logger = logging.getLogger(__name__)

SOURCE_NAME = "hackernews"
BATCH_SIZE = 50


@dataclass
class ScanResult:
    """Result of a scan operation."""

    items_scanned: int
    items_stored: int
    alerts_created: int
    last_seen_id: int


def match_keywords(text: str | None, keywords: list[str]) -> list[str]:
    """Match keywords against text.

    For single words, uses word boundaries to avoid partial matches.
    For phrases (containing spaces), uses substring matching.

    Args:
        text: Text to search in
        keywords: List of keywords/phrases to match

    Returns:
        List of matched keywords
    """
    if not text:
        return []

    text_lower = text.lower()
    matches: list[str] = []

    for keyword in keywords:
        keyword_lower = keyword.lower()
        if " " in keyword:
            # Phrase: use substring match
            if keyword_lower in text_lower:
                matches.append(keyword)
        else:
            # Single word: use word boundary
            pattern = rf"\b{re.escape(keyword_lower)}\b"
            if re.search(pattern, text_lower):
                matches.append(keyword)

    return matches


def get_searchable_text(item: HNItemData) -> str:
    """Get all searchable text from an item.

    For stories: title + text + url
    For comments: text only

    Args:
        item: HN item data

    Returns:
        Combined searchable text
    """
    parts: list[str] = []
    if item.title:
        parts.append(item.title)
    if item.text:
        parts.append(item.text)
    if item.url:
        parts.append(item.url)
    return " ".join(parts)


class HNScanner:
    """Scanner service for Hacker News content."""

    def __init__(self, session: AsyncSession, hn_client: HNClient) -> None:
        """Initialize the scanner.

        Args:
            session: Database session
            hn_client: HN API client
        """
        self.session = session
        self.hn_client = hn_client
        self._content_source: ContentSource | None = None

    async def get_content_source(self) -> ContentSource:
        """Get or create the hackernews content source."""
        if self._content_source is not None:
            return self._content_source

        stmt = select(ContentSource).where(ContentSource.name == SOURCE_NAME)
        result = await self.session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            source = ContentSource(name=SOURCE_NAME, is_active=True)
            self.session.add(source)
            await self.session.flush()

        self._content_source = source
        return source

    async def get_active_keywords(self) -> dict[str, list[tuple[int, int]]]:
        """Get all active keywords grouped by phrase.

        Returns:
            Dict mapping keyword phrase to list of (keyword_id, user_id) tuples
        """
        stmt = select(UserKeyword).where(UserKeyword.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        keywords = result.scalars().all()

        keyword_map: dict[str, list[tuple[int, int]]] = {}
        for kw in keywords:
            phrase = kw.phrase.lower()
            if phrase not in keyword_map:
                keyword_map[phrase] = []
            keyword_map[phrase].append((kw.id, kw.user_id))

        return keyword_map

    async def store_item(self, item: HNItemData) -> HNItem:
        """Store an HN item in the database.

        Args:
            item: Item data from API

        Returns:
            Stored HNItem model
        """
        # Check if item already exists
        stmt = select(HNItem).where(HNItem.hn_id == item.id)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        hn_item = HNItem(
            hn_id=item.id,
            item_type=item.item_type,
            title=item.title,
            text=item.text,
            url=item.url,
            author=item.author,
            score=item.score,
            parent_id=item.parent_id,
            created_utc=item.created_at,
        )
        self.session.add(hn_item)
        await self.session.flush()
        return hn_item

    async def alert_exists(
        self, user_id: int, item_id: int, keyword_id: int
    ) -> bool:
        """Check if an alert already exists for this user/item/keyword combo."""
        stmt = select(UserAlert).where(
            and_(
                UserAlert.user_id == user_id,
                UserAlert.item_id == item_id,
                UserAlert.keyword_id == keyword_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_alert(
        self,
        user_id: int,
        hn_item: HNItem,
        keyword_id: int,
        source: ContentSource,
    ) -> UserAlert | None:
        """Create an alert for a matched keyword.

        Returns None if alert already exists.
        """
        # Check for duplicate
        if await self.alert_exists(user_id, hn_item.id, keyword_id):
            return None

        alert = UserAlert(
            user_id=user_id,
            item_id=hn_item.id,
            keyword_id=keyword_id,
            source_id=source.id,
            status=AlertStatus.PENDING.value,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def process_item(
        self,
        item: HNItemData,
        keyword_map: dict[str, list[tuple[int, int]]],
        source: ContentSource,
    ) -> tuple[HNItem, int]:
        """Process a single item: store it and create alerts for matches.

        Args:
            item: HN item data
            keyword_map: Mapping of keyword phrases to (keyword_id, user_id) tuples
            source: Content source record

        Returns:
            Tuple of (stored HNItem, number of alerts created)
        """
        # Store the item
        hn_item = await self.store_item(item)

        # Get searchable text
        text = get_searchable_text(item)
        if not text:
            return hn_item, 0

        # Match keywords
        all_keywords = list(keyword_map.keys())
        matched_keywords = match_keywords(text, all_keywords)

        alerts_created = 0
        for matched_keyword in matched_keywords:
            # Create alert for each user monitoring this keyword
            for keyword_id, user_id in keyword_map[matched_keyword.lower()]:
                alert = await self.create_alert(user_id, hn_item, keyword_id, source)
                if alert is not None:
                    alerts_created += 1
                    logger.info(
                        "Alert created: user=%d keyword=%s item=%d",
                        user_id,
                        matched_keyword,
                        item.id,
                    )

        return hn_item, alerts_created

    async def scan(self, initial_lookback: int = 100) -> ScanResult:
        """Run a scan for new HN items.

        Args:
            initial_lookback: Number of items to look back on first scan

        Returns:
            ScanResult with statistics
        """
        # Get scanner state
        state = await get_scanner_state(self.session, SOURCE_NAME)
        last_seen_id = state.last_seen_id

        # Get max item ID from HN
        max_item_id = await self.hn_client.get_max_item_id()
        logger.info("HN max item ID: %d, last seen: %d", max_item_id, last_seen_id)

        # On first scan, start from max_id - initial_lookback
        if last_seen_id == 0:
            start_id = max(1, max_item_id - initial_lookback)
            logger.info("First scan, starting from ID %d", start_id)
        else:
            start_id = last_seen_id + 1

        if start_id > max_item_id:
            logger.info("No new items to scan")
            return ScanResult(
                items_scanned=0,
                items_stored=0,
                alerts_created=0,
                last_seen_id=last_seen_id,
            )

        # Get active keywords
        keyword_map = await self.get_active_keywords()
        if not keyword_map:
            logger.warning("No active keywords configured, updating state only")
            await update_scanner_state(self.session, SOURCE_NAME, max_item_id)
            return ScanResult(
                items_scanned=0,
                items_stored=0,
                alerts_created=0,
                last_seen_id=max_item_id,
            )

        logger.info(
            "Scanning items %d to %d with %d keywords",
            start_id,
            max_item_id,
            len(keyword_map),
        )

        # Get content source
        source = await self.get_content_source()

        total_scanned = 0
        total_stored = 0
        total_alerts = 0

        # Process in batches
        current_id = start_id
        while current_id <= max_item_id:
            batch_end = min(current_id + BATCH_SIZE, max_item_id + 1)
            batch_ids = list(range(current_id, batch_end))

            logger.debug("Fetching batch: %d to %d", current_id, batch_end - 1)
            items = await self.hn_client.get_items_batch(batch_ids)

            for item in items:
                hn_item, alerts = await self.process_item(item, keyword_map, source)
                total_stored += 1
                total_alerts += alerts

            total_scanned += len(batch_ids)
            current_id = batch_end

            # Update state after each batch
            await update_scanner_state(self.session, SOURCE_NAME, batch_end - 1)
            await self.session.commit()

        logger.info(
            "Scan complete: scanned=%d stored=%d alerts=%d",
            total_scanned,
            total_stored,
            total_alerts,
        )

        return ScanResult(
            items_scanned=total_scanned,
            items_stored=total_stored,
            alerts_created=total_alerts,
            last_seen_id=max_item_id,
        )
