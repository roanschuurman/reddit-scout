# Reddit Scout

A Reddit content monitoring and notification service. Stay informed about topics you care about without constantly checking Reddit.

## What It Does

Reddit Scout monitors subreddits and keywords you specify, then delivers matching posts to your preferred channel:

- **Discord** - Get notifications directly in your Discord server
- **JSON API** - Fetch matches programmatically for custom integrations
- **Webhooks** - Push notifications to any service (coming soon)

Think of it as **Google Alerts for Reddit** - track discussions about topics, brands, technologies, or anything else you want to follow.

## Features

- **Multi-Subreddit Monitoring** - Watch multiple subreddits from a single dashboard
- **Keyword Filtering** - Only get notified about posts matching your keywords
- **Configurable Frequency** - Set how often to check for new content (hourly to twice daily)
- **Discord Integration** - Rich embeds with post details and direct links
- **Multi-tenant** - Each user manages their own monitoring campaigns
- **Self-Hosted** - Full control over your data and infrastructure

## Use Cases

- Track mentions of your open source project
- Follow discussions about technologies you're learning
- Monitor communities for research or market analysis
- Get alerts when topics you care about are discussed
- Keep up with niche subreddits without constant browsing

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Docker (optional, for containerized deployment)
- Reddit API credentials
- Discord bot token (for Discord notifications)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/reddit-scout.git
cd reddit-scout

# Start with Docker Compose
docker compose up

# Or install locally
pip install -e ".[dev]"
uvicorn reddit_scout.api.main:app --reload
```

### Configuration

Create a `.env` file with your credentials:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/reddit_scout
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=reddit-scout/0.1
DISCORD_BOT_TOKEN=your_bot_token
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Reddit Scout                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   FastAPI   │    │  Scanner    │    │    Discord Bot      │  │
│  │   Web App   │    │  Service    │    │   (Notifications)   │  │
│  │             │    │  (Cron)     │    │                     │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────┘  │
│         │                  │                      │             │
│         └──────────────────┼──────────────────────┘             │
│                            │                                    │
│                   ┌────────▼────────┐                           │
│                   │   PostgreSQL    │                           │
│                   └─────────────────┘                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
               ┌─────────┐         ┌─────────┐
               │ Reddit  │         │ Discord │
               │   API   │         │   API   │
               └─────────┘         └─────────┘
```

**Components:**

1. **Web App** - Campaign management UI, subreddit discovery, match history
2. **Scanner Service** - Background job that polls Reddit for new matching content
3. **Discord Bot** - Sends notifications to configured channels

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: HTMX, Jinja2, Tailwind CSS
- **Database**: PostgreSQL
- **Reddit**: PRAW (Python Reddit API Wrapper)
- **Notifications**: discord.py

## Development

```bash
# Run tests
pytest

# Run linter
ruff check src tests

# Run type checker
mypy src

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## API Usage

Reddit Scout exposes a JSON API for programmatic access to your matches:

```bash
# Get recent matches for a campaign
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/campaigns/1/matches

# Response
{
  "matches": [
    {
      "id": 123,
      "subreddit": "programming",
      "title": "Discussion about Python async",
      "author": "some_user",
      "permalink": "/r/programming/comments/...",
      "matched_keyword": "async python",
      "created_utc": "2026-01-20T10:30:00Z"
    }
  ]
}
```

## License

MIT

## Acknowledgments

- [PRAW](https://praw.readthedocs.io/) - Python Reddit API Wrapper
- [discord.py](https://discordpy.readthedocs.io/) - Discord API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
