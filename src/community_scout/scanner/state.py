"""Scanner state management."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from community_scout.models import ScannerState


async def get_scanner_state(session: AsyncSession, source_name: str) -> ScannerState:
    """Get or create scanner state for a source.

    Args:
        session: Database session
        source_name: Name of the content source (e.g., "hackernews")

    Returns:
        ScannerState record for the source
    """
    stmt = select(ScannerState).where(ScannerState.source_name == source_name)
    result = await session.execute(stmt)
    state = result.scalar_one_or_none()

    if state is None:
        state = ScannerState(source_name=source_name, last_seen_id=0)
        session.add(state)
        await session.flush()

    return state


async def update_scanner_state(
    session: AsyncSession,
    source_name: str,
    last_seen_id: int,
) -> None:
    """Update scanner state after processing items.

    Args:
        session: Database session
        source_name: Name of the content source
        last_seen_id: Last processed item ID
    """
    state = await get_scanner_state(session, source_name)
    state.last_seen_id = last_seen_id
    state.last_scan_at = datetime.now(UTC)
    await session.flush()
