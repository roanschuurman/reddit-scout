"""Tests for the Reddit scanner service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.models.campaign import Campaign, CampaignKeyword, CampaignSubreddit
from reddit_scout.models.match import Match, MatchStatus, RedditType
from reddit_scout.models.user import User
from reddit_scout.scanner.client import RedditComment, RedditPost
from reddit_scout.scanner.matcher import (
    extract_context,
    match_comment,
    match_keywords,
    match_post,
)
from reddit_scout.scanner.service import ScannerService


class TestExtractContext:
    """Tests for context extraction."""

    def test_extract_context_middle_of_text(self) -> None:
        """Extract context from the middle of a long text."""
        text = "This is a long text with some important keyword in the middle of it all."
        # "keyword" starts at position 35
        context = extract_context(text, 35, 42, context_chars=20)
        assert "keyword" in context
        assert len(context) < len(text)

    def test_extract_context_start_of_text(self) -> None:
        """Extract context from the start of text."""
        text = "keyword appears at the start of this sentence."
        context = extract_context(text, 0, 7, context_chars=20)
        assert "keyword" in context
        assert not context.startswith("...")

    def test_extract_context_end_of_text(self) -> None:
        """Extract context from the end of text."""
        text = "This sentence ends with keyword"
        context = extract_context(text, 24, 31, context_chars=20)
        assert "keyword" in context
        assert not context.endswith("...")

    def test_extract_context_adds_ellipsis(self) -> None:
        """Context adds ellipsis when truncated."""
        text = "x" * 100 + " keyword " + "y" * 100
        context = extract_context(text, 101, 108, context_chars=20)
        assert context.startswith("...")
        assert context.endswith("...")


class TestMatchKeywords:
    """Tests for keyword matching."""

    def test_match_single_word(self) -> None:
        """Match a single word keyword."""
        result = match_keywords("This is a test of the scanner", ["test"])
        assert result is not None
        assert result.keyword == "test"
        assert "test" in result.context_snippet

    def test_match_case_insensitive(self) -> None:
        """Matching is case insensitive."""
        result = match_keywords("This is a TEST of the scanner", ["test"])
        assert result is not None
        assert result.keyword == "test"

    def test_match_phrase(self) -> None:
        """Match a multi-word phrase."""
        result = match_keywords("Looking for best tool for the job", ["best tool"])
        assert result is not None
        assert result.keyword == "best tool"

    def test_match_word_boundary(self) -> None:
        """Single word matching respects word boundaries."""
        # Should not match "testing" when looking for "test"
        result = match_keywords("I am testing this feature", ["test"])
        assert result is None

    def test_match_first_keyword_wins(self) -> None:
        """First matching keyword is returned."""
        result = match_keywords("Find foo and bar here", ["foo", "bar"])
        assert result is not None
        assert result.keyword == "foo"

    def test_no_match(self) -> None:
        """No match when keyword not present."""
        result = match_keywords("This is some text", ["missing"])
        assert result is None

    def test_empty_text(self) -> None:
        """No match on empty text."""
        result = match_keywords("", ["test"])
        assert result is None

    def test_empty_keywords(self) -> None:
        """No match with empty keywords list."""
        result = match_keywords("This is a test", [])
        assert result is None


class TestMatchPost:
    """Tests for matching posts."""

    def test_match_in_title(self) -> None:
        """Match keyword in post title."""
        result = match_post("Looking for a great scanner", "No keywords here", ["scanner"])
        assert result is not None
        assert result.keyword == "scanner"

    def test_match_in_body(self) -> None:
        """Match keyword in post body."""
        result = match_post("Generic title", "The body has scanner keyword", ["scanner"])
        assert result is not None
        assert result.keyword == "scanner"

    def test_title_priority(self) -> None:
        """Title match takes priority over body match."""
        result = match_post("Title has foo", "Body has bar", ["bar", "foo"])
        assert result is not None
        # Should match "foo" in title even though "bar" comes first in keywords
        assert result.keyword == "foo"


class TestMatchComment:
    """Tests for matching comments."""

    def test_match_in_comment(self) -> None:
        """Match keyword in comment body."""
        result = match_comment("This comment mentions scanner tool", ["scanner"])
        assert result is not None
        assert result.keyword == "scanner"


class TestScannerService:
    """Tests for the scanner service."""

    @pytest.fixture
    async def campaign_with_config(
        self, db_session: AsyncSession, test_user: User
    ) -> Campaign:
        """Create a campaign with subreddits and keywords configured."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        campaign = Campaign(
            user_id=test_user.id,
            name="Test Scanner Campaign",
            system_prompt="Test prompt",
            is_active=True,
            scan_frequency_minutes=60,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        # Add subreddits
        subreddit = CampaignSubreddit(
            campaign_id=campaign.id,
            subreddit_name="python",
        )
        db_session.add(subreddit)

        # Add keywords
        keyword = CampaignKeyword(
            campaign_id=campaign.id,
            phrase="scanner",
        )
        db_session.add(keyword)

        await db_session.commit()

        # Re-fetch with eager loading to avoid lazy load issues
        stmt = (
            select(Campaign)
            .where(Campaign.id == campaign.id)
            .options(
                selectinload(Campaign.subreddits),
                selectinload(Campaign.keywords),
            )
        )
        result = await db_session.execute(stmt)
        return result.scalar_one()

    @pytest.fixture
    def mock_reddit_client(self) -> MagicMock:
        """Create a mock Reddit client."""
        client = MagicMock()
        client.verify_connection.return_value = True
        return client

    async def test_get_campaigns_due_never_scanned(
        self, db_session: AsyncSession, campaign_with_config: Campaign
    ) -> None:
        """Campaign that was never scanned is due for scanning."""
        scanner = ScannerService(db_session)
        due = await scanner.get_campaigns_due_for_scan()
        assert len(due) == 1
        assert due[0].id == campaign_with_config.id

    async def test_get_campaigns_due_recently_scanned(
        self, db_session: AsyncSession, campaign_with_config: Campaign
    ) -> None:
        """Campaign that was recently scanned is not due."""
        campaign_with_config.last_scanned_at = datetime.now(UTC)
        await db_session.commit()

        scanner = ScannerService(db_session)
        due = await scanner.get_campaigns_due_for_scan()
        assert len(due) == 0

    async def test_get_campaigns_due_after_frequency(
        self, db_session: AsyncSession, campaign_with_config: Campaign
    ) -> None:
        """Campaign is due after scan frequency has passed."""
        campaign_with_config.last_scanned_at = datetime.now(UTC) - timedelta(hours=2)
        await db_session.commit()

        scanner = ScannerService(db_session)
        due = await scanner.get_campaigns_due_for_scan()
        assert len(due) == 1

    async def test_get_campaigns_skips_inactive(
        self, db_session: AsyncSession, campaign_with_config: Campaign
    ) -> None:
        """Inactive campaigns are not included."""
        campaign_with_config.is_active = False
        await db_session.commit()

        scanner = ScannerService(db_session)
        due = await scanner.get_campaigns_due_for_scan()
        assert len(due) == 0

    async def test_get_campaigns_skips_no_subreddits(
        self, db_session: AsyncSession, test_user: User
    ) -> None:
        """Campaigns without subreddits are skipped."""
        campaign = Campaign(
            user_id=test_user.id,
            name="No Subreddits",
            system_prompt="Test",
            is_active=True,
        )
        db_session.add(campaign)
        await db_session.commit()

        # Add keyword but no subreddit
        keyword = CampaignKeyword(campaign_id=campaign.id, phrase="test")
        db_session.add(keyword)
        await db_session.commit()

        scanner = ScannerService(db_session)
        due = await scanner.get_campaigns_due_for_scan()
        assert len(due) == 0

    async def test_scan_creates_match_for_post(
        self,
        db_session: AsyncSession,
        campaign_with_config: Campaign,
        mock_reddit_client: MagicMock,
    ) -> None:
        """Scanning creates matches for matching posts."""
        # Setup mock to return a matching post
        mock_post = RedditPost(
            id="abc123",
            subreddit="python",
            title="Looking for a good scanner",
            selftext="Need help with scanning.",
            author="testuser",
            permalink="/r/python/comments/abc123/post_title/",
            created_utc=datetime.now(UTC),
            score=10,
            num_comments=5,
        )
        mock_reddit_client.get_subreddit_posts.return_value = iter([mock_post])
        mock_reddit_client.get_subreddit_comments.return_value = iter([])

        scanner = ScannerService(db_session, mock_reddit_client)
        result = await scanner.scan_campaign(campaign_with_config)

        assert result.posts_checked == 1
        assert result.new_matches == 1

        # Verify match was created
        from sqlalchemy import select

        stmt = select(Match).where(Match.campaign_id == campaign_with_config.id)
        matches = (await db_session.execute(stmt)).scalars().all()
        assert len(matches) == 1
        assert matches[0].reddit_id == "t3_abc123"
        assert matches[0].reddit_type == RedditType.POST.value
        assert matches[0].status == MatchStatus.PENDING.value

    async def test_scan_creates_match_for_comment(
        self,
        db_session: AsyncSession,
        campaign_with_config: Campaign,
        mock_reddit_client: MagicMock,
    ) -> None:
        """Scanning creates matches for matching comments."""
        mock_comment = RedditComment(
            id="xyz789",
            subreddit="python",
            body="Check out this scanner tool!",
            author="commenter",
            permalink="/r/python/comments/abc/title/xyz789/",
            created_utc=datetime.now(UTC),
            score=5,
            link_title="Original Post",
        )
        mock_reddit_client.get_subreddit_posts.return_value = iter([])
        mock_reddit_client.get_subreddit_comments.return_value = iter([mock_comment])

        scanner = ScannerService(db_session, mock_reddit_client)
        result = await scanner.scan_campaign(campaign_with_config)

        assert result.comments_checked == 1
        assert result.new_matches == 1

        from sqlalchemy import select

        stmt = select(Match).where(Match.campaign_id == campaign_with_config.id)
        matches = (await db_session.execute(stmt)).scalars().all()
        assert len(matches) == 1
        assert matches[0].reddit_id == "t1_xyz789"
        assert matches[0].reddit_type == RedditType.COMMENT.value

    async def test_scan_deduplicates(
        self,
        db_session: AsyncSession,
        campaign_with_config: Campaign,
        mock_reddit_client: MagicMock,
    ) -> None:
        """Scanning skips already-matched reddit IDs."""
        # Create existing match
        existing_match = Match(
            campaign_id=campaign_with_config.id,
            reddit_id="t3_abc123",
            reddit_type=RedditType.POST.value,
            subreddit="python",
            matched_keyword="scanner",
            title="Old post",
            permalink="https://reddit.com/r/python/comments/abc123/",
            author="testuser",
            created_utc=datetime.now(UTC),
            status=MatchStatus.PENDING.value,
        )
        db_session.add(existing_match)
        await db_session.commit()

        # Setup mock to return post with same ID
        mock_post = RedditPost(
            id="abc123",
            subreddit="python",
            title="Looking for a good scanner",
            selftext="",
            author="testuser",
            permalink="/r/python/comments/abc123/post_title/",
            created_utc=datetime.now(UTC),
            score=10,
            num_comments=5,
        )
        mock_reddit_client.get_subreddit_posts.return_value = iter([mock_post])
        mock_reddit_client.get_subreddit_comments.return_value = iter([])

        scanner = ScannerService(db_session, mock_reddit_client)
        result = await scanner.scan_campaign(campaign_with_config)

        assert result.duplicates_skipped == 1
        assert result.new_matches == 0

    async def test_scan_updates_last_scanned_at(
        self,
        db_session: AsyncSession,
        campaign_with_config: Campaign,
        mock_reddit_client: MagicMock,
    ) -> None:
        """Scanning updates campaign's last_scanned_at."""
        assert campaign_with_config.last_scanned_at is None

        mock_reddit_client.get_subreddit_posts.return_value = iter([])
        mock_reddit_client.get_subreddit_comments.return_value = iter([])

        scanner = ScannerService(db_session, mock_reddit_client)
        await scanner.scan_campaign(campaign_with_config)

        assert campaign_with_config.last_scanned_at is not None

    async def test_scan_handles_errors_gracefully(
        self,
        db_session: AsyncSession,
        campaign_with_config: Campaign,
        mock_reddit_client: MagicMock,
    ) -> None:
        """Scanner handles errors from Reddit API gracefully."""
        mock_reddit_client.get_subreddit_posts.side_effect = Exception("API Error")
        mock_reddit_client.get_subreddit_comments.return_value = iter([])

        scanner = ScannerService(db_session, mock_reddit_client)
        result = await scanner.scan_campaign(campaign_with_config)

        assert len(result.errors) > 0
        assert "API Error" in result.errors[0]
