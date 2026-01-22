"""Hacker News API client."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)

HN_API_BASE_URL = "https://hacker-news.firebaseio.com/v0"


@dataclass
class HNItemData:
    """Parsed Hacker News item data."""

    id: int
    item_type: str
    title: str | None
    text: str | None
    url: str | None
    author: str
    score: int
    parent_id: int | None
    created_at: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, object]) -> "HNItemData | None":
        """Create HNItemData from API response.

        Returns None if the item is deleted, dead, or not a story/comment.
        """
        # Skip deleted or dead items
        if data.get("deleted") or data.get("dead"):
            return None

        item_type = data.get("type")
        if item_type not in ("story", "comment"):
            return None

        # Extract required fields with safe defaults
        item_id = data.get("id")
        author = data.get("by")
        time_val = data.get("time")

        if not isinstance(item_id, int) or not author or not time_val:
            return None

        score_val = data.get("score", 0)
        parent_val = data.get("parent")

        return cls(
            id=item_id,
            item_type=str(item_type),
            title=str(data["title"]) if data.get("title") else None,
            text=str(data["text"]) if data.get("text") else None,
            url=str(data["url"]) if data.get("url") else None,
            author=str(author),
            score=int(str(score_val)) if score_val else 0,
            parent_id=int(str(parent_val)) if parent_val else None,
            created_at=datetime.fromtimestamp(int(str(time_val)), tz=UTC),
        )


class HNClient:
    """Async client for the Hacker News API."""

    def __init__(
        self,
        base_url: str = HN_API_BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """Initialize the HN API client.

        Args:
            base_url: Base URL for HN API
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "HNClient":
        """Enter async context."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args: object) -> None:
        """Exit async context."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError("HNClient must be used as async context manager")
        return self._client

    async def _request_with_retry(self, url: str) -> object | None:
        """Make a request with retry logic.

        Returns None if the item doesn't exist (404).
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                result: object = response.json()
                return result
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        "Request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.max_retries,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        "Request error (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.max_retries,
                        delay,
                        e,
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
        return None

    async def get_max_item_id(self) -> int:
        """Get the current maximum item ID on HN."""
        url = f"{self.base_url}/maxitem.json"
        result = await self._request_with_retry(url)
        if not isinstance(result, int):
            raise ValueError(f"Unexpected max item response: {result}")
        return result

    async def get_item(self, item_id: int) -> HNItemData | None:
        """Fetch a single item by ID.

        Returns None if item doesn't exist, is deleted, or is not a story/comment.
        """
        url = f"{self.base_url}/item/{item_id}.json"
        result = await self._request_with_retry(url)
        if result is None or not isinstance(result, dict):
            return None
        return HNItemData.from_api_response(result)

    async def get_new_stories(self) -> list[int]:
        """Get list of new story IDs (most recent first)."""
        url = f"{self.base_url}/newstories.json"
        result = await self._request_with_retry(url)
        if not isinstance(result, list):
            return []
        return [int(x) for x in result if isinstance(x, int)]

    async def get_items_batch(
        self, item_ids: list[int], concurrency: int = 10
    ) -> list[HNItemData]:
        """Fetch multiple items concurrently.

        Args:
            item_ids: List of item IDs to fetch
            concurrency: Maximum concurrent requests

        Returns:
            List of successfully fetched items (skips None results)
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(item_id: int) -> HNItemData | None:
            async with semaphore:
                return await self.get_item(item_id)

        tasks = [fetch_with_semaphore(item_id) for item_id in item_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[HNItemData] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Failed to fetch item: %s", result)
            elif isinstance(result, HNItemData):
                items.append(result)
        return items
