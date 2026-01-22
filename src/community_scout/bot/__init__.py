"""Discord bot module."""

from community_scout.bot.bot import (
    CommunityScoutBot,
    get_bot,
    start_bot,
    stop_bot,
    verify_bot_connection,
)
from community_scout.bot.commands import APIKeyGroup, KeywordGroup, setup_commands
from community_scout.bot.modals import APIKeyModal
from community_scout.bot.onboarding import on_member_join_handler, setup_member

__all__ = [
    "CommunityScoutBot",
    "get_bot",
    "start_bot",
    "stop_bot",
    "verify_bot_connection",
    "KeywordGroup",
    "APIKeyGroup",
    "setup_commands",
    "APIKeyModal",
    "on_member_join_handler",
    "setup_member",
]
