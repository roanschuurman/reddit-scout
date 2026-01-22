"""Discord member onboarding for Community Scout."""

import logging

import discord
from sqlalchemy import select

from community_scout.config import settings
from community_scout.database import async_session_maker
from community_scout.models import ContentSource, DiscordUser, SourceThread

logger = logging.getLogger(__name__)

WELCOME_MESSAGE = """Welcome to Community Scout!

I'll monitor Hacker News for topics you care about and notify you here.

**Get started:**
1. Add keywords: `/keyword add python`
2. (Optional) Add your API key for AI summaries: `/apikey set`
3. Check your config: `/status`

Your alerts will appear in the thread below. Happy monitoring!"""


async def create_user_channel(
    guild: discord.Guild, member: discord.Member
) -> discord.TextChannel | None:
    """
    Create a private channel for a new member.

    Args:
        guild: The Discord guild
        member: The new member

    Returns:
        The created channel, or None if creation failed
    """
    # Sanitize username for channel name (Discord allows alphanumeric and dashes)
    safe_name = "".join(c if c.isalnum() else "-" for c in member.name.lower())
    safe_name = safe_name.strip("-")[:20]  # Limit length
    channel_name = f"alerts-{safe_name}"

    # Set up permissions: only user + bot can see
    overwrites: dict[
        discord.Role | discord.Member | discord.Object, discord.PermissionOverwrite
    ] = {
        member: discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            read_message_history=True,
        ),
        guild.me: discord.PermissionOverwrite(
            read_messages=True,
            send_messages=True,
            manage_messages=True,
            manage_threads=True,
        ),
    }
    # Add default role to hide channel from everyone else
    if guild.default_role:
        overwrites[guild.default_role] = discord.PermissionOverwrite(read_messages=False)

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Community Scout auto-provisioning for {member.name}",
        )
        logger.info("Created channel %s for user %s", channel.name, member.name)
        return channel
    except discord.Forbidden:
        logger.error("Missing permissions to create channel for %s", member.name)
        return None
    except discord.HTTPException as e:
        logger.error("Failed to create channel for %s: %s", member.name, e)
        return None


async def create_source_thread(
    channel: discord.TextChannel, source_name: str
) -> discord.Thread | None:
    """
    Create a thread for a content source in the user's channel.

    Args:
        channel: The user's private channel
        source_name: Name of the content source (e.g., "Hacker News")

    Returns:
        The created thread, or None if creation failed
    """
    try:
        # Create an initial message to anchor the thread
        message = await channel.send(f"**{source_name} Alerts**")
        thread = await message.create_thread(
            name=source_name,
            auto_archive_duration=10080,  # 7 days
            reason=f"Source thread for {source_name}",
        )
        logger.info("Created thread %s in channel %s", thread.name, channel.name)
        return thread
    except discord.Forbidden:
        logger.error("Missing permissions to create thread in %s", channel.name)
        return None
    except discord.HTTPException as e:
        logger.error("Failed to create thread in %s: %s", channel.name, e)
        return None


async def setup_member(bot: discord.ext.commands.Bot, member: discord.Member) -> bool:
    """
    Set up a new member with channel, threads, and database records.

    Args:
        bot: The Discord bot instance
        member: The new member

    Returns:
        True if setup succeeded, False otherwise
    """
    guild = member.guild

    # Check if user already exists
    async with async_session_maker() as session:
        user_result = await session.execute(
            select(DiscordUser).where(DiscordUser.discord_id == str(member.id))
        )
        existing = user_result.scalar_one_or_none()

        if existing:
            logger.info("User %s already exists in database", member.name)
            return True

    # Create private channel
    channel = await create_user_channel(guild, member)
    if not channel:
        return False

    # Create database records
    async with async_session_maker() as session:
        # Create user record
        user = DiscordUser(
            discord_id=str(member.id),
            discord_username=member.name,
            channel_id=str(channel.id),
            is_active=True,
        )
        session.add(user)
        await session.flush()  # Get user.id

        # Get or create Hacker News source
        source_result = await session.execute(
            select(ContentSource).where(ContentSource.name == "hackernews")
        )
        hn_source = source_result.scalar_one_or_none()

        if not hn_source:
            hn_source = ContentSource(name="hackernews", is_active=True)
            session.add(hn_source)
            await session.flush()

        # Create source thread
        thread = await create_source_thread(channel, "Hacker News")
        if thread:
            source_thread = SourceThread(
                user_id=user.id,
                source_id=hn_source.id,
                thread_id=str(thread.id),
            )
            session.add(source_thread)

        await session.commit()
        logger.info("Created database records for user %s", member.name)

    # Send welcome message
    try:
        await channel.send(WELCOME_MESSAGE)
    except discord.HTTPException as e:
        logger.error("Failed to send welcome message: %s", e)

    return True


async def on_member_join_handler(member: discord.Member) -> None:
    """
    Handle new member joining the guild.

    Args:
        member: The member who joined
    """
    # Skip bots
    if member.bot:
        logger.debug("Skipping bot user %s", member.name)
        return

    # Check if this is our target guild
    if settings.discord_guild_id and str(member.guild.id) != settings.discord_guild_id:
        logger.debug(
            "Member joined different guild (%s), skipping", member.guild.name
        )
        return

    logger.info("New member joined: %s", member.name)

    # Import here to avoid circular import
    from community_scout.bot.bot import get_bot

    bot = get_bot()
    success = await setup_member(bot, member)

    if success:
        logger.info("Successfully set up new member: %s", member.name)
    else:
        logger.error("Failed to set up new member: %s", member.name)
