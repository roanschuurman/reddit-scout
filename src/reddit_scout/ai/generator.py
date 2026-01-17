"""AI response generator service."""

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reddit_scout.ai.client import ChatMessage, OpenRouterClient
from reddit_scout.models.campaign import Campaign
from reddit_scout.models.match import DraftResponse, Match, RedditType

logger = logging.getLogger(__name__)


# Prompt template for generating responses
RESPONSE_PROMPT_TEMPLATE = """Context:
- Subreddit: r/{subreddit}
- Type: {content_type}
- Title: {title}
- Content: {content}
- Matched keyword: "{keyword}"

Task: Write a helpful, natural response to this {content_type}.
Be conversational and add value to the discussion.
Do not be promotional or salesy.
Keep it concise (2-3 paragraphs max)."""


@dataclass
class GenerationResult:
    """Result of generating a response."""

    draft_id: int
    content: str
    tokens_used: int


class ResponseGeneratorError(Exception):
    """Error during response generation."""

    pass


class ResponseGenerator:
    """Service for generating AI draft responses."""

    def __init__(self, client: OpenRouterClient | None = None) -> None:
        """
        Initialize the response generator.

        Args:
            client: OpenRouter client instance (created if not provided)
        """
        self._client = client

    def _get_client(self) -> OpenRouterClient:
        """Get or create the OpenRouter client."""
        if self._client is None:
            self._client = OpenRouterClient()
        return self._client

    def _build_prompt(self, match: Match, campaign: Campaign) -> list[ChatMessage]:
        """
        Build the prompt for generating a response.

        Args:
            match: The match to generate a response for
            campaign: The campaign with system prompt

        Returns:
            List of chat messages for the API
        """
        # Determine content type label
        content_type = "post" if match.reddit_type == RedditType.POST.value else "comment"

        # Build user message from template
        user_message = RESPONSE_PROMPT_TEMPLATE.format(
            subreddit=match.subreddit,
            content_type=content_type,
            title=match.title or "(no title)",
            content=match.body_snippet or "(no content)",
            keyword=match.matched_keyword,
        )

        messages = [
            ChatMessage(role="system", content=campaign.system_prompt),
            ChatMessage(role="user", content=user_message),
        ]

        return messages

    async def generate_response(
        self,
        session: AsyncSession,
        match: Match,
        campaign: Campaign | None = None,
    ) -> GenerationResult:
        """
        Generate an AI draft response for a match.

        Args:
            session: Database session
            match: The match to generate a response for
            campaign: Optional campaign (fetched if not provided)

        Returns:
            GenerationResult with the generated draft

        Raises:
            ResponseGeneratorError: If generation fails
        """
        # Get campaign if not provided
        if campaign is None:
            result = await session.execute(
                select(Campaign).where(Campaign.id == match.campaign_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign is None:
                raise ResponseGeneratorError(f"Campaign {match.campaign_id} not found")

        # Build prompt
        messages = self._build_prompt(match, campaign)

        # Generate response
        try:
            client = self._get_client()
            completion = await client.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error("Failed to generate response for match %d: %s", match.id, str(e))
            raise ResponseGeneratorError(f"AI generation failed: {e}") from e

        # Get next version number
        version = 1
        if match.draft_responses:
            version = max(d.version for d in match.draft_responses) + 1

        # Create draft response
        draft = DraftResponse(
            match_id=match.id,
            content=completion.content,
            version=version,
        )
        session.add(draft)
        await session.flush()  # Get the ID

        logger.info(
            "Generated draft v%d for match %d (%d tokens)",
            version,
            match.id,
            completion.total_tokens,
        )

        return GenerationResult(
            draft_id=draft.id,
            content=completion.content,
            tokens_used=completion.total_tokens,
        )

    async def regenerate_response(
        self,
        session: AsyncSession,
        match: Match,
        feedback: str | None = None,
    ) -> GenerationResult:
        """
        Regenerate a response with optional feedback.

        Args:
            session: Database session
            match: The match to regenerate a response for
            feedback: Optional user feedback to incorporate

        Returns:
            GenerationResult with the new draft
        """
        # Get campaign
        result = await session.execute(
            select(Campaign).where(Campaign.id == match.campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign is None:
            raise ResponseGeneratorError(f"Campaign {match.campaign_id} not found")

        # Build base prompt
        messages = self._build_prompt(match, campaign)

        # If we have previous drafts and feedback, include them
        if match.draft_responses and feedback:
            # Get the latest draft
            latest_draft = max(match.draft_responses, key=lambda d: d.version)
            messages.append(
                ChatMessage(role="assistant", content=latest_draft.content)
            )
            messages.append(
                ChatMessage(
                    role="user",
                    content=f"Please revise the response based on this feedback: {feedback}",
                )
            )

        # Generate response
        try:
            client = self._get_client()
            completion = await client.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
        except Exception as e:
            logger.error("Failed to regenerate response for match %d: %s", match.id, str(e))
            raise ResponseGeneratorError(f"AI regeneration failed: {e}") from e

        # Get next version number
        version = 1
        if match.draft_responses:
            version = max(d.version for d in match.draft_responses) + 1

        # Create new draft response
        draft = DraftResponse(
            match_id=match.id,
            content=completion.content,
            version=version,
        )
        session.add(draft)
        await session.flush()

        logger.info(
            "Regenerated draft v%d for match %d (%d tokens)",
            version,
            match.id,
            completion.total_tokens,
        )

        return GenerationResult(
            draft_id=draft.id,
            content=completion.content,
            tokens_used=completion.total_tokens,
        )
