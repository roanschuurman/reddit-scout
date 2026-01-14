"""Test configuration and fixtures."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from reddit_scout.api.deps import SESSION_COOKIE_NAME, create_session_token
from reddit_scout.api.main import app
from reddit_scout.auth import hash_password
from reddit_scout.database import get_db
from reddit_scout.models import Base, Campaign, User

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
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_cookies(test_user: User) -> dict[str, str]:
    """Get authentication cookies for test user."""
    token = create_session_token(test_user.id)
    return {SESSION_COOKIE_NAME: token}


@pytest.fixture
async def test_campaign(db_session: AsyncSession, test_user: User) -> Campaign:
    """Create a test campaign."""
    campaign = Campaign(
        user_id=test_user.id,
        name="Test Campaign",
        system_prompt="You are a helpful assistant.",
        is_active=True,
    )
    db_session.add(campaign)
    await db_session.commit()
    await db_session.refresh(campaign)
    return campaign
