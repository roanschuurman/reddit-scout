"""Reddit API client wrapper using PRAW."""

import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import praw  # type: ignore[import-untyped]
from prawcore.exceptions import (  # type: ignore[import-untyped]
    Forbidden,
    NotFound,
    PrawcoreException,
    ResponseException,
    TooManyRequests,
)

from reddit_scout.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    """Represents a Reddit post."""

    id: str
    subreddit: str
    title: str
    selftext: str
    author: str
    permalink: str
    created_utc: datetime
    score: int
    num_comments: int


@dataclass
class RedditComment:
    """Represents a Reddit comment."""

    id: str
    subreddit: str
    body: str
    author: str
    permalink: str
    created_utc: datetime
    score: int
    link_title: str  # Title of the parent post


class RedditClient:
    """Wrapper around PRAW with connection handling and rate limiting."""

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 5

    def __init__(self) -> None:
        """Initialize the Reddit client."""
        self._reddit: praw.Reddit | None = None

    def _get_client(self) -> praw.Reddit:
        """Get or create the PRAW Reddit instance."""
        if self._reddit is None:
            if not settings.reddit_client_id or not settings.reddit_client_secret:
                raise ValueError(
                    "Reddit API credentials not configured. "
                    "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables."
                )
            self._reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            logger.info("Reddit client initialized with user agent: %s", settings.reddit_user_agent)
        return self._reddit

    def _handle_rate_limit(self, exc: TooManyRequests) -> None:
        """Handle rate limit by waiting the specified time."""
        wait_time = exc.retry_after if hasattr(exc, "retry_after") and exc.retry_after else 60
        logger.warning("Rate limited by Reddit API. Waiting %d seconds...", wait_time)
        time.sleep(wait_time)

    def _with_retry(self, operation: str, func: Callable[[], Any]) -> Any:
        """Execute a function with retry logic for transient errors."""
        for attempt in range(self.MAX_RETRIES):
            try:
                return func()
            except TooManyRequests as e:
                self._handle_rate_limit(e)
            except (ResponseException, PrawcoreException) as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying...",
                        operation,
                        attempt + 1,
                        self.MAX_RETRIES,
                        str(e),
                    )
                    time.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                else:
                    logger.error(
                        "%s failed after %d attempts: %s", operation, self.MAX_RETRIES, str(e)
                    )
                    raise
        return None

    def get_subreddit_posts(
        self, subreddit_name: str, limit: int = 100, time_filter: str = "day"
    ) -> Iterator[RedditPost]:
        """
        Fetch recent posts from a subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/ prefix)
            limit: Maximum number of posts to fetch
            time_filter: Time filter for 'new' sort (hour, day, week, month, year, all)

        Yields:
            RedditPost objects
        """
        reddit = self._get_client()

        def fetch() -> list[Any]:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                # Use 'new' to get most recent posts
                return list(subreddit.new(limit=limit))
            except (NotFound, Forbidden) as e:
                logger.warning("Cannot access r/%s: %s", subreddit_name, str(e))
                return []

        posts: list[Any] = self._with_retry(f"fetch posts from r/{subreddit_name}", fetch) or []
        if not posts:
            return

        for post in posts:
            try:
                author_name = post.author.name if post.author else "[deleted]"
                yield RedditPost(
                    id=post.id,
                    subreddit=post.subreddit.display_name,
                    title=post.title,
                    selftext=post.selftext or "",
                    author=author_name,
                    permalink=post.permalink,
                    created_utc=datetime.fromtimestamp(post.created_utc, tz=UTC),
                    score=post.score,
                    num_comments=post.num_comments,
                )
            except Exception as e:
                logger.warning("Error processing post %s: %s", post.id, str(e))
                continue

    def get_subreddit_comments(
        self, subreddit_name: str, limit: int = 100
    ) -> Iterator[RedditComment]:
        """
        Fetch recent comments from a subreddit.

        Args:
            subreddit_name: Name of the subreddit (without r/ prefix)
            limit: Maximum number of comments to fetch

        Yields:
            RedditComment objects
        """
        reddit = self._get_client()

        def fetch() -> list[Any]:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                return list(subreddit.comments(limit=limit))
            except (NotFound, Forbidden) as e:
                logger.warning("Cannot access comments in r/%s: %s", subreddit_name, str(e))
                return []

        comments: list[Any] = (
            self._with_retry(f"fetch comments from r/{subreddit_name}", fetch) or []
        )
        if not comments:
            return

        for comment in comments:
            try:
                author_name = comment.author.name if comment.author else "[deleted]"
                # Get the parent post title
                link_title = ""
                if hasattr(comment, "link_title"):
                    link_title = comment.link_title
                elif hasattr(comment, "submission"):
                    link_title = comment.submission.title

                yield RedditComment(
                    id=comment.id,
                    subreddit=comment.subreddit.display_name,
                    body=comment.body or "",
                    author=author_name,
                    permalink=comment.permalink,
                    created_utc=datetime.fromtimestamp(comment.created_utc, tz=UTC),
                    score=comment.score,
                    link_title=link_title,
                )
            except Exception as e:
                logger.warning("Error processing comment %s: %s", comment.id, str(e))
                continue

    def verify_connection(self) -> bool:
        """Verify that the Reddit API connection is working."""
        try:
            reddit = self._get_client()
            # Try to access a simple endpoint to verify credentials
            reddit.user.me()  # Returns None for read-only app, but doesn't error
            logger.info("Reddit API connection verified")
            return True
        except Exception as e:
            logger.error("Reddit API connection failed: %s", str(e))
            return False
