"""OpenRouter API client wrapper."""

import logging
from dataclasses import dataclass

import httpx

from community_scout.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """Represents a chat message."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class ChatCompletion:
    """Represents a chat completion response."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenRouterError(Exception):
    """Base exception for OpenRouter errors."""

    pass


class OpenRouterAuthError(OpenRouterError):
    """Authentication error."""

    pass


class OpenRouterRateLimitError(OpenRouterError):
    """Rate limit error."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class OpenRouterClient:
    """Client for OpenRouter API."""

    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2
    DEFAULT_TIMEOUT = 60.0

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        """
        Initialize the OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to settings)
            model: Model to use (defaults to settings)
            base_url: API base URL (defaults to settings)
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.base_url = base_url or settings.openrouter_base_url

        if not self.api_key:
            raise OpenRouterAuthError(
                "OpenRouter API key not configured. "
                "Set OPENROUTER_API_KEY environment variable."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://community-scout.app",  # Required by OpenRouter
            "X-Title": "Community Scout",  # For OpenRouter dashboard
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> ChatCompletion:
        """
        Send a chat completion request to OpenRouter.

        Args:
            messages: List of chat messages
            model: Model to use (overrides default)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            ChatCompletion with the response

        Raises:
            OpenRouterError: If the request fails
        """
        model = model or self.model
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error: Exception | None = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        json=payload,
                    )

                    if response.status_code == 401:
                        raise OpenRouterAuthError("Invalid API key")

                    if response.status_code == 429:
                        retry_after = response.headers.get("Retry-After")
                        retry_seconds = int(retry_after) if retry_after else None
                        raise OpenRouterRateLimitError(
                            "Rate limited by OpenRouter", retry_after=retry_seconds
                        )

                    if response.status_code >= 400:
                        error_detail = response.text
                        raise OpenRouterError(
                            f"OpenRouter API error ({response.status_code}): {error_detail}"
                        )

                    data = response.json()

                    # Extract response content
                    choices = data.get("choices", [])
                    if not choices:
                        raise OpenRouterError("No choices in response")

                    content = choices[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})

                    return ChatCompletion(
                        content=content,
                        model=data.get("model", model),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    )

            except OpenRouterAuthError:
                # Don't retry auth errors
                raise
            except OpenRouterRateLimitError as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = e.retry_after or (self.RETRY_DELAY_SECONDS * (attempt + 1))
                    logger.warning(
                        "Rate limited (attempt %d/%d). Waiting %d seconds...",
                        attempt + 1,
                        self.MAX_RETRIES,
                        wait_time,
                    )
                    import asyncio

                    await asyncio.sleep(wait_time)
                    last_error = e
                else:
                    raise
            except httpx.TimeoutException as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "Request timeout (attempt %d/%d): %s. Retrying...",
                        attempt + 1,
                        self.MAX_RETRIES,
                        str(e),
                    )
                    import asyncio

                    await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    last_error = e
                else:
                    raise OpenRouterError(f"Request timeout after {self.MAX_RETRIES} attempts")
            except httpx.RequestError as e:
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "Request error (attempt %d/%d): %s. Retrying...",
                        attempt + 1,
                        self.MAX_RETRIES,
                        str(e),
                    )
                    import asyncio

                    await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
                    last_error = e
                else:
                    raise OpenRouterError(f"Request failed after {self.MAX_RETRIES} attempts: {e}")

        # Should not reach here, but just in case
        raise OpenRouterError(f"Unexpected error: {last_error}")

    async def verify_connection(self) -> bool:
        """
        Verify that the OpenRouter API connection is working.

        Returns:
            True if connection works, False otherwise
        """
        try:
            # Send a minimal request to check auth
            await self.chat(
                messages=[ChatMessage(role="user", content="Hi")],
                max_tokens=1,
            )
            logger.info("OpenRouter API connection verified")
            return True
        except OpenRouterAuthError as e:
            logger.error("OpenRouter authentication failed: %s", str(e))
            return False
        except OpenRouterError as e:
            logger.error("OpenRouter connection failed: %s", str(e))
            return False
