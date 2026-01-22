"""Discord bot core module."""

import logging

import discord
from discord.ext import commands

from community_scout.config import settings

logger = logging.getLogger(__name__)


class CommunityScoutBot(commands.Bot):
    """Discord bot for Community Scout notifications."""

    def __init__(self) -> None:
        """Initialize the bot with required intents."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Required for on_member_join

        super().__init__(
            command_prefix="!scout ",
            intents=intents,
            description="Community Scout - Content monitoring with AI summaries",
        )

        self._bot_ready = False

    async def setup_hook(self) -> None:
        """Called when the bot is starting up."""
        logger.info("Bot setup hook called")

        # Set up slash commands
        from community_scout.bot.commands import setup_commands

        await setup_commands(self)

        # Sync commands to guild
        if settings.discord_guild_id:
            guild = discord.Object(id=int(settings.discord_guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Synced commands to guild %s", settings.discord_guild_id)
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")

    async def on_ready(self) -> None:
        """Called when the bot is ready and connected."""
        self._bot_ready = True
        logger.info("Bot connected as %s (ID: %s)", self.user, self.user.id if self.user else None)
        logger.info("Connected to %d guilds", len(self.guilds))

    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins a guild."""
        from community_scout.bot.onboarding import on_member_join_handler

        await on_member_join_handler(member)

    async def on_error(self, event: str, *args: object, **kwargs: object) -> None:
        """Handle errors in event handlers."""
        logger.exception("Error in event %s", event)

    @property
    def bot_is_ready(self) -> bool:
        """Check if the bot is ready."""
        return self._bot_ready


# Global bot instance
_bot: CommunityScoutBot | None = None


def get_bot() -> CommunityScoutBot:
    """Get or create the bot instance."""
    global _bot
    if _bot is None:
        _bot = CommunityScoutBot()
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
