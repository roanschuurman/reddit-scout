"""Scanner service for monitoring Reddit."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from reddit_scout.models.campaign import Campaign
from reddit_scout.models.match import Match, MatchStatus, RedditType
from reddit_scout.scanner.client import RedditClient, RedditComment, RedditPost
from reddit_scout.scanner.matcher import match_comment, match_post

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of scanning a campaign."""

    campaign_id: int
    campaign_name: str
    subreddits_scanned: int
    posts_checked: int
    comments_checked: int
    new_matches: int
    duplicates_skipped: int
    errors: list[str]


class ScannerService:
    """Service for scanning Reddit for keyword matches."""

    def __init__(self, db: AsyncSession, reddit_client: RedditClient | None = None) -> None:
        """
        Initialize the scanner service.

        Args:
            db: Database session
            reddit_client: Reddit API client (created if not provided)
        """
        self.db = db
        self.reddit = reddit_client or RedditClient()

    async def get_campaigns_due_for_scan(self) -> list[Campaign]:
        """
        Get all active campaigns that are due for scanning.

        A campaign is due if:
        - It has never been scanned (last_scanned_at is None), OR
        - Time since last scan >= scan_frequency_minutes

        Returns:
            List of campaigns to scan
        """
        now = datetime.now(UTC)

        # Get active campaigns with their subreddits and keywords
        stmt = (
            select(Campaign)
            .where(Campaign.is_active == True)  # noqa: E712
            .options(
                selectinload(Campaign.subreddits),
                selectinload(Campaign.keywords),
            )
        )
        result = await self.db.execute(stmt)
        campaigns = result.scalars().all()

        due_campaigns = []
        for campaign in campaigns:
            # Skip campaigns without subreddits or keywords
            if not campaign.subreddits or not campaign.keywords:
                logger.debug(
                    "Skipping campaign %s: no subreddits or keywords configured",
                    campaign.name,
                )
                continue

            if campaign.last_scanned_at is None:
                # Never scanned - include it
                due_campaigns.append(campaign)
            else:
                # Check if enough time has passed
                next_scan_time = campaign.last_scanned_at + timedelta(
                    minutes=campaign.scan_frequency_minutes
                )
                if now >= next_scan_time:
                    due_campaigns.append(campaign)

        return due_campaigns

    async def _check_duplicate(self, campaign_id: int, reddit_id: str) -> bool:
        """Check if a match with this reddit_id already exists for this campaign."""
        stmt = select(Match).where(
            Match.campaign_id == campaign_id,
            Match.reddit_id == reddit_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _create_match_from_post(
        self,
        campaign: Campaign,
        post: RedditPost,
        matched_keyword: str,
        context_snippet: str,
    ) -> Match:
        """Create a Match record from a Reddit post."""
        match = Match(
            campaign_id=campaign.id,
            reddit_id=f"t3_{post.id}",  # t3_ prefix for posts
            reddit_type=RedditType.POST.value,
            subreddit=post.subreddit,
            matched_keyword=matched_keyword,
            title=post.title,
            body_snippet=context_snippet,
            permalink=f"https://reddit.com{post.permalink}",
            author=post.author,
            created_utc=post.created_utc,
            status=MatchStatus.PENDING.value,
        )
        self.db.add(match)
        return match

    async def _create_match_from_comment(
        self,
        campaign: Campaign,
        comment: RedditComment,
        matched_keyword: str,
        context_snippet: str,
    ) -> Match:
        """Create a Match record from a Reddit comment."""
        match = Match(
            campaign_id=campaign.id,
            reddit_id=f"t1_{comment.id}",  # t1_ prefix for comments
            reddit_type=RedditType.COMMENT.value,
            subreddit=comment.subreddit,
            matched_keyword=matched_keyword,
            title=comment.link_title,  # Store parent post title
            body_snippet=context_snippet,
            permalink=f"https://reddit.com{comment.permalink}",
            author=comment.author,
            created_utc=comment.created_utc,
            status=MatchStatus.PENDING.value,
        )
        self.db.add(match)
        return match

    async def scan_campaign(self, campaign: Campaign) -> ScanResult:
        """
        Scan a single campaign for keyword matches.

        Args:
            campaign: Campaign to scan

        Returns:
            ScanResult with statistics
        """
        result = ScanResult(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            subreddits_scanned=0,
            posts_checked=0,
            comments_checked=0,
            new_matches=0,
            duplicates_skipped=0,
            errors=[],
        )

        # Get keywords as list of strings
        keywords = [kw.phrase for kw in campaign.keywords]

        for subreddit in campaign.subreddits:
            subreddit_name = subreddit.subreddit_name
            logger.info("Scanning r/%s for campaign '%s'", subreddit_name, campaign.name)

            try:
                # Scan posts
                for post in self.reddit.get_subreddit_posts(subreddit_name, limit=100):
                    result.posts_checked += 1

                    # Check for keyword match
                    match_result = match_post(post.title, post.selftext, keywords)
                    if match_result:
                        reddit_id = f"t3_{post.id}"
                        if await self._check_duplicate(campaign.id, reddit_id):
                            result.duplicates_skipped += 1
                            continue

                        await self._create_match_from_post(
                            campaign,
                            post,
                            match_result.keyword,
                            match_result.context_snippet,
                        )
                        result.new_matches += 1
                        logger.debug(
                            "New match: post '%s' in r/%s (keyword: %s)",
                            post.title[:50],
                            subreddit_name,
                            match_result.keyword,
                        )

                # Scan comments
                for comment in self.reddit.get_subreddit_comments(subreddit_name, limit=100):
                    result.comments_checked += 1

                    # Check for keyword match
                    match_result = match_comment(comment.body, keywords)
                    if match_result:
                        reddit_id = f"t1_{comment.id}"
                        if await self._check_duplicate(campaign.id, reddit_id):
                            result.duplicates_skipped += 1
                            continue

                        await self._create_match_from_comment(
                            campaign,
                            comment,
                            match_result.keyword,
                            match_result.context_snippet,
                        )
                        result.new_matches += 1
                        logger.debug(
                            "New match: comment in r/%s (keyword: %s)",
                            subreddit_name,
                            match_result.keyword,
                        )

                result.subreddits_scanned += 1

            except Exception as e:
                error_msg = f"Error scanning r/{subreddit_name}: {str(e)}"
                logger.error(error_msg)
                result.errors.append(error_msg)

        # Update last_scanned_at
        campaign.last_scanned_at = datetime.now(UTC)

        return result

    async def run_scan(self) -> list[ScanResult]:
        """
        Run a full scan of all due campaigns.

        Returns:
            List of ScanResult for each campaign scanned
        """
        results: list[ScanResult] = []

        campaigns = await self.get_campaigns_due_for_scan()
        if not campaigns:
            logger.info("No campaigns due for scanning")
            return results

        logger.info("Found %d campaigns due for scanning", len(campaigns))

        for campaign in campaigns:
            try:
                logger.info("Starting scan for campaign '%s' (ID: %d)", campaign.name, campaign.id)
                result = await self.scan_campaign(campaign)
                results.append(result)

                logger.info(
                    "Completed scan for '%s': %d subreddits, %d posts, %d comments, "
                    "%d new matches, %d duplicates skipped",
                    campaign.name,
                    result.subreddits_scanned,
                    result.posts_checked,
                    result.comments_checked,
                    result.new_matches,
                    result.duplicates_skipped,
                )

                if result.errors:
                    logger.warning("Errors during scan: %s", result.errors)

            except Exception as e:
                logger.error("Failed to scan campaign '%s': %s", campaign.name, str(e))
                results.append(
                    ScanResult(
                        campaign_id=campaign.id,
                        campaign_name=campaign.name,
                        subreddits_scanned=0,
                        posts_checked=0,
                        comments_checked=0,
                        new_matches=0,
                        duplicates_skipped=0,
                        errors=[str(e)],
                    )
                )

        # Commit all changes
        await self.db.commit()

        return results
