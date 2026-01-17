"""Discord bot module."""

from reddit_scout.bot.bot import (
    RedditScoutBot,
    get_bot,
    start_bot,
    stop_bot,
    verify_bot_connection,
)
from reddit_scout.bot.notifications import (
    NotificationResult,
    build_match_embed,
    send_match_notification,
)
from reddit_scout.bot.views import MatchActionView, create_persistent_view

__all__ = [
    "RedditScoutBot",
    "get_bot",
    "start_bot",
    "stop_bot",
    "verify_bot_connection",
    "NotificationResult",
    "build_match_embed",
    "send_match_notification",
    "MatchActionView",
    "create_persistent_view",
]
