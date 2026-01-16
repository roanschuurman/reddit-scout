"""CLI runner for the Reddit scanner."""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime

from reddit_scout.database import async_session_maker
from reddit_scout.scanner.client import RedditClient
from reddit_scout.scanner.service import ScannerService


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the scanner."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def run_scanner(dry_run: bool = False, campaign_id: int | None = None) -> int:
    """
    Run the scanner.

    Args:
        dry_run: If True, don't save matches to database
        campaign_id: If provided, only scan this specific campaign

    Returns:
        Exit code (0 for success, 1 for errors)
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now(UTC)

    logger.info("=" * 60)
    logger.info("Reddit Scanner starting at %s", start_time.isoformat())
    logger.info("=" * 60)

    # Verify Reddit API connection
    reddit_client = RedditClient()
    try:
        reddit_client.verify_connection()
    except Exception as e:
        logger.error("Failed to connect to Reddit API: %s", e)
        return 1

    async with async_session_maker() as db:
        scanner = ScannerService(db, reddit_client)

        if campaign_id:
            # Scan specific campaign
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from reddit_scout.models.campaign import Campaign

            stmt = (
                select(Campaign)
                .where(Campaign.id == campaign_id)
                .options(
                    selectinload(Campaign.subreddits),
                    selectinload(Campaign.keywords),
                )
            )
            result = await db.execute(stmt)
            campaign = result.scalar_one_or_none()

            if not campaign:
                logger.error("Campaign with ID %d not found", campaign_id)
                return 1

            logger.info("Scanning single campaign: %s (ID: %d)", campaign.name, campaign.id)
            results = [await scanner.scan_campaign(campaign)]

            if not dry_run:
                await db.commit()
        else:
            # Scan all due campaigns
            if dry_run:
                campaigns = await scanner.get_campaigns_due_for_scan()
                logger.info("[DRY RUN] Would scan %d campaigns", len(campaigns))
                for c in campaigns:
                    logger.info("  - %s (ID: %d)", c.name, c.id)
                return 0
            else:
                results = await scanner.run_scan()

    # Print summary
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("Scanner completed in %.2f seconds", duration)

    total_matches = sum(r.new_matches for r in results)
    total_duplicates = sum(r.duplicates_skipped for r in results)
    total_errors = sum(len(r.errors) for r in results)

    logger.info("Campaigns scanned: %d", len(results))
    logger.info("New matches found: %d", total_matches)
    logger.info("Duplicates skipped: %d", total_duplicates)
    logger.info("Errors encountered: %d", total_errors)
    logger.info("=" * 60)

    if total_errors > 0:
        for r in results:
            if r.errors:
                logger.warning("Errors for campaign '%s': %s", r.campaign_name, r.errors)

    return 0 if total_errors == 0 else 1


def main() -> None:
    """Main entry point for the scanner CLI."""
    parser = argparse.ArgumentParser(description="Reddit Scout Scanner")
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be scanned without saving",
    )
    parser.add_argument(
        "--campaign-id",
        type=int,
        help="Scan only this specific campaign ID",
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    exit_code = asyncio.run(run_scanner(dry_run=args.dry_run, campaign_id=args.campaign_id))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
