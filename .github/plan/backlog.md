# Product Backlog

## Current Sprint

- Sprint 09: Discord Bot - Onboarding & Commands - IN PROGRESS

## Completed

### Community Scout (Post-Pivot)
- Sprint 08: Pivot Foundation - DONE
  - Renamed package to community_scout
  - New data models (DiscordUser, UserKeyword, HNItem, UserAlert, etc.)
  - Removed Reddit/PRAW dependencies
  - API key encryption utility

### Reddit Scout (Pre-Pivot, Archived)
- Sprint 07: Discord Enhancements - SUPERSEDED (see sprint_backup/sprint-07-2026-01-22.md)
- Sprint 06: Subreddit Discovery - DONE (see sprint_backup/sprint-06-2026-01-17.md)
- Sprint 05: AI Response Generation & Discord Notifications - DONE (see sprint_backup/sprint-05-2026-01-17.md)
- Sprint 04: Reddit Scanner Service - DONE (see sprint_backup/sprint-04-2026-01-17.md)
- Sprint 03: Campaign Configuration - DONE (see sprint_backup/sprint-03-2026-01-14.md)
- Sprint 02: Campaign CRUD - DONE (see sprint_backup/sprint-02-2026-01-14.md)
- Sprint 01: Project Foundation - DONE (see sprint_backup/sprint-01-2026-01-14.md)

## Upcoming Sprints

### Sprint 09: Discord Bot - Onboarding & Commands
- [ ] Implement on_member_join → create personal channel
- [ ] Create source thread (Hacker News) in channel
- [ ] Welcome message with instructions
- [ ] Slash commands: /keyword add/remove/list
- [ ] Slash commands: /apikey set (modal), /status
- [ ] /pause and /resume commands

### Sprint 10: Hacker News Integration
- [ ] Create HN API client (stories + comments)
- [ ] Scanner service for HN (polls every 5 mins)
- [ ] Keyword matching against HN content
- [ ] UserAlert creation for matches
- [ ] Track last_seen_id for incremental scanning

### Sprint 11: Notification Pipeline
- [ ] Per-user AI summary generation (using their API key)
- [ ] Post alerts to user's source thread
- [ ] Fallback message for users without API key
- [ ] Regenerate button for new AI summary
- [ ] Refine button with thread conversation _(from Sprint 07)_
- [ ] Copy button for easy copying _(from Sprint 07)_
- [ ] Dismiss button functionality

## Ideas / Someday

- Additional content sources (Reddit, Twitter/X, Lobste.rs)
- Web dashboard for viewing alert history
- Semantic search (beyond keyword matching)
- Sentiment/relevance filtering
- Team features (shared keywords)
- Scheduled digest mode (daily/weekly summary)
- Browser extension for quick actions
