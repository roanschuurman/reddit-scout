# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reddit Scout is an AI-powered Reddit monitoring and engagement tool. It monitors subreddits for keyword matches, generates AI-drafted responses, and notifies users via Discord for manual posting.

## Development Commands

```bash
# Start services (PostgreSQL + web app)
docker compose up

# Install dependencies locally (using uv)
uv pip install -e ".[dev]"

# Run web app locally
uvicorn reddit_scout.api.main:app --reload

# Run tests
pytest

# Run linter
ruff check src tests

# Run type checker
mypy src

# Database migrations (after Alembic is set up)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Tech Stack

- **Backend**: Python with FastAPI
- **Frontend**: HTMX + Jinja2 templates with Tailwind CSS + DaisyUI
- **Database**: PostgreSQL
- **Auth**: SuperTokens
- **Reddit API**: PRAW (Python Reddit API Wrapper)
- **Discord**: discord.py
- **AI**: OpenRouter API
- **Deployment**: Docker, Hetzner VPS with Coolify

## Architecture

Three main services:
1. **FastAPI Web App** - Campaign management, subreddit discovery, match history
2. **Scanner Service** - Background cron job that monitors Reddit for keyword matches
3. **Discord Bot** - Sends notifications with AI drafts, handles refinement interactions

All services share a PostgreSQL database.

## Core Data Models

- **User** - Authentication via SuperTokens
- **Campaign** - Product-specific monitoring config (system prompt, scan frequency, Discord channel)
- **CampaignSubreddit** - Subreddits to monitor per campaign
- **CampaignKeyword** - Keywords to match per campaign
- **Match** - Discovered Reddit posts/comments (status: pending/done/skipped)
- **DraftResponse** - AI-generated response versions per match

## Key Design Decisions

- Human-in-the-loop: Automate discovery and drafting, keep posting manual (prevents bans)
- Discord-first workflow for notifications and response refinement
- Multi-tenant from start (users only see their own campaigns)

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
