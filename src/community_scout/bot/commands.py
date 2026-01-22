"""Discord slash commands for Community Scout."""

import logging

import discord
from discord import app_commands
from sqlalchemy import select

from community_scout.database import async_session_maker
from community_scout.models import DiscordUser, UserKeyword

logger = logging.getLogger(__name__)

MAX_KEYWORD_LENGTH = 100
MAX_KEYWORDS_PER_USER = 50


class KeywordGroup(app_commands.Group):
    """Commands for managing keywords to monitor."""

    def __init__(self) -> None:
        super().__init__(name="keyword", description="Manage keywords to monitor")

    @app_commands.command(name="add", description="Add a keyword to monitor")
    @app_commands.describe(phrase="The keyword or phrase to monitor (max 100 chars)")
    async def add(self, interaction: discord.Interaction, phrase: str) -> None:
        """Add a keyword to monitor."""
        # Validate input
        phrase = phrase.strip()
        if not phrase:
            await interaction.response.send_message(
                "Keyword cannot be empty.", ephemeral=True
            )
            return

        if len(phrase) > MAX_KEYWORD_LENGTH:
            await interaction.response.send_message(
                f"Keyword too long. Maximum is {MAX_KEYWORD_LENGTH} characters.",
                ephemeral=True,
            )
            return

        async with async_session_maker() as session:
            # Get user
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet. Please wait for your channel to be created.",
                    ephemeral=True,
                )
                return

            # Check for duplicates
            result = await session.execute(
                select(UserKeyword).where(
                    UserKeyword.user_id == user.id,
                    UserKeyword.phrase.ilike(phrase),
                    UserKeyword.is_active == True,  # noqa: E712
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                await interaction.response.send_message(
                    f"You're already monitoring **{phrase}**.", ephemeral=True
                )
                return

            # Check keyword count
            result = await session.execute(
                select(UserKeyword).where(
                    UserKeyword.user_id == user.id,
                    UserKeyword.is_active == True,  # noqa: E712
                )
            )
            keywords = result.scalars().all()

            if len(keywords) >= MAX_KEYWORDS_PER_USER:
                await interaction.response.send_message(
                    f"You've reached the maximum of {MAX_KEYWORDS_PER_USER} keywords. "
                    "Remove some before adding more.",
                    ephemeral=True,
                )
                return

            # Add keyword
            keyword = UserKeyword(user_id=user.id, phrase=phrase, is_active=True)
            session.add(keyword)
            await session.commit()

            logger.info(
                "User %s added keyword: %s", interaction.user.name, phrase
            )
            await interaction.response.send_message(
                f"Now monitoring **{phrase}**.", ephemeral=True
            )

    @app_commands.command(name="remove", description="Remove a monitored keyword")
    @app_commands.describe(phrase="The keyword or phrase to stop monitoring")
    async def remove(self, interaction: discord.Interaction, phrase: str) -> None:
        """Remove a keyword from monitoring."""
        phrase = phrase.strip()
        if not phrase:
            await interaction.response.send_message(
                "Please specify a keyword to remove.", ephemeral=True
            )
            return

        async with async_session_maker() as session:
            # Get user
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            # Find keyword
            result = await session.execute(
                select(UserKeyword).where(
                    UserKeyword.user_id == user.id,
                    UserKeyword.phrase.ilike(phrase),
                    UserKeyword.is_active == True,  # noqa: E712
                )
            )
            keyword = result.scalar_one_or_none()

            if not keyword:
                await interaction.response.send_message(
                    f"You're not monitoring **{phrase}**.", ephemeral=True
                )
                return

            # Deactivate keyword
            keyword.is_active = False
            await session.commit()

            logger.info(
                "User %s removed keyword: %s", interaction.user.name, phrase
            )
            await interaction.response.send_message(
                f"Stopped monitoring **{phrase}**.", ephemeral=True
            )

    @app_commands.command(name="list", description="List all your monitored keywords")
    async def list_keywords(self, interaction: discord.Interaction) -> None:
        """List all monitored keywords."""
        async with async_session_maker() as session:
            # Get user
            user_result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = user_result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            # Get keywords
            kw_result = await session.execute(
                select(UserKeyword)
                .where(
                    UserKeyword.user_id == user.id,
                    UserKeyword.is_active == True,  # noqa: E712
                )
                .order_by(UserKeyword.created_at)
            )
            keywords = kw_result.scalars().all()

            if not keywords:
                await interaction.response.send_message(
                    "You're not monitoring any keywords yet.\n"
                    "Add one with `/keyword add <phrase>`",
                    ephemeral=True,
                )
                return

            keyword_list = "\n".join(
                f"- **{kw.phrase}** (added {kw.created_at.strftime('%Y-%m-%d')})"
                for kw in keywords
            )
            await interaction.response.send_message(
                f"**Your monitored keywords ({len(keywords)}):**\n{keyword_list}",
                ephemeral=True,
            )


class APIKeyGroup(app_commands.Group):
    """Commands for managing OpenRouter API key."""

    def __init__(self) -> None:
        super().__init__(name="apikey", description="Manage your OpenRouter API key")

    @app_commands.command(name="set", description="Set your OpenRouter API key for AI summaries")
    async def set_key(self, interaction: discord.Interaction) -> None:
        """Open modal to set API key."""
        from community_scout.bot.modals import APIKeyModal

        await interaction.response.send_modal(APIKeyModal())

    @app_commands.command(name="status", description="Check if your API key is configured")
    async def status(self, interaction: discord.Interaction) -> None:
        """Check API key status."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            if user.openrouter_api_key:
                await interaction.response.send_message(
                    "Your OpenRouter API key is configured. "
                    "AI summaries will use your personal key.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "No API key configured. "
                    "Set one with `/apikey set` for personalized AI summaries.",
                    ephemeral=True,
                )

    @app_commands.command(name="remove", description="Remove your stored API key")
    async def remove(self, interaction: discord.Interaction) -> None:
        """Remove stored API key."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            if not user.openrouter_api_key:
                await interaction.response.send_message(
                    "You don't have an API key configured.", ephemeral=True
                )
                return

            user.openrouter_api_key = None
            await session.commit()

            logger.info("User %s removed their API key", interaction.user.name)
            await interaction.response.send_message(
                "Your API key has been removed.", ephemeral=True
            )


async def setup_commands(bot: "discord.ext.commands.Bot") -> None:
    """Set up all command groups on the bot."""
    bot.tree.add_command(KeywordGroup())
    bot.tree.add_command(APIKeyGroup())

    @bot.tree.command(name="status", description="Show your Community Scout configuration")
    async def status_command(interaction: discord.Interaction) -> None:
        """Show user's configuration status."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet. Please wait for your channel to be created.",
                    ephemeral=True,
                )
                return

            # Get keyword count
            result = await session.execute(
                select(UserKeyword).where(
                    UserKeyword.user_id == user.id,
                    UserKeyword.is_active == True,  # noqa: E712
                )
            )
            keywords = result.scalars().all()

            api_status = "Configured" if user.openrouter_api_key else "Not configured"
            notif_status = "Active" if user.is_active else "Paused"

            embed = discord.Embed(
                title="Community Scout Status",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Keywords", value=str(len(keywords)), inline=True)
            embed.add_field(name="API Key", value=api_status, inline=True)
            embed.add_field(name="Notifications", value=notif_status, inline=True)
            embed.add_field(
                name="Channel",
                value=f"<#{user.channel_id}>",
                inline=False,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @bot.tree.command(name="pause", description="Pause notifications")
    async def pause_command(interaction: discord.Interaction) -> None:
        """Pause notifications for the user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            if not user.is_active:
                await interaction.response.send_message(
                    "Notifications are already paused.", ephemeral=True
                )
                return

            user.is_active = False
            await session.commit()

            logger.info("User %s paused notifications", interaction.user.name)
            await interaction.response.send_message(
                "Notifications paused. Use `/resume` to start receiving them again.",
                ephemeral=True,
            )

    @bot.tree.command(name="resume", description="Resume notifications")
    async def resume_command(interaction: discord.Interaction) -> None:
        """Resume notifications for the user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(DiscordUser).where(
                    DiscordUser.discord_id == str(interaction.user.id)
                )
            )
            user = result.scalar_one_or_none()

            if not user:
                await interaction.response.send_message(
                    "You're not set up yet.", ephemeral=True
                )
                return

            if user.is_active:
                await interaction.response.send_message(
                    "Notifications are already active.", ephemeral=True
                )
                return

            user.is_active = True
            await session.commit()

            logger.info("User %s resumed notifications", interaction.user.name)
            await interaction.response.send_message(
                "Notifications resumed! You'll now receive alerts for your keywords.",
                ephemeral=True,
            )
