"""Notifier CLI entry point.

Run with: python -m community_scout.notifier.run
"""

import asyncio
import logging
import signal
import sys

import discord

from community_scout.config import settings
from community_scout.database import async_session_maker
from community_scout.notifier.alert_notifier import AlertButtonView, AlertNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# How often to check for pending alerts (seconds)
NOTIFY_INTERVAL_SECONDS = 30


class NotifierBot(discord.Client):
    """Minimal Discord client for sending notifications."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self._shutdown = False
        self._ready = asyncio.Event()

    async def on_ready(self) -> None:
        logger.info("Notifier bot connected as %s", self.user)
        # Register persistent views for button interactions
        self.add_view(AlertButtonView(alert_id=0))  # Template for persistent buttons
        self._ready.set()

    async def wait_until_ready_custom(self) -> None:
        """Wait until the bot is ready."""
        await self._ready.wait()

    def request_shutdown(self) -> None:
        self._shutdown = True

    async def run_notifier_loop(self) -> None:
        """Run the notification loop."""
        await self.wait_until_ready_custom()
        logger.info("Starting notifier loop (interval: %ds)", NOTIFY_INTERVAL_SECONDS)

        while not self._shutdown:
            try:
                async with async_session_maker() as session:
                    notifier = AlertNotifier(session, self)
                    result = await notifier.process_pending_alerts()

                    if result.alerts_processed > 0:
                        logger.info(
                            "Processed %d alerts: %d sent, %d failed",
                            result.alerts_processed,
                            result.alerts_sent,
                            result.alerts_failed,
                        )
            except Exception:
                logger.exception("Error in notifier loop")

            # Wait for next interval
            for _ in range(NOTIFY_INTERVAL_SECONDS):
                if self._shutdown:
                    break
                await asyncio.sleep(1)

        logger.info("Notifier loop stopped")


async def main() -> None:
    """Main entry point."""
    if not settings.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN not configured")
        sys.exit(1)

    bot = NotifierBot()

    # Set up signal handlers
    loop = asyncio.get_running_loop()

    def signal_handler() -> None:
        logger.info("Shutdown signal received")
        bot.request_shutdown()
        # Schedule close after a short delay to allow cleanup
        loop.create_task(shutdown(bot))

    async def shutdown(bot: NotifierBot) -> None:
        await asyncio.sleep(1)
        await bot.close()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start the bot and notifier loop
    async with bot:
        bot_task = asyncio.create_task(bot.start(settings.discord_bot_token))
        notifier_task = asyncio.create_task(bot.run_notifier_loop())

        try:
            await asyncio.gather(bot_task, notifier_task)
        except asyncio.CancelledError:
            logger.info("Tasks cancelled")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(0)
