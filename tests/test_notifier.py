"""Tests for alert notifier functionality."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from community_scout.models import (
    AlertStatus,
    ContentSource,
    DiscordUser,
    HNItem,
    SourceThread,
    UserAlert,
    UserKeyword,
)
from community_scout.notifier.alert_notifier import AlertNotifier


class TestAlertNotifier:
    """Tests for AlertNotifier service."""

    @pytest.mark.asyncio
    async def test_get_pending_alerts(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_keyword: UserKeyword,
        test_content_source: ContentSource,
    ) -> None:
        """Test fetching pending alerts."""
        # Create HN item
        item = HNItem(
            hn_id=12345,
            item_type="story",
            title="Test Story",
            author="testuser",
            score=100,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        # Create pending alert
        alert = UserAlert(
            user_id=test_discord_user.id,
            item_id=item.id,
            keyword_id=test_keyword.id,
            source_id=test_content_source.id,
            status=AlertStatus.PENDING.value,
        )
        db_session.add(alert)
        await db_session.commit()

        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)
        alerts = await notifier.get_pending_alerts()

        assert len(alerts) == 1
        assert alerts[0].status == AlertStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_get_pending_alerts_excludes_sent(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_keyword: UserKeyword,
        test_content_source: ContentSource,
    ) -> None:
        """Test that sent alerts are excluded."""
        # Create HN item
        item = HNItem(
            hn_id=12346,
            item_type="story",
            title="Test Story 2",
            author="testuser",
            score=50,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        # Create sent alert
        alert = UserAlert(
            user_id=test_discord_user.id,
            item_id=item.id,
            keyword_id=test_keyword.id,
            source_id=test_content_source.id,
            status=AlertStatus.SENT.value,
        )
        db_session.add(alert)
        await db_session.commit()

        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)
        alerts = await notifier.get_pending_alerts()

        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_get_user_api_key_none(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
    ) -> None:
        """Test getting API key when user has none."""
        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)

        api_key = notifier.get_user_api_key(test_discord_user)
        assert api_key is None

    @pytest.mark.asyncio
    async def test_build_alert_embed(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_keyword: UserKeyword,
        test_content_source: ContentSource,
    ) -> None:
        """Test building Discord embed for alert."""
        # Create HN item
        item = HNItem(
            hn_id=12347,
            item_type="story",
            title="Show HN: Cool Project",
            text="This is a cool project",
            url="https://example.com",
            author="developer",
            score=200,
            created_utc=datetime.now(UTC),
        )
        db_session.add(item)
        await db_session.commit()
        await db_session.refresh(item)

        # Create alert
        alert = UserAlert(
            user_id=test_discord_user.id,
            item_id=item.id,
            keyword_id=test_keyword.id,
            source_id=test_content_source.id,
            status=AlertStatus.PENDING.value,
        )
        db_session.add(alert)
        await db_session.commit()
        await db_session.refresh(alert)

        # Load relationships
        await db_session.refresh(alert, ["item", "keyword"])

        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)

        embed = notifier.build_alert_embed(alert, "This is a test summary")

        assert embed.title == "Show HN: Cool Project"
        assert embed.url == item.hn_url

    @pytest.mark.asyncio
    async def test_generate_summary_no_api_key(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test summary generation fails gracefully without API key."""
        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)

        item = HNItem(
            hn_id=99999,
            item_type="story",
            title="Test",
            author="test",
            score=1,
            created_utc=datetime.now(UTC),
        )

        # Patch settings to have no API key
        with patch("community_scout.notifier.alert_notifier.settings") as mock_settings:
            mock_settings.openrouter_api_key = ""
            summary = await notifier.generate_summary(item, api_key=None)

        assert summary is None

    @pytest.mark.asyncio
    async def test_get_or_create_source_thread_existing(
        self,
        db_session: AsyncSession,
        test_discord_user: DiscordUser,
        test_content_source: ContentSource,
    ) -> None:
        """Test getting existing source thread."""
        # Create existing thread
        thread = SourceThread(
            user_id=test_discord_user.id,
            source_id=test_content_source.id,
            thread_id="123456789",
        )
        db_session.add(thread)
        await db_session.commit()

        mock_bot = MagicMock()
        notifier = AlertNotifier(db_session, mock_bot)

        thread_id = await notifier.get_or_create_source_thread(
            test_discord_user, test_content_source
        )

        assert thread_id == "123456789"


class TestNotifyResult:
    """Tests for NotifyResult dataclass."""

    def test_notify_result_creation(self) -> None:
        """Test creating a NotifyResult."""
        from community_scout.notifier.alert_notifier import NotifyResult

        result = NotifyResult(
            alerts_processed=10,
            alerts_sent=8,
            alerts_failed=2,
        )

        assert result.alerts_processed == 10
        assert result.alerts_sent == 8
        assert result.alerts_failed == 2
