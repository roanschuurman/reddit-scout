"""Discord bot module."""

from community_scout.bot.bot import (
    CommunityScoutBot,
    get_bot,
    start_bot,
    stop_bot,
    verify_bot_connection,
)

__all__ = [
    "CommunityScoutBot",
    "get_bot",
    "start_bot",
    "stop_bot",
    "verify_bot_connection",
]
