# Community Scout

A Discord-first Hacker News monitoring service. Get notified about topics you care about without constantly checking HN.

## What It Does

Community Scout monitors Hacker News for keywords you specify and delivers matching stories directly to your Discord channel:

1. **Join our Discord server** - Get your own private alerts channel
2. **Add keywords** - Use `/keyword add python` to monitor topics
3. **Get alerts** - Receive notifications when new content matches your keywords
4. **AI summaries** - Optionally add your OpenRouter API key for AI-generated summaries

Think of it as **Google Alerts for Hacker News** - track discussions about technologies, projects, or anything you want to follow.

## Features

- **Discord-First** - All interactions via slash commands
- **Personal Channels** - Each user gets their own private alerts channel
- **Keyword Monitoring** - Track multiple keywords across HN
- **AI Summaries** - Optional AI-generated summaries using your own API key
- **Organized Alerts** - Notifications organized by source (HN, more sources coming)
- **Privacy** - Your keywords and API keys are private to you

## Slash Commands

```
/keyword add <phrase>    - Add keyword to monitor
/keyword remove <phrase> - Remove keyword
/keyword list            - Show all your keywords
/apikey set              - Add your OpenRouter API key
/apikey status           - Check if key is configured
/status                  - Show your configuration
/pause                   - Pause notifications
/resume                  - Resume notifications
```

## Quick Start (Self-Hosting)

### Prerequisites

- Python 3.11+
- PostgreSQL
- Docker (optional)
- Discord bot token
- OpenRouter API key (optional, for AI summaries)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/community-scout.git
cd community-scout

# Start with Docker Compose
docker compose up

# Or install locally
pip install -e ".[dev]"
uvicorn community_scout.api.main:app --reload
```

### Configuration

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/community_scout
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_server_id
ENCRYPTION_KEY=your_fernet_key  # python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
OPENROUTER_API_KEY=your_api_key  # Default key for users without their own
HN_SCAN_INTERVAL_MINUTES=5
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Community Scout                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   FastAPI   │    │  HN Scanner │    │    Discord Bot      │  │
│  │   (Health)  │    │   Service   │    │  (Slash Commands)   │  │
│  │             │    │             │    │                     │  │
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
               │ Hacker  │         │ Discord │
               │ News    │         │   API   │
               │ API     │         │         │
               └─────────┘         └─────────┘
```

**Components:**

1. **Discord Bot** - Slash commands, user onboarding, alert notifications
2. **HN Scanner** - Polls Hacker News API for new stories and comments
3. **Web App** - Health checks and minimal API

## Tech Stack

- **Backend**: Python, FastAPI
- **Database**: PostgreSQL
- **Discord**: discord.py
- **AI**: OpenRouter API
- **Encryption**: cryptography (Fernet)

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
```

## Roadmap

- [x] **Sprint 08**: Rebrand & new data models
- [ ] **Sprint 09**: Discord bot onboarding & slash commands
- [ ] **Sprint 10**: Hacker News integration
- [ ] **Sprint 11**: Notification pipeline & AI summaries
- [ ] **Future**: Additional sources (Reddit, Twitter, etc.)

## License

MIT

## Acknowledgments

- [discord.py](https://discordpy.readthedocs.io/) - Discord API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Hacker News API](https://github.com/HackerNews/API) - Official HN API
