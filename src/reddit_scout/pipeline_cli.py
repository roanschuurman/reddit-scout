"""CLI runner for the match processing pipeline."""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

from reddit_scout.ai.client import OpenRouterClient
from reddit_scout.bot.bot import get_bot, start_bot, stop_bot
from reddit_scout.config import settings
from reddit_scout.database import async_session_maker
from reddit_scout.pipeline import MatchPipeline


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the pipeline."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Reduce noise from httpx and discord
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("discord").setLevel(logging.WARNING)


async def verify_services(skip_notification: bool = False) -> bool:
    """Verify that required services are available."""
    logger = logging.getLogger(__name__)

    # Check OpenRouter
    if not settings.openrouter_api_key:
        logger.error("OpenRouter API key not configured (OPENROUTER_API_KEY)")
        return False

    try:
        client = OpenRouterClient()
        if not await client.verify_connection():
            logger.error("Failed to verify OpenRouter connection")
            return False
        logger.info("OpenRouter connection verified")
    except Exception as e:
        logger.error("OpenRouter connection failed: %s", str(e))
        return False

    # Check Discord (if not skipping notifications)
    if not skip_notification:
        if not settings.discord_bot_token:
            logger.warning(
                "Discord bot token not configured (DISCORD_BOT_TOKEN). "
                "Notifications will be skipped."
            )
        else:
            logger.info("Discord bot token configured")

    return True


async def run_pipeline(
    dry_run: bool = False,
    skip_notification: bool = False,
    with_bot: bool = False,
) -> int:
    """
    Run the match processing pipeline.

    Args:
        dry_run: If True, show what would be processed without actually doing it
        skip_notification: If True, skip Discord notifications
        with_bot: If True, start the Discord bot before processing

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now(UTC)

    logger.info("=" * 60)
    logger.info("Match Pipeline starting at %s", start_time.isoformat())
    logger.info("=" * 60)

    # Verify services
    if not await verify_services(skip_notification):
        return 1

    # Start Discord bot if requested
    bot_task = None
    if with_bot and settings.discord_bot_token and not skip_notification:
        logger.info("Starting Discord bot...")
        bot_task = asyncio.create_task(start_bot())
        # Give the bot time to connect
        await asyncio.sleep(3)

        bot = get_bot()
        if not bot.bot_is_ready:
            logger.warning("Discord bot not ready yet, waiting...")
            for _ in range(10):  # Wait up to 10 more seconds
                await asyncio.sleep(1)
                if bot.bot_is_ready:
                    break

            if not bot.bot_is_ready:
                logger.error("Discord bot failed to connect")
                if bot_task:
                    bot_task.cancel()
                return 1

        logger.info("Discord bot connected")

    try:
        async with async_session_maker() as db:
            pipeline = MatchPipeline(db)

            if dry_run:
                # Just show what would be processed
                matches = await pipeline.get_pending_matches()
                logger.info("[DRY RUN] Would process %d pending matches:", len(matches))
                for match in matches:
                    logger.info(
                        "  - Match %d: r/%s (keyword: %s)",
                        match.id,
                        match.subreddit,
                        match.matched_keyword,
                    )
                return 0

            # Run the pipeline
            result = await pipeline.run(skip_notification=skip_notification)

        # Print summary
        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        logger.info("=" * 60)
        logger.info("Pipeline completed in %.2f seconds", duration)
        logger.info("Matches processed: %d", result.matches_processed)
        logger.info("AI drafts generated: %d", result.ai_generations_successful)
        logger.info("AI generation failures: %d", result.ai_generations_failed)
        logger.info("Discord notifications sent: %d", result.notifications_sent)
        logger.info("Discord notification failures: %d", result.notifications_failed)
        logger.info("=" * 60)

        if result.errors:
            logger.warning("Errors encountered:")
            for error in result.errors[:10]:  # Show first 10 errors
                logger.warning("  - %s", error)
            if len(result.errors) > 10:
                logger.warning("  ... and %d more errors", len(result.errors) - 10)

        return 0 if result.ai_generations_failed == 0 else 1

    finally:
        # Stop the bot if we started it
        if bot_task:
            logger.info("Stopping Discord bot...")
            await stop_bot()
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass


def main() -> None:
    """Main entry point for the pipeline CLI."""
    parser = argparse.ArgumentParser(
        description="Reddit Scout Match Pipeline - Process matches with AI and Discord"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without doing it",
    )
    parser.add_argument(
        "--skip-notification",
        action="store_true",
        help="Skip Discord notifications (only generate AI drafts)",
    )
    parser.add_argument(
        "--with-bot",
        action="store_true",
        help="Start Discord bot for sending notifications (auto-stops after)",
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    exit_code = asyncio.run(
        run_pipeline(
            dry_run=args.dry_run,
            skip_notification=args.skip_notification,
            with_bot=args.with_bot,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
