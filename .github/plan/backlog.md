# Product Backlog

## Current Sprint

- Sprint 01: Project Foundation - IN PROGRESS

## Completed

_(none yet)_

## Upcoming

### Foundation & Infrastructure
- [ ] Alembic migrations setup
- [ ] SuperTokens auth integration
- [ ] User registration/login flow

### Campaign Management (Web App)
- [ ] Campaign CRUD operations
- [ ] Configure subreddits per campaign
- [ ] Configure keywords per campaign
- [ ] Custom AI system prompt per campaign
- [ ] Set scan frequency (2x/day to 1x/hour)
- [ ] Assign Discord channel per campaign

### Subreddit Discovery (Web App)
- [ ] Search subreddits by keyword
- [ ] Display subscriber count + active users
- [ ] Preview recent posts before adding
- [ ] Show related subreddit suggestions

### Reddit Monitoring (Scanner Service)
- [ ] PRAW integration for Reddit API
- [ ] Scan subreddits at configured frequency
- [ ] Match posts AND comments against keywords
- [ ] Deduplicate matches
- [ ] Queue matches for AI processing

### AI Response Generation
- [ ] OpenRouter integration
- [ ] Generate contextual responses using campaign system prompt
- [ ] Adapt tone based on context (post vs comment reply)

### Discord Integration
- [ ] Discord bot setup
- [ ] Send notifications to campaign-specific channels
- [ ] Include: subreddit, post age, keyword, snippet, AI draft, link
- [ ] Buttons: Done, Regenerate, Refine
- [ ] Thread-based refinement conversation
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
