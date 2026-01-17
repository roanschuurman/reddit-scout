"""Tests for Discord bot module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from reddit_scout.bot.notifications import (
    _format_time_ago,
    _truncate,
    build_match_embed,
)
from reddit_scout.models.match import Match, RedditType


class TestFormatTimeAgo:
    """Tests for time formatting helper."""

    def test_just_now(self) -> None:
        """Test formatting for very recent times."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(seconds=30))
        assert result == "just now"

    def test_minutes(self) -> None:
        """Test formatting for minutes ago."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(minutes=5))
        assert result == "5 minutes ago"

    def test_minute_singular(self) -> None:
        """Test singular minute."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(minutes=1))
        assert result == "1 minute ago"

    def test_hours(self) -> None:
        """Test formatting for hours ago."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(hours=3))
        assert result == "3 hours ago"

    def test_hour_singular(self) -> None:
        """Test singular hour."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(hours=1))
        assert result == "1 hour ago"

    def test_days(self) -> None:
        """Test formatting for days ago."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(days=2))
        assert result == "2 days ago"

    def test_day_singular(self) -> None:
        """Test singular day."""
        now = datetime.now(UTC)
        result = _format_time_ago(now - timedelta(days=1))
        assert result == "1 day ago"

    def test_naive_datetime(self) -> None:
        """Test that naive datetimes are handled."""
        now = datetime.now(UTC)
        naive = now.replace(tzinfo=None) - timedelta(hours=2)
        result = _format_time_ago(naive)
        assert "hour" in result


class TestTruncate:
    """Tests for text truncation helper."""

    def test_no_truncation_needed(self) -> None:
        """Test text shorter than max length."""
        result = _truncate("short text", max_length=100)
        assert result == "short text"

    def test_exact_length(self) -> None:
        """Test text exactly at max length."""
        result = _truncate("12345", max_length=5)
        assert result == "12345"

    def test_truncation(self) -> None:
        """Test text longer than max length."""
        result = _truncate("this is a long text", max_length=10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_custom_suffix(self) -> None:
        """Test truncation with custom suffix."""
        result = _truncate("this is a long text", max_length=12, suffix="…")
        assert result.endswith("…")


class TestBuildMatchEmbed:
    """Tests for Discord embed building."""

    @pytest.fixture
    def sample_match(self) -> Match:
        """Create a sample match for testing."""
        match = MagicMock(spec=Match)
        match.id = 123
        match.subreddit = "test_subreddit"
        match.reddit_type = RedditType.POST.value
        match.title = "This is a test post title"
        match.author = "testuser"
        match.created_utc = datetime.now(UTC) - timedelta(hours=2)
        match.matched_keyword = "help"
        match.body_snippet = "I need help with this problem..."
        match.permalink = "/r/test_subreddit/comments/abc123/test_post/"
        return match

    def test_embed_has_title(self, sample_match: Match) -> None:
        """Test embed has correct title."""
        embed = build_match_embed(sample_match)
        assert "r/test_subreddit" in embed.title

    def test_embed_has_fields(self, sample_match: Match) -> None:
        """Test embed has required fields."""
        embed = build_match_embed(sample_match)
        field_names = [f.name for f in embed.fields]

        assert any("Post" in name for name in field_names)  # Type field
        assert "Author" in field_names
        assert "Keyword" in field_names
        assert "Content" in field_names
        assert "Link" in field_names

    def test_embed_includes_keyword(self, sample_match: Match) -> None:
        """Test embed includes matched keyword."""
        embed = build_match_embed(sample_match)
        keyword_field = next(f for f in embed.fields if f.name == "Keyword")
        assert "help" in keyword_field.value

    def test_embed_includes_reddit_link(self, sample_match: Match) -> None:
        """Test embed includes Reddit link."""
        embed = build_match_embed(sample_match)
        link_field = next(f for f in embed.fields if f.name == "Link")
        assert "reddit.com" in link_field.value
        assert sample_match.permalink in link_field.value

    def test_embed_with_draft(self, sample_match: Match) -> None:
        """Test embed includes AI draft when provided."""
        draft = "This is a helpful AI generated response."
        embed = build_match_embed(sample_match, draft_content=draft)

        field_names = [f.name for f in embed.fields]
        assert "📝 AI Draft" in field_names

        draft_field = next(f for f in embed.fields if f.name == "📝 AI Draft")
        assert "helpful" in draft_field.value

    def test_embed_without_draft(self, sample_match: Match) -> None:
        """Test embed without AI draft."""
        embed = build_match_embed(sample_match)
        field_names = [f.name for f in embed.fields]
        assert "📝 AI Draft" not in field_names

    def test_embed_for_comment(self, sample_match: Match) -> None:
        """Test embed for comment type."""
        sample_match.reddit_type = RedditType.COMMENT.value
        embed = build_match_embed(sample_match)

        field_names = [f.name for f in embed.fields]
        assert any("Comment" in name for name in field_names)

    def test_embed_has_footer(self, sample_match: Match) -> None:
        """Test embed has footer with match ID."""
        embed = build_match_embed(sample_match)
        assert embed.footer is not None
        assert "123" in embed.footer.text

    def test_embed_has_timestamp(self, sample_match: Match) -> None:
        """Test embed has timestamp."""
        embed = build_match_embed(sample_match)
        assert embed.timestamp is not None

    def test_embed_truncates_long_content(self, sample_match: Match) -> None:
        """Test that long content is truncated."""
        sample_match.body_snippet = "x" * 1000
        embed = build_match_embed(sample_match)

        content_field = next(f for f in embed.fields if f.name == "Content")
        assert len(content_field.value) <= 510  # 500 + prefix "> " + ellipsis

    def test_embed_truncates_long_draft(self, sample_match: Match) -> None:
        """Test that long draft is truncated."""
        long_draft = "y" * 2000
        embed = build_match_embed(sample_match, draft_content=long_draft)

        draft_field = next(f for f in embed.fields if f.name == "📝 AI Draft")
        assert len(draft_field.value) <= 1003  # 1000 + "..."
