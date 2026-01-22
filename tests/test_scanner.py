"""Tests for HN scanner functionality."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from community_scout.hn.client import HNClient, HNItemData
from community_scout.models import (
    AlertStatus,
    ContentSource,
    DiscordUser,
    HNItem,
    UserKeyword,
)
from community_scout.scanner import match_keywords
from community_scout.scanner.hn_scanner import HNScanner, get_searchable_text
from community_scout.scanner.state import get_scanner_state, update_scanner_state


class TestMatchKeywords:
    """Tests for keyword matching function."""

    def test_single_word_match(self) -> None:
        """Test matching a single word with word boundaries."""
        text = "I love Python programming"
        keywords = ["python", "java"]
        matches = match_keywords(text, keywords)
        assert matches == ["python"]

    def test_single_word_no_partial_match(self) -> None:
        """Test that partial matches are rejected for single words."""
        text = "I love Pythonic code"
        keywords = ["python"]
        matches = match_keywords(text, keywords)
        assert matches == []  # "python" should not match "Pythonic"

    def test_phrase_match(self) -> None:
        """Test matching a multi-word phrase."""
        text = "Machine learning is transforming the industry"
        keywords = ["machine learning", "deep learning"]
        matches = match_keywords(text, keywords)
        assert matches == ["machine learning"]

    def test_phrase_substring_match(self) -> None:
        """Test that phrases match as substrings."""
        text = "The machine learning model works great"
        keywords = ["machine learning"]
        matches = match_keywords(text, keywords)
        assert matches == ["machine learning"]

    def test_case_insensitive(self) -> None:
        """Test that matching is case-insensitive."""
        text = "PYTHON is great, python is awesome, Python rocks"
        keywords = ["python"]
        matches = match_keywords(text, keywords)
        assert matches == ["python"]

    def test_multiple_matches(self) -> None:
        """Test matching multiple keywords."""
        text = "Python and Rust are both great languages"
        keywords = ["python", "rust", "java"]
        matches = match_keywords(text, keywords)
        assert set(matches) == {"python", "rust"}

    def test_empty_text(self) -> None:
        """Test matching against empty text."""
        matches = match_keywords("", ["python"])
        assert matches == []

    def test_none_text(self) -> None:
        """Test matching against None text."""
        matches = match_keywords(None, ["python"])
        assert matches == []

    def test_empty_keywords(self) -> None:
        """Test matching with no keywords."""
        matches = match_keywords("Python is great", [])
        assert matches == []

    def test_special_characters_in_keyword(self) -> None:
        """Test that special regex characters are escaped.

        Note: Word boundary matching doesn't work well with special chars
        like ++ or #, so these are tested as phrases (with spaces).
        """
        text = "Check out my c++ project and learn c# basics"
        keywords = ["c++ project", "c# basics"]  # Use phrases for special chars
        matches = match_keywords(text, keywords)
        assert set(matches) == {"c++ project", "c# basics"}


class TestGetSearchableText:
    """Tests for searchable text extraction."""

    def test_story_with_all_fields(self) -> None:
        """Test extracting text from a story with all fields."""
        item = HNItemData(
            id=123,
            item_type="story",
            title="Show HN: My Project",
            text="Description here",
            url="https://example.com/project",
            author="user",
            score=42,
            parent_id=None,
            created_at=datetime.now(UTC),
        )
        text = get_searchable_text(item)
        assert "Show HN: My Project" in text
        assert "Description here" in text
        assert "https://example.com/project" in text

    def test_comment_only_text(self) -> None:
        """Test extracting text from a comment."""
        item = HNItemData(
            id=124,
            item_type="comment",
            title=None,
            text="This is a comment",
            url=None,
            author="user",
            score=10,
            parent_id=123,
            created_at=datetime.now(UTC),
        )
        text = get_searchable_text(item)
        assert text == "This is a comment"


class TestScannerState:
    """Tests for scanner state management."""

    @pytest.mark.asyncio
    async def test_get_scanner_state_creates_new(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_scanner_state creates a new state if none exists."""
        state = await get_scanner_state(db_session, "hackernews")
        assert state is not None
        assert state.source_name == "hackernews"
        assert state.last_seen_id == 0
        assert state.last_scan_at is None

    @pytest.mark.asyncio
    async def test_get_scanner_state_returns_existing(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_scanner_state returns existing state."""
        # Create initial state
        state1 = await get_scanner_state(db_session, "hackernews")
        state1.last_seen_id = 12345
        await db_session.commit()

        # Get it again
        state2 = await get_scanner_state(db_session, "hackernews")
        assert state2.id == state1.id
        assert state2.last_seen_id == 12345

    @pytest.mark.asyncio
    async def test_update_scanner_state(self, db_session: AsyncSession) -> None:
        """Test updating scanner state."""
        await update_scanner_state(db_session, "hackernews", 99999)
        await db_session.commit()

        state = await get_scanner_state(db_session, "hackernews")
        assert state.last_seen_id == 99999
        assert state.last_scan_at is not None


class TestHNScanner:
    """Tests for HNScanner service."""

    @pytest.mark.asyncio
    async def test_get_content_source_creates_new(
        self, db_session: AsyncSession
    ) -> None:
        """Test that get_content_source creates hackernews source."""
        mock_client = MagicMock(spec=HNClient)
        scanner = HNScanner(db_session, mock_client)

        source = await scanner.get_content_source()
        assert source is not None
        assert source.name == "hackernews"
        assert source.is_active is True

    @pytest.mark.asyncio
    async def test_get_active_keywords(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
    ) -> None:
        """Test getting active keywords grouped by phrase."""
        # Create keywords
        kw1 = UserKeyword(user_id=test_discord_user.id, phrase="python")
        kw2 = UserKeyword(user_id=test_discord_user.id, phrase="rust")
        kw3 = UserKeyword(user_id=test_discord_user.id, phrase="java", is_active=False)
        db_session.add_all([kw1, kw2, kw3])
        await db_session.commit()

        mock_client = MagicMock(spec=HNClient)
        scanner = HNScanner(db_session, mock_client)

        keyword_map = await scanner.get_active_keywords()
        assert "python" in keyword_map
        assert "rust" in keyword_map
        assert "java" not in keyword_map  # inactive

    @pytest.mark.asyncio
    async def test_store_item(self, db_session: AsyncSession) -> None:
        """Test storing an HN item."""
        mock_client = MagicMock(spec=HNClient)
        scanner = HNScanner(db_session, mock_client)

        item_data = HNItemData(
            id=12345,
            item_type="story",
            title="Test Story",
            text="Description",
            url="https://example.com",
            author="testuser",
            score=100,
            parent_id=None,
            created_at=datetime.now(UTC),
        )

        hn_item = await scanner.store_item(item_data)
        assert hn_item.hn_id == 12345
        assert hn_item.title == "Test Story"

        # Store again - should return existing
        hn_item2 = await scanner.store_item(item_data)
        assert hn_item2.id == hn_item.id

    @pytest.mark.asyncio
    async def test_create_alert(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_keyword: UserKeyword,
        test_content_source: ContentSource,
    ) -> None:
        """Test creating an alert."""
        mock_client = MagicMock(spec=HNClient)
        scanner = HNScanner(db_session, mock_client)

        # Create an HN item
        hn_item = HNItem(
            hn_id=99999,
            item_type="story",
            title="Python News",
            author="news",
            score=50,
            created_utc=datetime.now(UTC),
        )
        db_session.add(hn_item)
        await db_session.commit()
        await db_session.refresh(hn_item)

        # Create alert
        alert = await scanner.create_alert(
            test_discord_user.id,
            hn_item,
            test_keyword.id,
            test_content_source,
        )
        assert alert is not None
        assert alert.status == AlertStatus.PENDING.value

        # Try to create duplicate - should return None
        alert2 = await scanner.create_alert(
            test_discord_user.id,
            hn_item,
            test_keyword.id,
            test_content_source,
        )
        assert alert2 is None

    @pytest.mark.asyncio
    async def test_scan_no_keywords(self, db_session: AsyncSession) -> None:
        """Test scan with no active keywords."""
        mock_client = AsyncMock(spec=HNClient)
        mock_client.get_max_item_id.return_value = 10000

        scanner = HNScanner(db_session, mock_client)
        result = await scanner.scan()

        assert result.items_scanned == 0
        assert result.items_stored == 0
        assert result.alerts_created == 0


class TestHNItemData:
    """Tests for HNItemData parsing."""

    def test_from_api_response_story(self) -> None:
        """Test parsing a story from API response."""
        data = {
            "id": 123,
            "type": "story",
            "title": "Test Title",
            "text": "Test text",
            "url": "https://example.com",
            "by": "testuser",
            "score": 42,
            "time": 1704067200,
        }
        item = HNItemData.from_api_response(data)
        assert item is not None
        assert item.id == 123
        assert item.item_type == "story"
        assert item.title == "Test Title"
        assert item.author == "testuser"

    def test_from_api_response_comment(self) -> None:
        """Test parsing a comment from API response."""
        data = {
            "id": 124,
            "type": "comment",
            "text": "Test comment",
            "by": "commenter",
            "time": 1704067200,
            "parent": 123,
        }
        item = HNItemData.from_api_response(data)
        assert item is not None
        assert item.item_type == "comment"
        assert item.parent_id == 123

    def test_from_api_response_deleted(self) -> None:
        """Test that deleted items return None."""
        data = {"id": 125, "type": "story", "deleted": True}
        item = HNItemData.from_api_response(data)
        assert item is None

    def test_from_api_response_dead(self) -> None:
        """Test that dead items return None."""
        data = {"id": 126, "type": "story", "dead": True}
        item = HNItemData.from_api_response(data)
        assert item is None

    def test_from_api_response_job(self) -> None:
        """Test that job items return None."""
        data = {
            "id": 127,
            "type": "job",
            "title": "Job posting",
            "by": "company",
            "time": 1704067200,
        }
        item = HNItemData.from_api_response(data)
        assert item is None
