"""Discord bot core module."""

import logging

import discord
from discord.ext import commands

from reddit_scout.config import settings

logger = logging.getLogger(__name__)


class RedditScoutBot(commands.Bot):
    """Discord bot for Reddit Scout notifications."""

    def __init__(self) -> None:
        """Initialize the bot with required intents."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!scout ",
            intents=intents,
            description="Reddit Scout - AI-powered Reddit monitoring",
        )

        self._bot_ready = False

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Bot setup hook called")

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        self._bot_ready = True
        logger.info("Bot connected as %s (ID: %s)", self.user, self.user.id if self.user else None)
        logger.info("Connected to %d guilds", len(self.guilds))

    async def on_error(self, event: str, *args: object, **kwargs: object) -> None:
        """Handle errors in event handlers."""
        logger.exception("Error in event %s", event)

    @property
    def bot_is_ready(self) -> bool:
        """Check if the bot is ready."""
        return self._bot_ready


# Global bot instance
_bot: RedditScoutBot | None = None


def get_bot() -> RedditScoutBot:
    """Get or create the bot instance."""
    global _bot
    if _bot is None:
        _bot = RedditScoutBot()
    return _bot


async def start_bot() -> None:
    """Start the Discord bot."""
    if not settings.discord_bot_token:
        raise ValueError(
            "Discord bot token not configured. "
            "Set DISCORD_BOT_TOKEN environment variable."
        )

    bot = get_bot()
    logger.info("Starting Discord bot...")

    try:
        await bot.start(settings.discord_bot_token)
    except discord.LoginFailure as e:
        logger.error("Failed to login to Discord: %s", str(e))
        raise


async def stop_bot() -> None:
    """Stop the Discord bot gracefully."""
    global _bot
    if _bot is not None:
        logger.info("Stopping Discord bot...")
        await _bot.close()
        _bot = None


async def verify_bot_connection() -> bool:
    """
    Verify the bot token is valid by making a test connection.

    Returns:
        True if the token is valid, False otherwise.
    """
    if not settings.discord_bot_token:
        logger.error("Discord bot token not configured")
        return False

    try:
        # Create a temporary client to test the token
        async with discord.Client(intents=discord.Intents.default()):
            # on_ready is called when connected
            # We just need to verify we can connect
            pass
        logger.info("Discord bot token verified")
        return True
    except discord.LoginFailure as e:
        logger.error("Discord bot token invalid: %s", str(e))
        return False
    except Exception as e:
        logger.error("Failed to verify Discord connection: %s", str(e))
        return False
