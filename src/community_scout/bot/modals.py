"""Discord UI modals for Community Scout."""

import logging

import discord
from sqlalchemy import select

from community_scout.crypto import encrypt
from community_scout.database import async_session_maker
from community_scout.models import DiscordUser

logger = logging.getLogger(__name__)


class APIKeyModal(discord.ui.Modal, title="Set OpenRouter API Key"):
    """Modal for entering OpenRouter API key."""

    api_key: discord.ui.TextInput[discord.ui.Modal] = discord.ui.TextInput(
        label="API Key",
        placeholder="sk-or-v1-...",
        style=discord.TextStyle.short,
        required=True,
        min_length=10,
        max_length=200,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        key_value = self.api_key.value.strip()

        # Basic validation
        if not key_value.startswith("sk-"):
            await interaction.response.send_message(
                "Invalid API key format. OpenRouter keys typically start with `sk-`.",
                ephemeral=True,
            )
            return

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

            # Encrypt and store
            encrypted_key = encrypt(key_value)
            user.openrouter_api_key = encrypted_key
            await session.commit()

            logger.info("User %s configured their API key", interaction.user.name)
            await interaction.response.send_message(
                "Your API key has been securely saved. "
                "AI summaries will now use your personal key.",
                ephemeral=True,
            )

    async def on_error(  # type: ignore[override]
        self, interaction: discord.Interaction, error: Exception, /
    ) -> None:
        """Handle errors in the modal."""
        logger.exception("Error in API key modal: %s", error)
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "Something went wrong while saving your API key. Please try again.",
                ephemeral=True,
            )
