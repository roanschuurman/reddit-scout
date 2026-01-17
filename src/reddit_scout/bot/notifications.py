"""Discord notification service for matches."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import discord

from reddit_scout.bot.bot import get_bot
from reddit_scout.bot.views import MatchActionView
from reddit_scout.models.match import Match, RedditType

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of sending a notification."""

    success: bool
    message_id: str | None = None
    error: str | None = None


def _format_time_ago(dt: datetime) -> str:
    """Format a datetime as 'X hours ago' style string."""
    now = datetime.now(UTC)
    # Ensure both are timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"


def _truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def build_match_embed(match: Match, draft_content: str | None = None) -> discord.Embed:
    """
    Build a Discord embed for a match notification.

    Args:
        match: The match to create an embed for
        draft_content: Optional AI draft response to include

    Returns:
        Discord Embed object

    Embed structure:
    ┌─────────────────────────────────────────┐
    │ 🔍 New Match in r/subreddit             │
    ├─────────────────────────────────────────┤
    │ **Post:** Title of the post...          │
    │ **Author:** u/username • 2 hours ago    │
    │ **Keyword:** "matched phrase"           │
    │                                         │
    │ > Snippet of the matched content...     │
    │                                         │
    │ **📝 AI Draft:**                        │
    │ Generated response text here...         │
    │                                         │
    │ [View on Reddit ↗]                      │
    └─────────────────────────────────────────┘
    """
    # Determine content type
    is_post = match.reddit_type == RedditType.POST.value
    type_label = "Post" if is_post else "Comment"
    type_emoji = "📝" if is_post else "💬"

    # Create embed
    embed = discord.Embed(
        title=f"🔍 New Match in r/{match.subreddit}",
        color=discord.Color.blue(),
        timestamp=datetime.now(UTC),
    )

    # Title/context field
    if match.title:
        embed.add_field(
            name=f"{type_emoji} {type_label}",
            value=_truncate(match.title, 200),
            inline=False,
        )

    # Author and time
    time_ago = _format_time_ago(match.created_utc)
    embed.add_field(
        name="Author",
        value=f"u/{match.author} • {time_ago}",
        inline=True,
    )

    # Matched keyword
    embed.add_field(
        name="Keyword",
        value=f'"{match.matched_keyword}"',
        inline=True,
    )

    # Content snippet
    if match.body_snippet:
        snippet = _truncate(match.body_snippet, 500)
        embed.add_field(
            name="Content",
            value=f"> {snippet}",
            inline=False,
        )

    # AI Draft
    if draft_content:
        draft_display = _truncate(draft_content, 1000)
        embed.add_field(
            name="📝 AI Draft",
            value=draft_display,
            inline=False,
        )

    # Reddit link
    reddit_url = f"https://reddit.com{match.permalink}"
    embed.add_field(
        name="Link",
        value=f"[View on Reddit ↗]({reddit_url})",
        inline=False,
    )

    # Footer
    embed.set_footer(text=f"Match ID: {match.id}")

    return embed


async def send_match_notification(
    match: Match,
    channel_id: str,
    draft_content: str | None = None,
) -> NotificationResult:
    """
    Send a match notification to a Discord channel.

    Args:
        match: The match to notify about
        channel_id: Discord channel ID to send to
        draft_content: Optional AI draft response to include

    Returns:
        NotificationResult with success status and message ID
    """
    bot = get_bot()

    if not bot.bot_is_ready:
        return NotificationResult(
            success=False,
            error="Bot is not connected to Discord",
        )

    try:
        # Get the channel
        channel_id_int = int(channel_id)
        channel = bot.get_channel(channel_id_int)

        if channel is None:
            # Try to fetch it
            try:
                channel = await bot.fetch_channel(channel_id_int)
            except discord.NotFound:
                return NotificationResult(
                    success=False,
                    error=f"Channel {channel_id} not found",
                )
            except discord.Forbidden:
                return NotificationResult(
                    success=False,
                    error=f"Bot does not have access to channel {channel_id}",
                )

        if not isinstance(channel, discord.TextChannel):
            return NotificationResult(
                success=False,
                error=f"Channel {channel_id} is not a text channel",
            )

        # Build the embed
        embed = build_match_embed(match, draft_content)

        # Create the view with buttons
        view = MatchActionView(match.id)

        # Send the message
        message = await channel.send(embed=embed, view=view)

        logger.info(
            "Sent notification for match %d to channel %s (message %s)",
            match.id,
            channel_id,
            message.id,
        )

        return NotificationResult(
            success=True,
            message_id=str(message.id),
        )

    except discord.Forbidden:
        return NotificationResult(
            success=False,
            error=f"Bot lacks permission to send messages to channel {channel_id}",
        )
    except discord.HTTPException as e:
        logger.error("Discord HTTP error sending notification: %s", str(e))
        return NotificationResult(
            success=False,
            error=f"Discord API error: {e}",
        )
    except Exception as e:
        logger.exception("Unexpected error sending notification: %s", str(e))
        return NotificationResult(
            success=False,
            error=f"Unexpected error: {e}",
        )
