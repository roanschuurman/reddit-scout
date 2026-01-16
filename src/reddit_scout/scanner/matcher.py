"""Keyword matching logic for Reddit content."""

import re
from dataclasses import dataclass


@dataclass
class MatchResult:
    """Result of a keyword match."""

    keyword: str
    context_snippet: str


def extract_context(text: str, match_start: int, match_end: int, context_chars: int = 150) -> str:
    """
    Extract a context snippet around a match.

    Args:
        text: The full text
        match_start: Start index of the match
        match_end: End index of the match
        context_chars: Number of characters to include before and after

    Returns:
        A snippet with the match highlighted by context
    """
    # Calculate start and end positions for context
    start = max(0, match_start - context_chars)
    end = min(len(text), match_end + context_chars)

    # Adjust to word boundaries
    if start > 0:
        # Find the next space after start
        space_pos = text.find(" ", start)
        if space_pos != -1 and space_pos < match_start:
            start = space_pos + 1

    if end < len(text):
        # Find the last space before end
        space_pos = text.rfind(" ", match_end, end)
        if space_pos != -1:
            end = space_pos

    snippet = text[start:end].strip()

    # Add ellipsis if truncated
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."

    return snippet


def match_keywords(text: str, keywords: list[str]) -> MatchResult | None:
    """
    Check if any keywords match in the text.

    Matching is case-insensitive and supports multi-word phrases.
    Returns the first matching keyword and a context snippet.

    Args:
        text: The text to search in
        keywords: List of keyword phrases to match

    Returns:
        MatchResult if a match is found, None otherwise
    """
    if not text or not keywords:
        return None

    text_lower = text.lower()

    for keyword in keywords:
        keyword_lower = keyword.lower().strip()
        if not keyword_lower:
            continue

        # Use word boundary matching for single words,
        # simple contains for multi-word phrases
        if " " in keyword_lower:
            # Multi-word phrase: simple substring match
            pos = text_lower.find(keyword_lower)
            if pos != -1:
                context = extract_context(text, pos, pos + len(keyword_lower))
                return MatchResult(keyword=keyword, context_snippet=context)
        else:
            # Single word: use word boundary regex
            pattern = r"\b" + re.escape(keyword_lower) + r"\b"
            match = re.search(pattern, text_lower)
            if match:
                context = extract_context(text, match.start(), match.end())
                return MatchResult(keyword=keyword, context_snippet=context)

    return None


def match_post(title: str, body: str, keywords: list[str]) -> MatchResult | None:
    """
    Check if any keywords match in a post's title or body.

    Args:
        title: Post title
        body: Post body (selftext)
        keywords: List of keyword phrases

    Returns:
        MatchResult if a match is found, None otherwise
    """
    # Check title first (higher priority)
    result = match_keywords(title, keywords)
    if result:
        return result

    # Then check body
    return match_keywords(body, keywords)


def match_comment(body: str, keywords: list[str]) -> MatchResult | None:
    """
    Check if any keywords match in a comment.

    Args:
        body: Comment body
        keywords: List of keyword phrases

    Returns:
        MatchResult if a match is found, None otherwise
    """
    return match_keywords(body, keywords)
