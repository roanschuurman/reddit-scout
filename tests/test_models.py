"""Tests for new data models."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from community_scout.models import (
    AlertStatus,
    ContentSource,
    DiscordUser,
    HNItem,
    HNItemType,
    SourceThread,
    UserAlert,
    UserKeyword,
)


class TestDiscordUser:
    """Tests for DiscordUser model."""

    @pytest.mark.asyncio
    async def test_create_discord_user(self, db_session: AsyncSession) -> None:
        """Test creating a Discord user."""
        user = DiscordUser(
            discord_id="123456789012345678",
            discord_username="testuser#1234",
            channel_id="987654321098765432",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.discord_id == "123456789012345678"
        assert user.discord_username == "testuser#1234"
        assert user.channel_id == "987654321098765432"
        assert user.is_active is True
        assert user.openrouter_api_key is None
        assert user.created_at is not None


class TestUserKeyword:
    """Tests for UserKeyword model."""

    @pytest.mark.asyncio
    async def test_create_keyword(
        self, db_session: AsyncSession, test_discord_user: DiscordUser
    ) -> None:
        """Test creating a keyword for a user."""
        keyword = UserKeyword(
            user_id=test_discord_user.id,
            phrase="machine learning",
        )
        db_session.add(keyword)
        await db_session.commit()
        await db_session.refresh(keyword)

        assert keyword.id is not None
        assert keyword.user_id == test_discord_user.id
        assert keyword.phrase == "machine learning"
        assert keyword.is_active is True


class TestHNItem:
    """Tests for HNItem model."""

    @pytest.mark.asyncio
    async def test_create_hn_story(self, db_session: AsyncSession) -> None:
        """Test creating an HN story item."""
        item = HNItem(
            hn_id=12345678,
            item_type=HNItemType.STORY.value,
            title="Show HN: My Cool Project",
            text="Description of my project...",
            url="https://github.com/user/project",
            author="hackernews_user",
            score=142,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.id is not None
        assert item.hn_id == 12345678
        assert item.item_type == "story"
        assert item.title == "Show HN: My Cool Project"
        assert item.hn_url == "https://news.ycombinator.com/item?id=12345678"

    @pytest.mark.asyncio
    async def test_create_hn_comment(self, db_session: AsyncSession) -> None:
        """Test creating an HN comment item."""
        item = HNItem(
            hn_id=12345679,
            item_type=HNItemType.COMMENT.value,
            text="This is a great project!",
            author="commenter",
            score=50,
            parent_id=12345678,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        assert item.id is not None
        assert item.item_type == "comment"
        assert item.parent_id == 12345678
        assert item.title is None


class TestUserAlert:
    """Tests for UserAlert model."""

    @pytest.mark.asyncio
    async def test_create_user_alert(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_keyword: UserKeyword,
        test_content_source: ContentSource,
    ) -> None:
        """Test creating a user alert."""
        # Create an HN item first
        item = HNItem(
            hn_id=99999999,
            item_type=HNItemType.STORY.value,
            title="Python 4.0 Released",
            author="python_news",
            score=500,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        # Create the alert
        alert = UserAlert(
            user_id=test_discord_user.id,
            item_id=item.id,
            keyword_id=test_keyword.id,
            source_id=test_content_source.id,
            summary="Python 4.0 has been released with major improvements.",
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)

        assert alert.id is not None
        assert alert.status == AlertStatus.PENDING.value
        assert alert.summary is not None
        assert alert.discord_message_id is None


class TestSourceThread:
    """Tests for SourceThread model."""

    @pytest.mark.asyncio
    async def test_create_source_thread(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_content_source: ContentSource,
    ) -> None:
        """Test creating a source thread for a user."""
        thread = SourceThread(
            user_id=test_discord_user.id,
            source_id=test_content_source.id,
            thread_id="111222333444555666",
        )
        db_session.add(thread)
        await db_session.commit()
        await db_session.refresh(thread)

        assert thread.id is not None
        assert thread.thread_id == "111222333444555666"
