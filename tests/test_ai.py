"""Tests for AI module (OpenRouter client and summary generator)."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.ai.client import (
    ChatCompletion,
    ChatMessage,
    OpenRouterAuthError,
    OpenRouterClient,
    OpenRouterError,
)
from reddit_scout.ai.generator import SummaryGenerator, SummaryGeneratorError
from reddit_scout.models import Campaign, Match, User
from reddit_scout.models.match import MatchStatus, RedditType


class TestChatMessage:
    """Tests for ChatMessage dataclass."""

    def test_create_message(self) -> None:
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self) -> None:
        """Test creating a system message."""
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"


class TestOpenRouterClient:
    """Tests for OpenRouterClient."""

    def test_client_requires_api_key(self) -> None:
        """Test that client raises error without API key."""
        with patch("reddit_scout.ai.client.settings") as mock_settings:
            mock_settings.openrouter_api_key = ""
            mock_settings.openrouter_model = "test-model"
            mock_settings.openrouter_base_url = "https://api.example.com"

            with pytest.raises(OpenRouterAuthError, match="API key not configured"):
                OpenRouterClient()

    def test_client_with_explicit_key(self) -> None:
        """Test client accepts explicit API key."""
        client = OpenRouterClient(api_key="test-key", model="test-model")
        assert client.api_key == "test-key"
        assert client.model == "test-model"

    def test_headers(self) -> None:
        """Test that headers include required fields."""
        client = OpenRouterClient(api_key="test-key", model="test-model")
        headers = client._get_headers()

        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
        assert "HTTP-Referer" in headers
        assert "X-Title" in headers

    @pytest.mark.asyncio
    async def test_chat_success(self) -> None:
        """Test successful chat completion."""
        client = OpenRouterClient(api_key="test-key", model="test-model")

        mock_response = {
            "choices": [{"message": {"content": "Hello there!"}}],
            "model": "test-model",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
            )

            result = await client.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                temperature=0.7,
                max_tokens=100,
            )

            assert isinstance(result, ChatCompletion)
            assert result.content == "Hello there!"
            assert result.model == "test-model"
            assert result.total_tokens == 15

    @pytest.mark.asyncio
    async def test_chat_auth_error(self) -> None:
        """Test that auth errors are raised properly."""
        client = OpenRouterClient(api_key="invalid-key", model="test-model")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=401,
                text="Unauthorized",
            )

            with pytest.raises(OpenRouterAuthError, match="Invalid API key"):
                await client.chat(
                    messages=[ChatMessage(role="user", content="Hi")],
                )

    @pytest.mark.asyncio
    async def test_chat_api_error(self) -> None:
        """Test that API errors are raised properly."""
        client = OpenRouterClient(api_key="test-key", model="test-model")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                text="Internal Server Error",
            )

            with pytest.raises(OpenRouterError, match="500"):
                await client.chat(
                    messages=[ChatMessage(role="user", content="Hi")],
                )


class TestSummaryGenerator:
    """Tests for SummaryGenerator."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock OpenRouter client."""
        client = MagicMock(spec=OpenRouterClient)
        client.chat = AsyncMock(
            return_value=ChatCompletion(
                content="This is a helpful summary.",
                model="test-model",
                prompt_tokens=50,
                completion_tokens=20,
                total_tokens=70,
            )
        )
        return client

    @pytest.fixture
    async def test_match(
        self, db_session: AsyncSession, test_user: User, test_campaign: Campaign
    ) -> Match:
        """Create a test match."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        match = Match(
            campaign_id=test_campaign.id,
            reddit_id="t3_test123",
            reddit_type=RedditType.POST.value,
            subreddit="test",
            matched_keyword="help",
            title="Need help with something",
            body_snippet="I'm looking for help with this problem...",
            permalink="/r/test/comments/test123/",
            author="testuser",
            created_utc=datetime.now(UTC),
            status=MatchStatus.PENDING.value,
        )
        db_session.add(match)
        await db_session.commit()
        # Re-fetch with relationships loaded
        stmt = (
            select(Match)
            .where(Match.id == match.id)
            .options(selectinload(Match.draft_responses))
        )
        result = await db_session.execute(stmt)
        return result.scalar_one()

    @pytest.mark.asyncio
    async def test_generate_summary(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
        mock_client: MagicMock,
    ) -> None:
        """Test generating a summary for a match."""
        generator = SummaryGenerator(client=mock_client)

        result = await generator.generate_summary(
            session=db_session,
            match=test_match,
            campaign=test_campaign,
        )

        # Verify result
        assert result.content == "This is a helpful summary."
        assert result.tokens_used == 70
        assert result.summary_id is not None

        # Verify the client was called with correct messages
        mock_client.chat.assert_called_once()
        call_args = mock_client.chat.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0]
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == test_campaign.system_prompt
        assert messages[1].role == "user"
        assert "r/test" in messages[1].content

    @pytest.mark.asyncio
    async def test_regenerate_summary_with_feedback(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
        mock_client: MagicMock,
    ) -> None:
        """Test that regeneration includes feedback in the prompt."""
        from reddit_scout.models.match import DraftResponse

        # Add an existing summary to the match
        existing_summary = DraftResponse(
            match_id=test_match.id,
            content="First summary",
            version=1,
        )
        db_session.add(existing_summary)
        await db_session.flush()

        # Update the test_match's draft_responses in memory
        test_match.draft_responses.append(existing_summary)

        generator = SummaryGenerator(client=mock_client)

        # Generate second summary with feedback
        result = await generator.regenerate_summary(
            session=db_session,
            match=test_match,
            feedback="Make it more concise",
        )

        assert result.content == "This is a helpful summary."
        assert result.tokens_used == 70

        # Verify the client was called with feedback included
        mock_client.chat.assert_called()
        call_args = mock_client.chat.call_args
        messages = call_args.kwargs.get("messages") or call_args.args[0]

        # Should have: system, user, assistant (previous summary), user (feedback)
        assert len(messages) == 4
        assert messages[2].role == "assistant"
        assert messages[2].content == "First summary"
        assert messages[3].role == "user"
        assert "concise" in messages[3].content

    @pytest.mark.asyncio
    async def test_generate_summary_handles_error(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test that errors are handled properly."""
        mock_client = MagicMock(spec=OpenRouterClient)
        mock_client.chat = AsyncMock(side_effect=OpenRouterError("API error"))

        generator = SummaryGenerator(client=mock_client)

        with pytest.raises(SummaryGeneratorError, match="AI generation failed"):
            await generator.generate_summary(
                session=db_session,
                match=test_match,
                campaign=test_campaign,
            )

    def test_build_prompt_post(
        self,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test building prompt for a post."""
        generator = SummaryGenerator()
        messages = generator._build_prompt(test_match, test_campaign)

        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == test_campaign.system_prompt
        assert messages[1].role == "user"
        assert "r/test" in messages[1].content
        assert "post" in messages[1].content
        assert "help" in messages[1].content

    def test_build_prompt_comment(
        self,
        db_session: AsyncSession,
        test_campaign: Campaign,
        test_match: Match,
    ) -> None:
        """Test building prompt for a comment."""
        test_match.reddit_type = RedditType.COMMENT.value

        generator = SummaryGenerator()
        messages = generator._build_prompt(test_match, test_campaign)

        assert "comment" in messages[1].content
