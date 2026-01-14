"""Tests for campaign CRUD operations."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.models import Campaign, CampaignKeyword, CampaignSubreddit, User

HTML_HEADERS = {"Accept": "text/html"}


class TestCampaignListPage:
    """Tests for campaign list page."""

    async def test_list_campaigns_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.get(
            "/campaigns", headers=HTML_HEADERS, follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_list_campaigns_empty(
        self, client: AsyncClient, auth_cookies: dict[str, str]
    ) -> None:
        """Authenticated user sees empty state."""
        response = await client.get("/campaigns", cookies=auth_cookies)
        assert response.status_code == 200
        assert "No campaigns yet" in response.text

    async def test_list_campaigns_with_campaign(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Authenticated user sees their campaigns."""
        response = await client.get("/campaigns", cookies=auth_cookies)
        assert response.status_code == 200
        assert test_campaign.name in response.text


class TestNewCampaignPage:
    """Tests for new campaign form."""

    async def test_new_campaign_form_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.get(
            "/campaigns/new", headers=HTML_HEADERS, follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_new_campaign_form_renders(
        self, client: AsyncClient, auth_cookies: dict[str, str]
    ) -> None:
        """Authenticated user can see new campaign form."""
        response = await client.get("/campaigns/new", cookies=auth_cookies)
        assert response.status_code == 200
        assert "Create New Campaign" in response.text
        assert "Campaign Name" in response.text
        assert "System Prompt" in response.text


class TestCreateCampaign:
    """Tests for campaign creation."""

    async def test_create_campaign_requires_auth(self, client: AsyncClient) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.post(
            "/campaigns",
            headers=HTML_HEADERS,
            data={"name": "Test", "system_prompt": "Test prompt"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_create_campaign_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        db_session: AsyncSession,
        test_user: User,
    ) -> None:
        """Successfully create a campaign."""
        response = await client.post(
            "/campaigns",
            data={
                "name": "My New Campaign",
                "system_prompt": "You are a helpful assistant.",
                "is_active": "true",
            },
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/campaigns/" in response.headers["location"]
        assert "created=1" in response.headers["location"]

        # Verify campaign was created
        result = await db_session.execute(
            select(Campaign).where(Campaign.user_id == test_user.id)
        )
        campaign = result.scalar_one()
        assert campaign.name == "My New Campaign"
        assert campaign.system_prompt == "You are a helpful assistant."
        assert campaign.is_active is True

    async def test_create_campaign_validation_errors(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Show validation errors for invalid input."""
        response = await client.post(
            "/campaigns",
            data={
                "name": "",
                "system_prompt": "",
            },
            cookies=auth_cookies,
        )
        assert response.status_code == 400
        assert "Campaign name is required" in response.text
        assert "System prompt is required" in response.text


class TestViewCampaign:
    """Tests for campaign detail page."""

    async def test_view_campaign_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.get(
            f"/campaigns/{test_campaign.id}",
            headers=HTML_HEADERS,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_view_campaign_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Authenticated user can view their campaign."""
        response = await client.get(
            f"/campaigns/{test_campaign.id}", cookies=auth_cookies
        )
        assert response.status_code == 200
        assert test_campaign.name in response.text
        assert test_campaign.system_prompt in response.text

    async def test_view_nonexistent_campaign_redirects(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
    ) -> None:
        """Viewing nonexistent campaign redirects to list."""
        response = await client.get(
            "/campaigns/99999", cookies=auth_cookies, follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/campaigns"


class TestEditCampaign:
    """Tests for campaign edit form."""

    async def test_edit_campaign_form_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.get(
            f"/campaigns/{test_campaign.id}/edit",
            headers=HTML_HEADERS,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_edit_campaign_form_renders(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Authenticated user can see edit form with current values."""
        response = await client.get(
            f"/campaigns/{test_campaign.id}/edit", cookies=auth_cookies
        )
        assert response.status_code == 200
        assert "Edit Campaign" in response.text
        assert test_campaign.name in response.text


class TestUpdateCampaign:
    """Tests for campaign update."""

    async def test_update_campaign_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            headers=HTML_HEADERS,
            data={"name": "Updated", "system_prompt": "Updated prompt"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_update_campaign_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully update a campaign."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            data={
                "name": "Updated Campaign",
                "system_prompt": "Updated system prompt.",
                "is_active": "true",
            },
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert f"/campaigns/{test_campaign.id}?updated=1" in response.headers["location"]

        # Verify campaign was updated
        await db_session.refresh(test_campaign)
        assert test_campaign.name == "Updated Campaign"
        assert test_campaign.system_prompt == "Updated system prompt."


class TestDeleteCampaign:
    """Tests for campaign deletion."""

    async def test_delete_campaign_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/delete",
            headers=HTML_HEADERS,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_delete_campaign_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully delete a campaign."""
        campaign_id = test_campaign.id
        response = await client.post(
            f"/campaigns/{campaign_id}/delete",
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "/campaigns?deleted=1" in response.headers["location"]

        # Verify campaign was deleted
        result = await db_session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        assert result.scalar_one_or_none() is None


class TestMultiTenancy:
    """Tests for multi-tenant isolation."""

    async def test_user_cannot_view_other_users_campaign(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_campaign: Campaign,
    ) -> None:
        """Users cannot view campaigns belonging to other users."""
        from reddit_scout.api.deps import create_session_token
        from reddit_scout.auth import hash_password

        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        # Try to view first user's campaign as second user
        other_token = create_session_token(other_user.id)
        response = await client.get(
            f"/campaigns/{test_campaign.id}",
            cookies={"session": other_token},
            follow_redirects=False,
        )
        # Should redirect to campaigns list (campaign not found for this user)
        assert response.status_code == 302
        assert response.headers["location"] == "/campaigns"

    async def test_user_only_sees_own_campaigns(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_campaign: Campaign,
        auth_cookies: dict[str, str],
    ) -> None:
        """Users only see their own campaigns in the list."""
        from reddit_scout.auth import hash_password

        # Create another user with a campaign
        other_user = User(
            email="other@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add(other_user)
        await db_session.commit()

        other_campaign = Campaign(
            user_id=other_user.id,
            name="Other User Campaign",
            system_prompt="Other prompt",
        )
        db_session.add(other_campaign)
        await db_session.commit()

        # View campaigns as first user
        response = await client.get("/campaigns", cookies=auth_cookies)
        assert response.status_code == 200
        assert test_campaign.name in response.text
        assert "Other User Campaign" not in response.text


class TestSubredditManagement:
    """Tests for subreddit CRUD operations."""

    async def test_add_subreddit_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            headers=HTML_HEADERS,
            data={"subreddit_name": "python"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_add_subreddit_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully add a subreddit to a campaign."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            data={"subreddit_name": "python"},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "r/python" in response.text

        # Verify in database
        result = await db_session.execute(
            select(CampaignSubreddit).where(
                CampaignSubreddit.campaign_id == test_campaign.id
            )
        )
        subreddit = result.scalar_one()
        assert subreddit.subreddit_name == "python"

    async def test_add_subreddit_strips_r_prefix(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """r/ prefix is stripped from subreddit name."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            data={"subreddit_name": "r/learnpython"},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "r/learnpython" in response.text

        # Verify stored without prefix
        result = await db_session.execute(
            select(CampaignSubreddit).where(
                CampaignSubreddit.campaign_id == test_campaign.id
            )
        )
        subreddit = result.scalar_one()
        assert subreddit.subreddit_name == "learnpython"

    async def test_add_subreddit_empty_name(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Empty subreddit name shows error."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            data={"subreddit_name": ""},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "Subreddit name is required" in response.text

    async def test_add_subreddit_duplicate(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Duplicate subreddit shows error."""
        # Add first
        subreddit = CampaignSubreddit(
            campaign_id=test_campaign.id, subreddit_name="python"
        )
        db_session.add(subreddit)
        await db_session.commit()

        # Try to add again
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            data={"subreddit_name": "python"},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "Subreddit already added" in response.text

    async def test_remove_subreddit_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully remove a subreddit."""
        # Add subreddit first
        subreddit = CampaignSubreddit(
            campaign_id=test_campaign.id, subreddit_name="learnprogramming"
        )
        db_session.add(subreddit)
        await db_session.commit()
        await db_session.refresh(subreddit)

        response = await client.delete(
            f"/campaigns/{test_campaign.id}/subreddits/{subreddit.id}",
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        # Check the badge is gone (don't check for word since placeholder contains "python")
        assert "r/learnprogramming" not in response.text

        # Verify deleted
        result = await db_session.execute(
            select(CampaignSubreddit).where(CampaignSubreddit.id == subreddit.id)
        )
        assert result.scalar_one_or_none() is None


class TestKeywordManagement:
    """Tests for keyword CRUD operations."""

    async def test_add_keyword_requires_auth(
        self, client: AsyncClient, test_campaign: Campaign
    ) -> None:
        """Unauthenticated users are redirected to login."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/keywords",
            headers=HTML_HEADERS,
            data={"phrase": "best tool"},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/login"

    async def test_add_keyword_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully add a keyword to a campaign."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/keywords",
            data={"phrase": "best tool for"},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "best tool for" in response.text

        # Verify in database
        result = await db_session.execute(
            select(CampaignKeyword).where(
                CampaignKeyword.campaign_id == test_campaign.id
            )
        )
        keyword = result.scalar_one()
        assert keyword.phrase == "best tool for"

    async def test_add_keyword_empty_phrase(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Empty keyword shows error."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}/keywords",
            data={"phrase": ""},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "Keyword is required" in response.text

    async def test_add_keyword_duplicate(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Duplicate keyword shows error."""
        # Add first
        keyword = CampaignKeyword(campaign_id=test_campaign.id, phrase="best tool")
        db_session.add(keyword)
        await db_session.commit()

        # Try to add again
        response = await client.post(
            f"/campaigns/{test_campaign.id}/keywords",
            data={"phrase": "best tool"},
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "Keyword already added" in response.text

    async def test_remove_keyword_success(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully remove a keyword."""
        # Add keyword first (use unique phrase not in placeholder)
        keyword = CampaignKeyword(campaign_id=test_campaign.id, phrase="unique test phrase")
        db_session.add(keyword)
        await db_session.commit()
        await db_session.refresh(keyword)

        response = await client.delete(
            f"/campaigns/{test_campaign.id}/keywords/{keyword.id}",
            cookies=auth_cookies,
        )
        assert response.status_code == 200
        assert "unique test phrase" not in response.text

        # Verify deleted
        result = await db_session.execute(
            select(CampaignKeyword).where(CampaignKeyword.id == keyword.id)
        )
        assert result.scalar_one_or_none() is None


class TestCampaignSettings:
    """Tests for campaign settings (scan frequency, Discord channel)."""

    async def test_update_scan_frequency(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully update scan frequency."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            data={
                "name": test_campaign.name,
                "system_prompt": test_campaign.system_prompt,
                "scan_frequency_minutes": "30",
                "discord_channel_id": "",
            },
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify in database
        await db_session.refresh(test_campaign)
        assert test_campaign.scan_frequency_minutes == 30

    async def test_update_discord_channel(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Successfully update Discord channel ID."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            data={
                "name": test_campaign.name,
                "system_prompt": test_campaign.system_prompt,
                "scan_frequency_minutes": "60",
                "discord_channel_id": "1234567890123456789",
            },
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify in database
        await db_session.refresh(test_campaign)
        assert test_campaign.discord_channel_id == "1234567890123456789"

    async def test_update_discord_channel_empty_clears(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
        db_session: AsyncSession,
    ) -> None:
        """Empty Discord channel clears the value."""
        # Set a value first
        test_campaign.discord_channel_id = "1234567890123456789"
        await db_session.commit()

        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            data={
                "name": test_campaign.name,
                "system_prompt": test_campaign.system_prompt,
                "scan_frequency_minutes": "60",
                "discord_channel_id": "",
            },
            cookies=auth_cookies,
            follow_redirects=False,
        )
        assert response.status_code == 302

        # Verify cleared in database
        await db_session.refresh(test_campaign)
        assert test_campaign.discord_channel_id is None

    async def test_invalid_scan_frequency_rejected(
        self,
        client: AsyncClient,
        auth_cookies: dict[str, str],
        test_campaign: Campaign,
    ) -> None:
        """Invalid scan frequency shows error."""
        response = await client.post(
            f"/campaigns/{test_campaign.id}",
            data={
                "name": test_campaign.name,
                "system_prompt": test_campaign.system_prompt,
                "scan_frequency_minutes": "999",
                "discord_channel_id": "",
            },
            cookies=auth_cookies,
        )
        assert response.status_code == 400
        assert "Invalid scan frequency" in response.text


class TestSubredditKeywordMultiTenancy:
    """Tests for multi-tenant isolation of subreddits and keywords."""

    async def test_cannot_add_subreddit_to_other_users_campaign(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_campaign: Campaign,
    ) -> None:
        """Users cannot add subreddits to other users' campaigns."""
        from reddit_scout.api.deps import create_session_token
        from reddit_scout.auth import hash_password

        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        # Try to add subreddit to first user's campaign as second user
        other_token = create_session_token(other_user.id)
        response = await client.post(
            f"/campaigns/{test_campaign.id}/subreddits",
            data={"subreddit_name": "python"},
            cookies={"session": other_token},
        )
        assert response.status_code == 404

    async def test_cannot_add_keyword_to_other_users_campaign(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_campaign: Campaign,
    ) -> None:
        """Users cannot add keywords to other users' campaigns."""
        from reddit_scout.api.deps import create_session_token
        from reddit_scout.auth import hash_password

        # Create another user
        other_user = User(
            email="other@example.com",
            password_hash=hash_password("password123"),
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        # Try to add keyword to first user's campaign as second user
        other_token = create_session_token(other_user.id)
        response = await client.post(
            f"/campaigns/{test_campaign.id}/keywords",
            data={"phrase": "best tool"},
            cookies={"session": other_token},
        )
        assert response.status_code == 404
