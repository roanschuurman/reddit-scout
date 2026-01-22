"""Alert notification service."""

import logging
from dataclasses import dataclass

import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from community_scout.ai.client import ChatMessage, OpenRouterClient, OpenRouterError
from community_scout.config import settings
from community_scout.crypto import decrypt
from community_scout.models import (
    AlertStatus,
    ContentSource,
    DiscordUser,
    HNItem,
    SourceThread,
    UserAlert,
)

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """You are a helpful assistant that summarizes Hacker News content.
Given a title and optional text/URL, write a 1-2 sentence summary explaining what it is about.
Be concise and informative. Focus on the key points."""


@dataclass
class NotifyResult:
    """Result of notification processing."""

    alerts_processed: int
    alerts_sent: int
    alerts_failed: int


class AlertNotifier:
    """Service for sending alerts to Discord."""

    def __init__(
        self,
        session: AsyncSession,
        bot: discord.Client,
    ) -> None:
        """Initialize the notifier.

        Args:
            session: Database session
            bot: Discord bot instance
        """
        self.session = session
        self.bot = bot

    async def get_pending_alerts(self, limit: int = 50) -> list[UserAlert]:
        """Get pending alerts with related data loaded."""
        stmt = (
            select(UserAlert)
            .where(UserAlert.status == AlertStatus.PENDING.value)
            .options(
                selectinload(UserAlert.user),
                selectinload(UserAlert.item),
                selectinload(UserAlert.keyword),
                selectinload(UserAlert.source),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_or_create_source_thread(
        self,
        user: DiscordUser,
        source: ContentSource,
    ) -> str | None:
        """Get or create a Discord thread for the source.

        Returns the thread ID or None if creation failed.
        """
        # Check if thread exists
        stmt = select(SourceThread).where(
            SourceThread.user_id == user.id,
            SourceThread.source_id == source.id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing.thread_id

        # Create thread in user's channel
        try:
            channel = self.bot.get_channel(int(user.channel_id))
            if channel is None:
                channel = await self.bot.fetch_channel(int(user.channel_id))

            if not isinstance(channel, discord.TextChannel):
                logger.error("User channel %s is not a text channel", user.channel_id)
                return None

            # Create a thread
            thread = await channel.create_thread(
                name=f"🔔 {source.name.title()} Alerts",
                type=discord.ChannelType.public_thread,
            )

            # Save to database
            source_thread = SourceThread(
                user_id=user.id,
                source_id=source.id,
                thread_id=str(thread.id),
            )
            self.session.add(source_thread)
            await self.session.flush()

            logger.info(
                "Created thread %s for user %s source %s",
                thread.id,
                user.discord_username,
                source.name,
            )
            return str(thread.id)

        except discord.DiscordException as e:
            logger.error("Failed to create thread: %s", e)
            return None

    def get_user_api_key(self, user: DiscordUser) -> str | None:
        """Get decrypted API key for user, or None if not set."""
        if not user.openrouter_api_key:
            return None
        try:
            return decrypt(user.openrouter_api_key)
        except Exception as e:
            logger.warning("Failed to decrypt API key for user %s: %s", user.id, e)
            return None

    async def generate_summary(
        self,
        item: HNItem,
        api_key: str | None = None,
    ) -> str | None:
        """Generate AI summary for an HN item.

        Args:
            item: The HN item to summarize
            api_key: User's API key (uses default if None)

        Returns:
            Summary text or None if generation failed
        """
        # Use user's key or fall back to default
        key = api_key or settings.openrouter_api_key
        if not key:
            logger.warning("No API key available for summary generation")
            return None

        try:
            client = OpenRouterClient(api_key=key)

            # Build content to summarize
            content_parts = []
            if item.title:
                content_parts.append(f"Title: {item.title}")
            if item.text:
                # Truncate long text
                text = item.text[:1000] + "..." if len(item.text) > 1000 else item.text
                content_parts.append(f"Content: {text}")
            if item.url:
                content_parts.append(f"URL: {item.url}")

            content = "\n".join(content_parts)

            messages = [
                ChatMessage(role="system", content=SUMMARY_SYSTEM_PROMPT),
                ChatMessage(role="user", content=content),
            ]

            response = await client.chat(messages, max_tokens=150)
            return response.content.strip()

        except OpenRouterError as e:
            logger.error("Failed to generate summary: %s", e)
            return None

    def build_alert_embed(
        self,
        alert: UserAlert,
        summary: str | None,
    ) -> discord.Embed:
        """Build a Discord embed for an alert."""
        item = alert.item
        keyword = alert.keyword

        # Color based on item type
        color = discord.Color.orange() if item.item_type == "story" else discord.Color.blue()

        embed = discord.Embed(
            title=item.title or "Comment",
            url=item.hn_url,
            color=color,
        )

        # Add keyword match info
        embed.set_author(name=f"🔔 Keyword: {keyword.phrase}")

        # Add metadata
        meta_parts = [f"by {item.author}"]
        if item.score:
            meta_parts.append(f"{item.score} points")
        embed.add_field(name="Info", value=" · ".join(meta_parts), inline=False)

        # Add summary or fallback
        if summary:
            embed.add_field(name="AI Summary", value=summary, inline=False)
        elif item.text:
            # Show truncated text as fallback
            text = item.text[:300] + "..." if len(item.text) > 300 else item.text
            embed.add_field(name="Content", value=text, inline=False)

        embed.set_footer(text="Hacker News")

        return embed

    def build_alert_view(self, alert_id: int) -> discord.ui.View:
        """Build the interactive buttons for an alert."""
        view = AlertButtonView(alert_id)
        return view

    async def send_alert(self, alert: UserAlert) -> bool:
        """Send a single alert to Discord.

        Returns True if successful.
        """
        user = alert.user
        item = alert.item
        source = alert.source

        # Get or create thread
        thread_id = await self.get_or_create_source_thread(user, source)
        if not thread_id:
            logger.error("Could not get thread for alert %d", alert.id)
            return False

        try:
            thread = self.bot.get_channel(int(thread_id))
            if thread is None:
                thread = await self.bot.fetch_channel(int(thread_id))

            if not isinstance(thread, discord.Thread):
                logger.error("Channel %s is not a thread", thread_id)
                return False

            # Generate summary
            api_key = self.get_user_api_key(user)
            summary = await self.generate_summary(item, api_key)

            # Save summary to alert
            alert.summary = summary

            # Build message
            embed = self.build_alert_embed(alert, summary)
            view = self.build_alert_view(alert.id)

            # Send message
            message = await thread.send(embed=embed, view=view)

            # Update alert status
            alert.status = AlertStatus.SENT.value
            alert.discord_message_id = str(message.id)
            await self.session.flush()

            logger.info("Sent alert %d to thread %s", alert.id, thread_id)
            return True

        except discord.DiscordException as e:
            logger.error("Failed to send alert %d: %s", alert.id, e)
            return False

    async def process_pending_alerts(self, limit: int = 50) -> NotifyResult:
        """Process pending alerts.

        Args:
            limit: Maximum alerts to process

        Returns:
            NotifyResult with statistics
        """
        alerts = await self.get_pending_alerts(limit)
        logger.info("Processing %d pending alerts", len(alerts))

        sent = 0
        failed = 0

        for alert in alerts:
            try:
                success = await self.send_alert(alert)
                if success:
                    sent += 1
                else:
                    failed += 1
            except Exception as e:
                logger.exception("Error processing alert %d: %s", alert.id, e)
                failed += 1

        await self.session.commit()

        return NotifyResult(
            alerts_processed=len(alerts),
            alerts_sent=sent,
            alerts_failed=failed,
        )


class AlertButtonView(discord.ui.View):
    """Interactive buttons for alert messages."""

    def __init__(self, alert_id: int) -> None:
        super().__init__(timeout=None)  # Persistent view
        self.alert_id = alert_id

    @discord.ui.button(label="View on HN", style=discord.ButtonStyle.link, emoji="🔗")
    async def view_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        # Link buttons don't need a callback - URL is set dynamically
        pass

    @discord.ui.button(label="Regenerate", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def regenerate_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Regenerate the AI summary."""
        await interaction.response.defer(ephemeral=True)

        from community_scout.database import async_session_maker

        async with async_session_maker() as session:
            # Get alert with related data
            stmt = (
                select(UserAlert)
                .where(UserAlert.id == self.alert_id)
                .options(
                    selectinload(UserAlert.user),
                    selectinload(UserAlert.item),
                    selectinload(UserAlert.keyword),
                )
            )
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()

            if not alert:
                await interaction.followup.send("Alert not found.", ephemeral=True)
                return

            # Get user's API key
            api_key = None
            if alert.user.openrouter_api_key:
                try:
                    api_key = decrypt(alert.user.openrouter_api_key)
                except Exception:
                    pass

            # Generate new summary
            notifier = AlertNotifier(session, interaction.client)
            summary = await notifier.generate_summary(alert.item, api_key)

            if summary:
                alert.summary = summary
                await session.commit()

                # Update the message embed
                embed = notifier.build_alert_embed(alert, summary)
                await interaction.message.edit(embed=embed)  # type: ignore[union-attr]
                await interaction.followup.send("Summary regenerated!", ephemeral=True)
            else:
                await interaction.followup.send(
                    "Failed to regenerate summary. Check your API key.", ephemeral=True
                )

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def dismiss_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[discord.ui.View]
    ) -> None:
        """Dismiss the alert."""
        await interaction.response.defer(ephemeral=True)

        from community_scout.database import async_session_maker

        async with async_session_maker() as session:
            stmt = select(UserAlert).where(UserAlert.id == self.alert_id)
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()

            if alert:
                alert.status = AlertStatus.DISMISSED.value
                await session.commit()

        # Delete the message
        try:
            await interaction.message.delete()  # type: ignore[union-attr]
        except discord.DiscordException:
            await interaction.followup.send("Alert dismissed.", ephemeral=True)
