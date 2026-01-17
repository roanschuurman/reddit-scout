# Product Backlog

## Current Sprint

_None_

## Completed

- Sprint 05: AI Response Generation & Discord Notifications - DONE (see sprint_backup/sprint-05-2026-01-17.md)
- Sprint 04: Reddit Scanner Service - DONE (see sprint_backup/sprint-04-2026-01-17.md)
- Sprint 03: Campaign Configuration - DONE (see sprint_backup/sprint-03-2026-01-14.md)
- Sprint 02: Campaign CRUD - DONE (see sprint_backup/sprint-02-2026-01-14.md)
- Sprint 01: Project Foundation - DONE (see sprint_backup/sprint-01-2026-01-14.md)

## Upcoming

### Foundation & Infrastructure
- [x] Alembic migrations setup _(Sprint 01)_
- [x] User registration/login flow _(Sprint 01)_
- [ ] SuperTokens auth integration _(deferred - using session auth for MVP)_

### Campaign Management (Web App)
- [x] Campaign CRUD operations _(Sprint 02)_
- [x] Configure subreddits per campaign _(Sprint 03)_
- [x] Configure keywords per campaign _(Sprint 03)_
- [x] Custom AI system prompt per campaign _(Sprint 02 - part of campaign create/edit)_
- [x] Set scan frequency (2x/day to 1x/hour) _(Sprint 03)_
- [x] Assign Discord channel per campaign _(Sprint 03)_

### Subreddit Discovery (Web App)
- [ ] Search subreddits by keyword
- [ ] Display subscriber count + active users
- [ ] Preview recent posts before adding
- [ ] Show related subreddit suggestions

### Reddit Monitoring (Scanner Service)
- [x] PRAW integration for Reddit API _(Sprint 04)_
- [x] Scan subreddits at configured frequency _(Sprint 04)_
- [x] Match posts AND comments against keywords _(Sprint 04)_
- [x] Deduplicate matches _(Sprint 04)_
- [x] Queue matches for AI processing _(Sprint 05)_

### AI Response Generation
- [x] OpenRouter integration _(Sprint 05)_
- [x] Generate contextual responses using campaign system prompt _(Sprint 05)_
- [x] Adapt tone based on context (post vs comment reply) _(Sprint 05)_

### Discord Integration
- [x] Discord bot setup _(Sprint 05)_
- [x] Send notifications to campaign-specific channels _(Sprint 05)_
- [x] Include: subreddit, post age, keyword, snippet, AI draft, link _(Sprint 05)_
- [x] Buttons: Done, Skip _(Sprint 05)_
- [ ] Regenerate button (request new AI draft)
- [ ] Refine button with thread-based conversation
- [ ] Copy Final button

### Match Tracking (Web App)
- [ ] Mark items as done from Discord
- [ ] View match history (pending, completed, skipped)
- [ ] Filter by campaign, date, status

## Ideas / Someday

- Web-based response editor with AI chat
- Analytics & insights (engagement tracking, UTM clicks)
- Semantic search (beyond keyword matching)
- Sentiment filtering
- Team features (multiple users, roles)
- Slack integration
- Browser extension for one-click posting
- Mobile app
