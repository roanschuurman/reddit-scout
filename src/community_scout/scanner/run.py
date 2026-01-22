"""Scanner CLI entry point.

Run with: python -m community_scout.scanner.run
"""

import asyncio
import logging
import signal
import sys
from datetime import UTC, datetime

from community_scout.config import settings
from community_scout.database import async_session_maker
from community_scout.hn.client import HNClient
from community_scout.scanner.hn_scanner import HNScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ScannerRunner:
    """Runs the HN scanner on a configured interval."""

    def __init__(self, interval_minutes: int = 5) -> None:
        """Initialize the runner.

        Args:
            interval_minutes: Minutes between scans
        """
        self.interval_minutes = interval_minutes
        self._shutdown = False

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        logger.info("Shutdown requested")
        self._shutdown = True

    async def run_once(self) -> None:
        """Run a single scan."""
        logger.info("Starting scan at %s", datetime.now(UTC).isoformat())

        async with HNClient() as hn_client:
            async with async_session_maker() as session:
                scanner = HNScanner(session, hn_client)
                try:
                    result = await scanner.scan()
                    logger.info(
                        "Scan complete: scanned=%d stored=%d alerts=%d",
                        result.items_scanned,
                        result.items_stored,
                        result.alerts_created,
                    )
                except Exception:
                    logger.exception("Scan failed")
                    raise

    async def run_loop(self) -> None:
        """Run continuous scan loop."""
        logger.info(
            "Starting scanner with %d minute interval",
            self.interval_minutes,
        )

        while not self._shutdown:
            try:
                await self.run_once()
            except Exception:
                logger.exception("Scan iteration failed, will retry next interval")

            if self._shutdown:
                break

            # Wait for next interval
            logger.info("Sleeping for %d minutes...", self.interval_minutes)
            for _ in range(self.interval_minutes * 60):
                if self._shutdown:
                    break
                await asyncio.sleep(1)

        logger.info("Scanner stopped")


async def main() -> None:
    """Main entry point."""
    runner = ScannerRunner(interval_minutes=settings.hn_scan_interval_minutes)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        runner.request_shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    await runner.run_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)
