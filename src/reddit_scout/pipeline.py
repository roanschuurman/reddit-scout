"""Pipeline for processing matches: AI generation → Discord notification."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from reddit_scout.ai.generator import ResponseGenerator, ResponseGeneratorError
from reddit_scout.bot.notifications import send_match_notification
from reddit_scout.models.campaign import Campaign
from reddit_scout.models.match import Match, MatchStatus

if TYPE_CHECKING:
    from reddit_scout.ai.generator import GenerationResult

logger = logging.getLogger(__name__)


@dataclass
class MatchProcessingResult:
    """Result of processing a single match."""

    match_id: int
    ai_generated: bool
    ai_content: str | None
    ai_tokens: int
    notification_sent: bool
    discord_message_id: str | None
    errors: list[str]


@dataclass
class PipelineResult:
    """Result of running the pipeline."""

    matches_processed: int
    ai_generations_successful: int
    ai_generations_failed: int
    notifications_sent: int
    notifications_failed: int
    errors: list[str]
    match_results: list[MatchProcessingResult]


class MatchPipeline:
    """Pipeline for processing matches through AI generation and Discord notification."""

    def __init__(
        self,
        db: AsyncSession,
        generator: ResponseGenerator | None = None,
    ) -> None:
        """
        Initialize the pipeline.

        Args:
            db: Database session
            generator: Response generator (created if not provided)
        """
        self.db = db
        self.generator = generator or ResponseGenerator()

    async def get_pending_matches(self) -> list[Match]:
        """
        Get all pending matches that need processing.

        Returns:
            List of matches without AI drafts
        """
        stmt = (
            select(Match)
            .where(Match.status == MatchStatus.PENDING.value)
            .options(selectinload(Match.draft_responses))
            .order_by(Match.discovered_at)
        )
        result = await self.db.execute(stmt)
        matches = result.scalars().all()

        # Filter to only matches without drafts
        return [m for m in matches if not m.draft_responses]

    async def process_match(
        self,
        match: Match,
        campaign: Campaign,
        skip_notification: bool = False,
    ) -> MatchProcessingResult:
        """
        Process a single match: generate AI draft and send notification.

        Args:
            match: Match to process
            campaign: Campaign the match belongs to
            skip_notification: If True, skip Discord notification

        Returns:
            MatchProcessingResult with processing details
        """
        result = MatchProcessingResult(
            match_id=match.id,
            ai_generated=False,
            ai_content=None,
            ai_tokens=0,
            notification_sent=False,
            discord_message_id=None,
            errors=[],
        )

        # Step 1: Generate AI draft
        gen_result: GenerationResult | None = None
        try:
            gen_result = await self.generator.generate_response(
                session=self.db,
                match=match,
                campaign=campaign,
            )
            result.ai_generated = True
            result.ai_content = gen_result.content
            result.ai_tokens = gen_result.tokens_used
            logger.info(
                "Generated AI draft for match %d (%d tokens)",
                match.id,
                gen_result.tokens_used,
            )
        except ResponseGeneratorError as e:
            error_msg = f"AI generation failed: {e}"
            result.errors.append(error_msg)
            logger.error("AI generation failed for match %d: %s", match.id, str(e))

        # Step 2: Send Discord notification (if we have a channel and draft)
        if not skip_notification and campaign.discord_channel_id and result.ai_generated:
            notification_result = await send_match_notification(
                match=match,
                channel_id=campaign.discord_channel_id,
                draft_content=result.ai_content,
            )

            if notification_result.success:
                result.notification_sent = True
                result.discord_message_id = notification_result.message_id

                # Update match with discord message ID
                match.discord_message_id = notification_result.message_id

                logger.info(
                    "Sent Discord notification for match %d (message: %s)",
                    match.id,
                    notification_result.message_id,
                )
            else:
                error_msg = f"Discord notification failed: {notification_result.error}"
                result.errors.append(error_msg)
                logger.error(
                    "Failed to send Discord notification for match %d: %s",
                    match.id,
                    notification_result.error,
                )
        elif not campaign.discord_channel_id:
            logger.debug(
                "Skipping notification for match %d: no Discord channel configured",
                match.id,
            )
        elif not result.ai_generated:
            logger.debug(
                "Skipping notification for match %d: AI generation failed",
                match.id,
            )

        return result

    async def run(self, skip_notification: bool = False) -> PipelineResult:
        """
        Run the pipeline for all pending matches.

        Args:
            skip_notification: If True, skip Discord notifications

        Returns:
            PipelineResult with processing statistics
        """
        result = PipelineResult(
            matches_processed=0,
            ai_generations_successful=0,
            ai_generations_failed=0,
            notifications_sent=0,
            notifications_failed=0,
            errors=[],
            match_results=[],
        )

        # Get pending matches
        matches = await self.get_pending_matches()
        if not matches:
            logger.info("No pending matches to process")
            return result

        logger.info("Found %d pending matches to process", len(matches))

        # Get campaigns for all matches
        campaign_ids = {m.campaign_id for m in matches}
        campaigns_stmt = (
            select(Campaign)
            .where(Campaign.id.in_(campaign_ids))
        )
        campaigns_result = await self.db.execute(campaigns_stmt)
        campaigns = {c.id: c for c in campaigns_result.scalars().all()}

        # Process each match
        for match in matches:
            campaign = campaigns.get(match.campaign_id)
            if not campaign:
                error_msg = f"Campaign {match.campaign_id} not found for match {match.id}"
                result.errors.append(error_msg)
                logger.error(error_msg)
                continue

            match_result = await self.process_match(
                match=match,
                campaign=campaign,
                skip_notification=skip_notification,
            )
            result.match_results.append(match_result)
            result.matches_processed += 1

            if match_result.ai_generated:
                result.ai_generations_successful += 1
            else:
                result.ai_generations_failed += 1

            if match_result.notification_sent:
                result.notifications_sent += 1
            elif campaign.discord_channel_id and match_result.ai_generated:
                # Only count as failed if we should have sent but didn't
                result.notifications_failed += 1

            result.errors.extend(match_result.errors)

        # Commit all changes
        await self.db.commit()

        logger.info(
            "Pipeline complete: %d matches processed, %d AI drafts, %d notifications sent",
            result.matches_processed,
            result.ai_generations_successful,
            result.notifications_sent,
        )

        return result


async def process_new_matches(
    db: AsyncSession,
    skip_notification: bool = False,
) -> PipelineResult:
    """
    Convenience function to process all pending matches.

    Args:
        db: Database session
        skip_notification: If True, skip Discord notifications

    Returns:
        PipelineResult with processing statistics
    """
    pipeline = MatchPipeline(db)
    return await pipeline.run(skip_notification=skip_notification)
