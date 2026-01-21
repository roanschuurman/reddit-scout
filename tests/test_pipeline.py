"""Tests for the match processing pipeline."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.ai.generator import GenerationResult, SummaryGenerator
from reddit_scout.models import Campaign, Match
from reddit_scout.models.match import DraftResponse, MatchStatus, RedditType
from reddit_scout.pipeline import MatchPipeline, MatchProcessingResult, PipelineResult


class TestMatchPipeline:
    """Tests for MatchPipeline."""

    @pytest.fixture
    async def test_match(
        self, db_session: AsyncSession, test_campaign: Campaign
    ) -> Match:
        """Create a test match."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        match = Match(
            campaign_id=test_campaign.id,
            reddit_id="t3_test123",
            reddit_type=RedditType.POST.value,
            subreddit="test",
            matched_keyword="help",
            title="Need help with something",
            body_snippet="I'm looking for help with this problem...",
            permalink="/r/test/comments/test123/",
            author="testuser",
            created_utc=datetime.now(UTC),
            status=MatchStatus.PENDING.value,
        )
        db_session.add(match)
        await db_session.commit()
        # Re-fetch with relationships loaded
        stmt = (
            select(Match)
            .where(Match.id == match.id)
            .options(selectinload(Match.draft_responses))
        )
        result = await db_session.execute(stmt)
        return result.scalar_one()

    @pytest.fixture
    def mock_generator(self) -> MagicMock:
        """Create a mock summary generator."""
        generator = MagicMock(spec=SummaryGenerator)
        generator.generate_summary = AsyncMock(
            return_value=GenerationResult(
                summary_id=1,
                content="This is a helpful summary.",
                tokens_used=50,
            )
        )
        return generator

    @pytest.mark.asyncio
    async def test_get_pending_matches_returns_matches_without_summaries(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test that only matches without summaries are returned."""
        pipeline = MatchPipeline(db_session)

        # Initially should find the match
        matches = await pipeline.get_pending_matches()
        assert len(matches) == 1
        assert matches[0].id == test_match.id

    @pytest.mark.asyncio
    async def test_get_pending_matches_excludes_matches_with_summaries(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test that matches with summaries are excluded."""
        # Add a summary to the match
        summary = DraftResponse(
            match_id=test_match.id,
            content="Existing summary",
            version=1,
        )
        db_session.add(summary)
        await db_session.flush()  # Flush to ensure it's written
        await db_session.commit()

        # Expire all to force re-fetch
        db_session.expire_all()

        pipeline = MatchPipeline(db_session)
        matches = await pipeline.get_pending_matches()

        # Should not find the match since it has a summary
        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_get_pending_matches_excludes_done_matches(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test that done matches are excluded."""
        test_match.status = MatchStatus.DONE.value
        await db_session.commit()

        pipeline = MatchPipeline(db_session)
        matches = await pipeline.get_pending_matches()

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_process_match_generates_summary(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
        mock_generator: MagicMock,
    ) -> None:
        """Test that processing a match generates an AI summary."""
        pipeline = MatchPipeline(db_session, generator=mock_generator)

        result = await pipeline.process_match(
            match=test_match,
            campaign=test_campaign,
            skip_notification=True,
        )

        assert result.ai_generated is True
        assert result.ai_content == "This is a helpful summary."
        assert result.ai_tokens == 50
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_process_match_handles_ai_error(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test that AI generation errors are handled."""
        from reddit_scout.ai.generator import SummaryGeneratorError

        mock_generator = MagicMock(spec=SummaryGenerator)
        mock_generator.generate_summary = AsyncMock(
            side_effect=SummaryGeneratorError("AI Error")
        )

        pipeline = MatchPipeline(db_session, generator=mock_generator)

        result = await pipeline.process_match(
            match=test_match,
            campaign=test_campaign,
            skip_notification=True,
        )

        assert result.ai_generated is False
        assert result.ai_content is None
        assert len(result.errors) > 0
        assert "AI generation failed" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_processes_all_pending_matches(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        mock_generator: MagicMock,
    ) -> None:
        """Test that run processes all pending matches."""
        # Create multiple matches
        for i in range(3):
            match = Match(
                campaign_id=test_campaign.id,
                reddit_id=f"t3_test{i}",
                reddit_type=RedditType.POST.value,
                subreddit="test",
                matched_keyword="help",
                title=f"Test post {i}",
                body_snippet="Content...",
                permalink=f"/r/test/comments/test{i}/",
                author="testuser",
                created_utc=datetime.now(UTC),
                status=MatchStatus.PENDING.value,
            )
            db_session.add(match)
        await db_session.commit()

        pipeline = MatchPipeline(db_session, generator=mock_generator)

        result = await pipeline.run(skip_notification=True)

        assert result.matches_processed == 3
        assert result.ai_generations_successful == 3
        assert result.ai_generations_failed == 0

    @pytest.mark.asyncio
    async def test_run_returns_empty_when_no_matches(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Test that run returns empty result when no matches."""
        pipeline = MatchPipeline(db_session)

        result = await pipeline.run(skip_notification=True)

        assert result.matches_processed == 0
        assert result.ai_generations_successful == 0


class TestMatchProcessingResult:
    """Tests for MatchProcessingResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a processing result."""
        result = MatchProcessingResult(
            match_id=1,
            ai_generated=True,
            ai_content="Response content",
            ai_tokens=50,
            notification_sent=False,
            discord_message_id=None,
            errors=[],
        )

        assert result.match_id == 1
        assert result.ai_generated is True
        assert result.ai_tokens == 50

    def test_result_with_errors(self) -> None:
        """Test result with errors."""
        result = MatchProcessingResult(
            match_id=1,
            ai_generated=False,
            ai_content=None,
            ai_tokens=0,
            notification_sent=False,
            discord_message_id=None,
            errors=["Error 1", "Error 2"],
        )

        assert len(result.errors) == 2


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a pipeline result."""
        result = PipelineResult(
            matches_processed=5,
            ai_generations_successful=4,
            ai_generations_failed=1,
            notifications_sent=3,
            notifications_failed=1,
            errors=["One error"],
            match_results=[],
        )

        assert result.matches_processed == 5
        assert result.ai_generations_successful == 4
        assert result.notifications_sent == 3
