# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Community Scout is a Discord-first Hacker News monitoring service. Users join a Discord server, get auto-provisioned personal channels, and configure their own keywords via slash commands. Notifications arrive in threads organized by source (Hacker News for now, extensible to other platforms).

## Development Commands

```bash
# Start services (PostgreSQL + web app)
docker compose up

# Install dependencies locally (using uv)
uv pip install -e ".[dev]"

# Run web app locally
uvicorn community_scout.api.main:app --reload

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

## Tech Stack

- **Backend**: Python with FastAPI
- **Database**: PostgreSQL
- **Discord**: discord.py (slash commands, auto-provisioning)
- **AI**: OpenRouter API (per-user API keys supported)
- **Encryption**: cryptography (Fernet for API key storage)
- **Deployment**: Docker, Hetzner VPS with Coolify

## Architecture

Two main services:
1. **FastAPI Web App** - Health checks, minimal API
2. **Discord Bot** - User onboarding, keyword management, alert notifications

Scanner service (coming in Sprint 10):
- **HN Scanner** - Polls Hacker News for new stories/comments, matches keywords

All services share a PostgreSQL database.

## Core Data Models

- **DiscordUser** - Discord user with channel_id, optional OpenRouter API key
- **UserKeyword** - Keywords to monitor per user
- **ContentSource** - Content sources (e.g., "hackernews")
- **SourceThread** - User's Discord thread per source
- **HNItem** - Hacker News stories and comments
- **UserAlert** - Alerts for matched content (status: pending/sent/dismissed)

## Key Design Decisions

- Discord-first: All interactions via slash commands
- Per-user configuration: Each user has their own keywords and API key
- Personal channels: Auto-provisioned on member join
- Source threads: Organized alerts by content source
- Encryption: User API keys stored encrypted

## Environment Variables

```
DATABASE_URL                 # PostgreSQL connection string
DISCORD_BOT_TOKEN            # Discord bot token
DISCORD_GUILD_ID             # Server where bot operates
ENCRYPTION_KEY               # Fernet key for API key encryption
OPENROUTER_API_KEY           # Default API key (for users without their own)
HN_SCAN_INTERVAL_MINUTES     # Scan frequency (default: 5)
```

## Workflow

This project uses the agile workflow defined in `scrum.md`. Key points:

- **Claude = Scrum Master**, **User = Product Owner**
- One sprint = one Claude Code conversation
- Sprint lifecycle: START → EXECUTE → AUTOTEST → HANDOFF → CLOSE → UPDATE

### Folder Structure

```
.github/plan/
├── backlog.md                    # Product backlog with status tracking
├── sprint/                       # Active sprint document (only 1 at a time)
│   └── sprint-XX-description.md
└── sprint_backup/                # Completed sprint summaries
    └── sprint-XX-YYYY-MM-DD.md
```

### Sprint Process

1. **Start**: Create sprint doc in `.github/plan/sprint/` with goal, tasks, acceptance criteria
2. **Execute**: Check off tasks, track decisions and blockers
3. **Autotest**: Run all automated tests before handoff
4. **Handoff**: Provide summary + manual test steps to Product Owner
5. **Close**: After approval, create summary in `sprint_backup/`, delete sprint doc
6. **Update**: Mark backlog items as DONE with reference to summary

### Git Commits

```
type(scope): brief description

Co-Authored-By: Claude <model>@anthropic.com
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`
