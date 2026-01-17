"""Tests for subreddit discovery functionality."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.models import Campaign, CampaignSubreddit, User
from reddit_scout.scanner.client import (
    RedditClient,
    SubredditInfo,
    SubredditPreviewPost,
)


class TestRedditClientSubredditMethods:
    """Tests for Reddit client subreddit discovery methods."""

    @pytest.fixture
    def mock_praw_subreddit(self) -> MagicMock:
        """Create a mock PRAW subreddit."""
        subreddit = MagicMock()
        subreddit.display_name = "python"
        subreddit.subscribers = 1000000
        subreddit.accounts_active = 5000
        subreddit.description = "A long description of the subreddit"
        subreddit.public_description = "Short description"
        subreddit.subreddit_type = "public"
        subreddit.quarantine = False
        return subreddit

    @pytest.fixture
    def mock_praw_post(self) -> MagicMock:
        """Create a mock PRAW post."""
        post = MagicMock()
        post.id = "abc123"
        post.title = "Test Post Title"
        post.score = 100
        post.num_comments = 50
        post.created_utc = datetime.now(UTC).timestamp()
        post.permalink = "/r/python/comments/abc123/test_post/"
        post.stickied = False
        return post

    def test_search_subreddits_returns_list(self) -> None:
        """search_subreddits returns a list of SubredditInfo."""
        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_subreddit.display_name = "python"
            mock_subreddit.subscribers = 1000000
            mock_subreddit.accounts_active = 5000
            mock_subreddit.description = "A description"
            mock_subreddit.public_description = "Short desc"
            mock_subreddit.subreddit_type = "public"
            mock_subreddit.quarantine = False

            mock_reddit.subreddits.search.return_value = [mock_subreddit]
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            results = client.search_subreddits("python", limit=10)

            assert len(results) == 1
            assert isinstance(results[0], SubredditInfo)
            assert results[0].name == "python"
            assert results[0].subscribers == 1000000

    def test_search_subreddits_handles_private(self) -> None:
        """search_subreddits marks private subreddits."""
        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_subreddit.display_name = "private_sub"
            mock_subreddit.subscribers = 1000
            mock_subreddit.subreddit_type = "private"
            mock_subreddit.quarantine = False
            mock_subreddit.description = ""
            mock_subreddit.public_description = ""

            mock_reddit.subreddits.search.return_value = [mock_subreddit]
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            results = client.search_subreddits("private", limit=10)

            assert len(results) == 1
            assert results[0].is_private is True

    def test_get_subreddit_info_returns_info(
        self, mock_praw_subreddit: MagicMock
    ) -> None:
        """get_subreddit_info returns SubredditInfo for valid subreddit."""
        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()
            mock_reddit.subreddit.return_value = mock_praw_subreddit
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            info = client.get_subreddit_info("python")

            assert info is not None
            assert isinstance(info, SubredditInfo)
            assert info.name == "python"
            assert info.subscribers == 1000000

    def test_get_subreddit_info_returns_none_for_not_found(self) -> None:
        """get_subreddit_info returns None for non-existent subreddit."""
        from prawcore.exceptions import NotFound

        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_subreddit.subscribers = NotFound(MagicMock())
            type(mock_subreddit).subscribers = property(
                lambda self: (_ for _ in ()).throw(NotFound(MagicMock()))
            )
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            info = client.get_subreddit_info("nonexistent")

            assert info is None

    def test_get_subreddit_preview_returns_posts(
        self, mock_praw_post: MagicMock
    ) -> None:
        """get_subreddit_preview returns list of preview posts."""
        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()
            mock_subreddit = MagicMock()
            mock_subreddit.hot.return_value = [mock_praw_post]
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            posts = client.get_subreddit_preview("python", limit=5)

            assert len(posts) == 1
            assert isinstance(posts[0], SubredditPreviewPost)
            assert posts[0].id == "abc123"
            assert posts[0].title == "Test Post Title"

    def test_get_subreddit_preview_skips_stickied(self) -> None:
        """get_subreddit_preview skips stickied posts."""
        with patch.object(RedditClient, "_get_client") as mock_get_client:
            mock_reddit = MagicMock()

            stickied_post = MagicMock()
            stickied_post.stickied = True
            stickied_post.id = "stickied1"

            normal_post = MagicMock()
            normal_post.stickied = False
            normal_post.id = "normal1"
            normal_post.title = "Normal Post"
            normal_post.score = 50
            normal_post.num_comments = 10
            normal_post.created_utc = datetime.now(UTC).timestamp()
            normal_post.permalink = "/r/test/comments/normal1/"

            mock_subreddit = MagicMock()
            mock_subreddit.hot.return_value = [stickied_post, normal_post]
            mock_reddit.subreddit.return_value = mock_subreddit
            mock_get_client.return_value = mock_reddit

            client = RedditClient()
            posts = client.get_subreddit_preview("test", limit=5)

            assert len(posts) == 1
            assert posts[0].id == "normal1"


class TestSubredditDiscoveryAPI:
    """Tests for subreddit discovery API endpoints."""

    @pytest.fixture
    async def campaign_with_subreddit(
        self, db_session: AsyncSession, test_user: User
    ) -> Campaign:
        """Create a campaign with an existing subreddit."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        campaign = Campaign(
            user_id=test_user.id,
            name="Test Campaign",
            system_prompt="Test prompt",
            is_active=True,
        )
        db_session.add(campaign)
        await db_session.commit()
        await db_session.refresh(campaign)

        subreddit = CampaignSubreddit(
            campaign_id=campaign.id,
            subreddit_name="existingsub",
        )
        db_session.add(subreddit)
        await db_session.commit()

        stmt = (
            select(Campaign)
            .where(Campaign.id == campaign.id)
            .options(selectinload(Campaign.subreddits))
        )
        result = await db_session.execute(stmt)
        return result.scalar_one()

    async def test_search_requires_auth(self, client: AsyncClient) -> None:
        """Search endpoint requires authentication."""
        response = await client.get(
            "/api/subreddits/search?q=python",
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 302  # Redirects to login

    async def test_search_returns_html(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Search endpoint returns HTML partial."""
        with patch(
            "reddit_scout.api.routes.subreddits._get_reddit_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.search_subreddits.return_value = [
                SubredditInfo(
                    name="python",
                    subscribers=1000000,
                    active_users=5000,
                    description="Python subreddit",
                    public_description="Python programming",
                    is_private=False,
                    is_quarantined=False,
                )
            ]
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/subreddits/search?q=python",
                cookies=auth_cookies,
            )

            assert response.status_code == 200
            assert "r/python" in response.text
            assert "1,000,000 subscribers" in response.text

    async def test_search_empty_query(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Empty search query returns placeholder message."""
        response = await client.get(
            "/api/subreddits/search?q=",
            cookies=auth_cookies,
        )

        assert response.status_code == 200
        assert "Search for subreddits" in response.text

    async def test_search_marks_existing_subreddits(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        campaign_with_subreddit: Campaign,
    ) -> None:
        """Search marks already-added subreddits."""
        with patch(
            "reddit_scout.api.routes.subreddits._get_reddit_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.search_subreddits.return_value = [
                SubredditInfo(
                    name="existingsub",
                    subscribers=1000,
                    active_users=100,
                    description="Existing sub",
                    public_description="Already added",
                    is_private=False,
                    is_quarantined=False,
                )
            ]
            mock_get_client.return_value = mock_client

            response = await client.get(
                f"/api/subreddits/search?q=existing&campaign_id={campaign_with_subreddit.id}",
                cookies=auth_cookies,
            )

            assert response.status_code == 200
            assert "Added" in response.text

    async def test_preview_requires_auth(self, client: AsyncClient) -> None:
        """Preview endpoint requires authentication."""
        response = await client.get(
            "/api/subreddits/python/preview",
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 302

    async def test_preview_returns_posts(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Preview endpoint returns HTML with posts."""
        with patch(
            "reddit_scout.api.routes.subreddits._get_reddit_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_subreddit_preview.return_value = [
                SubredditPreviewPost(
                    id="abc123",
                    title="Test Post Title",
                    score=100,
                    num_comments=50,
                    created_utc=datetime.now(UTC),
                    permalink="/r/python/comments/abc123/",
                )
            ]
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/subreddits/python/preview",
                cookies=auth_cookies,
            )

            assert response.status_code == 200
            assert "Test Post Title" in response.text
            assert "100 points" in response.text

    async def test_info_requires_auth(self, client: AsyncClient) -> None:
        """Info endpoint requires authentication."""
        # HTML requests redirect to login
        response = await client.get(
            "/api/subreddits/python/info",
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 302

    async def test_info_returns_json(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Info endpoint returns JSON."""
        with patch(
            "reddit_scout.api.routes.subreddits._get_reddit_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_subreddit_info.return_value = SubredditInfo(
                name="python",
                subscribers=1000000,
                active_users=5000,
                description="Python subreddit",
                public_description="Python programming",
                is_private=False,
                is_quarantined=False,
            )
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/subreddits/python/info",
                cookies=auth_cookies,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "python"
            assert data["subscribers"] == 1000000

    async def test_info_not_found(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Info endpoint returns 404 for non-existent subreddit."""
        with patch(
            "reddit_scout.api.routes.subreddits._get_reddit_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_subreddit_info.return_value = None
            mock_get_client.return_value = mock_client

            response = await client.get(
                "/api/subreddits/nonexistent/info",
                cookies=auth_cookies,
            )

            assert response.status_code == 404
