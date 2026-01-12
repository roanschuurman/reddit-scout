# 📘 Product Solution Design Document

## Reddit Scout — AI-Powered Reddit Monitoring & Engagement Tool

**Version:** 1.0  
**Date:** January 11, 2026  
**Status:** Ready for Development

---

## 1. Problem Statement

### The Pain Point

Solo founders and small teams know Reddit is a goldmine for organic customer acquisition — relevant discussions happen daily where their product could genuinely help. But capitalizing on this requires:

- **Hours of manual browsing** across multiple subreddits
- **Crafting personalized, authentic responses** that don't feel spammy
- **Timing** — catching posts early when engagement matters most
- **Tracking** — remembering what you've already responded to

The result: most founders either skip Reddit entirely or do it inconsistently, missing high-intent opportunities.

### Why Now?

- Reddit's influence in purchase decisions has grown (Google now surfaces Reddit in search results)
- AI can now generate contextual, human-sounding responses
- API access (for reading) remains available at reasonable rate limits
- Manual posting keeps accounts safe from automation detection

---

## 2. Target Users & Market

### Primary User

**Solo founders and indie hackers** promoting their own products who:
- Have 1-3 products to promote
- Value authentic engagement over spray-and-pray marketing
- Are technical enough to self-host or use a simple dashboard
- Want to save 5-10+ hours/week on Reddit prospecting

### Secondary Users (Future)

- Small marketing teams at startups
- Agencies managing multiple client brands
- Developer advocates and community managers

### Buyer vs. User

For v1, same person — the founder both buys and uses the tool.

---

## 3. Proposed Solution

### Core Concept

A self-hosted tool that:
1. **Monitors** specified subreddits for keyword matches (posts + comments)
2. **Generates** AI-drafted responses using a personalized voice/style
3. **Notifies** via Discord with draft + direct link
4. **Enables** refinement through conversational AI in Discord threads
5. **Tracks** engagement history in a web dashboard

### Key Insight

Human-in-the-loop design: Automate discovery and drafting (the tedious parts), keep posting manual (the risky part).

---

## 4. Core Value Proposition

> **"Never miss a Reddit opportunity again. Find relevant conversations automatically, get AI-drafted responses in your voice, and engage authentically — in minutes instead of hours."**

### Why This Wins

| Alternative | Problem | Reddit Scout Advantage |
|-------------|---------|------------------------|
| Manual browsing | Time-consuming, inconsistent | Automated scanning, consistent coverage |
| Generic alerts (F5Bot) | No response drafting | AI generates contextual replies |
| Full automation bots | High ban risk, spammy | Manual posting, authentic voice |
| Hiring a VA | Expensive, training overhead | AI learns your voice instantly |

---

## 5. MVP Feature List (v1)

### Campaign Management (Web App)

- [ ] Create/edit/delete campaigns (one per product)
- [ ] Configure multiple subreddits per campaign
- [ ] Configure multiple keyword phrases per campaign
- [ ] Set custom AI system prompt per campaign (voice/style)
- [ ] Set scan frequency (2x/day to 1x/hour)
- [ ] Assign Discord channel per campaign

### Subreddit Discovery (Web App)

- [ ] Search subreddits by keyword
- [ ] Display subscriber count + active users
- [ ] Preview recent posts before adding
- [ ] Show related subreddit suggestions

### Reddit Monitoring (Background Service)

