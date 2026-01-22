"""Test configuration and fixtures."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from community_scout.api.main import app
from community_scout.database import get_db
from community_scout.models import Base, ContentSource, DiscordUser, UserKeyword

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine with static pool to share connection
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency for tests."""
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Set up and tear down database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for tests."""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_discord_user(db_session: AsyncSession) -> DiscordUser:
    """Create a test Discord user."""
    user = DiscordUser(
        discord_id="123456789012345678",
        discord_username="testuser",
        channel_id="987654321098765432",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_keyword(db_session: AsyncSession, test_discord_user: DiscordUser) -> UserKeyword:
    """Create a test keyword for a user."""
    keyword = UserKeyword(
        user_id=test_discord_user.id,
        phrase="python",
    )
    db_session.add(keyword)
    await db_session.commit()
    await db_session.refresh(keyword)
    return keyword


@pytest.fixture
async def test_content_source(db_session: AsyncSession) -> ContentSource:
    """Create a test content source."""
    source = ContentSource(name="hackernews")
    db_session.add(source)
    await db_session.commit()
    await db_session.refresh(source)
    return source
