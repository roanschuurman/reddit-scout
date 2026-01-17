"""Discord UI components (buttons, views) for match notifications."""

import logging
from datetime import UTC, datetime

import discord
from sqlalchemy import select

from reddit_scout.database import async_session_maker
from reddit_scout.models.match import Match, MatchStatus

logger = logging.getLogger(__name__)


class MatchActionView(discord.ui.View):
    """View with Done and Skip buttons for match notifications."""

    def __init__(self, match_id: int) -> None:
        """
        Initialize the view.

        Args:
            match_id: ID of the match this view is for
        """
        # Persistent views need timeout=None
        super().__init__(timeout=None)
        self.match_id = match_id

    @discord.ui.button(
        label="Done",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="match_done",
    )
    async def done_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Handle the Done button click."""
        await self._update_match_status(
            interaction,
            MatchStatus.DONE,
            "✅ Marked as done",
            discord.Color.green(),
        )

    @discord.ui.button(
        label="Skip",
        style=discord.ButtonStyle.secondary,
        emoji="⏭️",
        custom_id="match_skip",
    )
    async def skip_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Handle the Skip button click."""
        await self._update_match_status(
            interaction,
            MatchStatus.SKIPPED,
            "⏭️ Skipped",
            discord.Color.light_grey(),
        )

    async def _update_match_status(
        self,
        interaction: discord.Interaction,
        status: MatchStatus,
        status_text: str,
        color: discord.Color,
    ) -> None:
        """Update the match status in the database and update the message."""
        try:
            async with async_session_maker() as session:
                # Get the match
                result = await session.execute(
                    select(Match).where(Match.id == self.match_id)
                )
                match = result.scalar_one_or_none()

                if match is None:
                    await interaction.response.send_message(
                        "Match not found in database.",
                        ephemeral=True,
                    )
                    return

                # Update status
                match.status = status.value
                if status == MatchStatus.DONE:
                    match.completed_at = datetime.now(UTC)

                await session.commit()

                logger.info(
                    "Match %d status updated to %s by %s",
                    self.match_id,
                    status.value,
                    interaction.user,
                )

            # Update the message embed
            if interaction.message:
                embed = interaction.message.embeds[0] if interaction.message.embeds else None
                if embed:
                    # Create updated embed with status
                    updated_embed = discord.Embed(
                        title=embed.title,
                        description=embed.description,
                        color=color,
                    )
                    # Copy fields
                    for field in embed.fields:
                        updated_embed.add_field(
                            name=field.name,
                            value=field.value,
                            inline=field.inline,
                        )
                    # Add status field
                    updated_embed.add_field(
                        name="Status",
                        value=f"{status_text} by {interaction.user.mention}",
                        inline=False,
                    )
                    # Update timestamp
                    updated_embed.timestamp = datetime.now(UTC)

                    # Disable buttons
                    for item in self.children:
                        if isinstance(item, discord.ui.Button):
                            item.disabled = True

                    await interaction.response.edit_message(
                        embed=updated_embed,
                        view=self,
                    )
                else:
                    await interaction.response.send_message(
                        status_text,
                        ephemeral=True,
                    )
            else:
                await interaction.response.send_message(
                    status_text,
                    ephemeral=True,
                )

        except Exception as e:
            logger.exception("Error updating match status: %s", str(e))
            await interaction.response.send_message(
                f"Error updating match: {e}",
                ephemeral=True,
            )


def create_persistent_view(match_id: int) -> MatchActionView:
    """
    Create a persistent view for a match.

    Persistent views survive bot restarts if registered properly.

    Args:
        match_id: ID of the match

    Returns:
        MatchActionView instance
    """
    return MatchActionView(match_id)