- [ ] Scan configured subreddits at set frequency
- [ ] Match posts AND comments against keywords
- [ ] Deduplicate matches (don't re-alert on seen items)
- [ ] Queue matches for AI processing

### AI Response Generation

- [ ] Generate contextual response using campaign's system prompt
- [ ] Adapt tone based on context (reply to post vs. reply to comment)
- [ ] Use OpenRouter for model flexibility

### Discord Integration

- [ ] Send notifications to campaign-specific channels
- [ ] Include: subreddit, post age, matched keyword, post snippet, AI draft, direct link
- [ ] Buttons: [✅ Done] [🔄 Regenerate] [✏️ Refine]
- [ ] Thread-based refinement via free-form conversation
- [ ] [📋 Copy Final] button for easy posting

### Completion Tracking (Web App)

- [ ] Mark items as "done" from Discord
- [ ] View history of all matches (pending, completed, skipped)
- [ ] Filter by campaign, date, status

### Auth & Multi-tenancy

- [ ] User registration/login via SuperTokens
- [ ] Users can only see their own campaigns
- [ ] Foundation for future multi-user commercial version

---

## 6. Post-MVP Backlog (v2+)

### Web-Based Response Editing
- Full rich-text editor in dashboard
- AI chat interface for refinement (beyond Discord)
- Response templates library

### Analytics & Insights
- Engagement tracking (did you actually post?)
- Click tracking via UTM parameters
- Subreddit performance comparison
- Best posting times analysis

### Advanced Matching
- Semantic search (not just keyword matching)
- Sentiment filtering (skip negative/rant posts)
- Competitor mention alerts

### Team Features
- Multiple users per account
- Role-based permissions
- Response approval workflows

### Integrations
- Slack as alternative to Discord
- Browser extension for one-click posting
- Mobile app for on-the-go review

### Scale Features
- Multiple Reddit accounts management
- API for programmatic campaign creation
- White-label option

---

## 7. Competitive & Market Analysis

### Direct Competitors

| Tool | What It Does | Gap |
|------|--------------|-----|
| F5Bot | Free Reddit keyword alerts | No AI drafting, email-only |
| Brand24 | Social listening (Reddit included) | Expensive, no response generation |
| Mention | Multi-platform monitoring | Not Reddit-focused, no AI drafting |
| Syften | Reddit monitoring | Limited AI features, expensive |

### Indirect Alternatives

- Manual Reddit browsing
- Hiring a VA
- Ignoring Reddit entirely

### Differentiation

1. **AI response generation** with personal voice training
2. **Discord-first workflow** for speed and familiarity
3. **Self-hosted option** for privacy and control
4. **Human-in-the-loop** design that keeps accounts safe

### Risks

- **Platform risk**: Reddit could restrict API further
- **Commoditization**: Easy for others to build similar tools
- **Mitigation**: Focus on workflow excellence and voice personalization

---

## 8. Pricing & Monetization Strategy

### Phase 1: Personal Use (Now)
- Free for self-hosted personal use
- Validate workflow, refine features

### Phase 2: Commercial Launch (Future)

| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | 1 campaign, 2 scans/day, 50 matches/month |
| Pro | $29/mo | 5 campaigns, hourly scans, unlimited matches |
| Team | $79/mo | 15 campaigns, multiple users, priority support |

### Revenue Milestones
1. First paying user within 2 months of launch
2. $1K MRR within 6 months
3. $5K MRR within 12 months

---

## 9. Recommended Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend** | Python (FastAPI) | Best Reddit/Discord libraries, rapid development |
| **Frontend** | HTMX + Jinja2 | Python-native, no JS build step, fast iteration |
| **Styling** | Tailwind + DaisyUI | Clean components, modern look with minimal effort |
| **Database** | PostgreSQL | Robust, scalable, handles relational data well |
| **Auth** | SuperTokens | Open-source, self-hostable, handles OAuth |
| **Reddit API** | PRAW | Mature, well-documented Python wrapper |
| **Discord** | discord.py | Solid library for bot interactions |
| **AI** | OpenRouter | Single API, multiple models, easy switching |
| **Hosting** | Hetzner VPS + Coolify | Cost-effective, Docker-native, full control |
| **Containers** | Docker | Consistent deployment, easy scaling |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hetzner VPS + Coolify                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   FastAPI   │    │  Scanner    │    │    Discord Bot      │  │
│  │   Web App   │    │  Service    │    │                     │  │
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
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐          ┌───────────┐         ┌─────────┐
   │ Reddit  │          │ OpenRouter│         │ Discord │
   │   API   │          │    API    │         │   API   │
   └─────────┘          └───────────┘         └─────────┘
```

### Data Model (Core Entities)

```
User
├── id (PK)
├── email
├── created_at
└── supertokens_id

Campaign
├── id (PK)
├── user_id (FK)
├── name
├── system_prompt
├── scan_frequency_minutes
├── discord_channel_id
├── is_active
└── created_at

CampaignSubreddit
├── id (PK)
├── campaign_id (FK)
├── subreddit_name
└── added_at

CampaignKeyword
├── id (PK)
├── campaign_id (FK)
├── phrase
└── added_at

Match
├── id (PK)
├── campaign_id (FK)
├── reddit_id (post or comment ID)
├── reddit_type (post | comment)
├── subreddit
├── matched_keyword
├── title
├── body_snippet
├── permalink
├── author
├── created_utc
├── discovered_at
├── status (pending | done | skipped)
├── completed_at
└── discord_message_id

DraftResponse
├── id (PK)
├── match_id (FK)
├── content
├── version
├── created_at
└── is_final
```

---

## 10. Risks, Assumptions & Open Questions

### Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Reddit restricts API further | High | Medium | Monitor announcements, build scraping fallback |
| AI responses feel spammy | High | Low | Personal system prompts, human review |
| Low engagement ROI | Medium | Medium | Track conversions, iterate on targeting |
| SuperTokens complexity | Low | Low | Good docs, fallback to simple JWT |
| Discord rate limits | Low | Low | Queue notifications, respect limits |

### Assumptions (To Validate)

1. Founders will actually post AI-drafted responses (not just read them)
2. Discord is the right notification channel for this audience
3. 2x/day to 1x/hour scanning frequency is sufficient
4. Personal system prompts produce noticeably better responses
5. Users will pay $29+/mo once validated

### Open Questions

1. Should we track whether users actually posted? (Browser extension?)
2. What's the right default system prompt template?
3. Should matches expire after X days if not acted on?
4. How to handle Reddit's 10-minute rate limit on new accounts?

---

## 11. Go-To-Market & Revenue Plan

### Phase 1: Dogfooding (Weeks 1-4)
- Build MVP
- Use for SimplSign promotion
- Document friction points and wins

### Phase 2: Private Beta (Weeks 5-8)
- Invite 5-10 founder friends
- Gather feedback on workflow
- Iterate on AI response quality

### Phase 3: Public Launch (Weeks 9-12)

**Channels:**
- Indie Hackers (community post + discussion)
- r/SideProject, r/startups, r/EntrepreneurRideAlong
- Twitter/X (build in public thread)
- Product Hunt launch

**Launch Offer:**
- First 50 users: Free Pro tier for 3 months
- Collect testimonials and case studies

### Phase 4: Growth (Month 4+)
- Content marketing: "How I got X customers from Reddit"
- SEO: Target "Reddit marketing tool", "Reddit monitoring"
- Affiliate program for power users

---

## 12. Next Execution Steps

### Immediate (This Week)
1. Set up project repository
2. Initialize FastAPI project structure
3. Configure PostgreSQL + Docker Compose
4. Implement SuperTokens auth

### Week 2
5. Build campaign CRUD (web UI)
6. Implement subreddit discovery features
7. Create basic keyword management

### Week 3
8. Build Reddit scanner service
9. Implement match detection logic
10. Set up OpenRouter integration

### Week 4
11. Build Discord bot
12. Implement notification flow
13. Add refinement thread interaction
14. Connect "Mark Done" to database

### Week 5
15. Build match history view
16. Polish UI (loading states, error handling)
17. Write deployment scripts

### Week 6
18. Deploy to Hetzner/Coolify
19. Begin dogfooding with SimplSign
20. Document bugs and improvements

---

## Appendix A: Discord Notification Template

```
🔔 New Match: {campaign_name}

📍 r/{subreddit} • {time_ago}
🔑 Matched: "{keyword}"

📝 "{post_title_or_comment_snippet}"

💬 Draft Response:
"{ai_generated_response}"

🔗 View on Reddit: {permalink}

[✅ Done] [🔄 Regenerate] [✏️ Refine]
```

---

## Appendix B: Example System Prompt

```
You are writing Reddit responses on behalf of a solo founder.

Voice guidelines:
- Friendly and helpful, never salesy
- Share from personal experience ("I had the same issue...")
- Keep responses concise (2-4 sentences ideal)
- Only mention the product if genuinely relevant
- Never use marketing speak or superlatives
- Match the tone of the subreddit (casual vs professional)

Product context:
SimplSign is a simple e-signature tool for freelancers and small businesses. 
Key benefits: No account required for signers, simple interface, affordable.

If the post isn't a good fit for mentioning SimplSign, just provide helpful advice without any product mention.
```

---

## Appendix C: Scoring Summary

### Idea Viability Score

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Problem Severity | 4/5 | Real pain, but not critical — nice-to-have for most |
| Market Size | 3/5 | Niche (founders doing Reddit marketing) but growing |
| Willingness to Pay | 3/5 | Will pay if ROI proven, skeptical otherwise |
| Differentiation | 4/5 | AI drafting + workflow is unique combo |
| Timing | 4/5 | Reddit's SEO rise + AI capabilities align well |
| **Total** | **18/25** | |

### Execution Feasibility Score

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Technical Complexity | 4/5 | Standard stack, clear architecture |
| MVP Speed | 4/5 | 6 weeks achievable with focus |
| Dependencies | 3/5 | Reddit API is a dependency risk |
| Team Fit | 5/5 | Matches your skills perfectly |
| Maintenance Risk | 4/5 | Simple stack, few moving parts |
| **Total** | **20/25** | |

### Risk Assessment

| Risk Type | Level | Notes |
|-----------|-------|-------|
| Market Risk | Medium | Niche audience, need to validate willingness to pay |
| Product Risk | Low | Clear problem, straightforward solution |
| Technical Risk | Low | Proven technologies, no novel engineering |
| Distribution Risk | Medium | Need to reach founders, crowded content channels |
| Regulatory Risk | Low | ToS compliant with manual posting approach |

**Biggest Risk:** Reddit API policy changes could break core functionality.

---

*Document generated: January 11, 2026*
*Ready for development*
