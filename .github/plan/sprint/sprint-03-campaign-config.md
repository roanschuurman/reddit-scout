# Sprint 03: Campaign Configuration

**Goal:** Enable users to fully configure campaigns with subreddits, keywords, scan frequency, and Discord channel settings.

---

## Tasks

### Phase 1: Subreddit Management
- [x] Add subreddit to campaign (name input)
- [x] List subreddits on campaign detail page
- [x] Remove subreddit from campaign
- [x] Validate subreddit name format

### Phase 2: Keyword Management
- [x] Add keyword to campaign
- [x] List keywords on campaign detail page
- [x] Remove keyword from campaign
- [x] Support multi-word phrases

### Phase 3: Campaign Settings
- [x] Scan frequency dropdown (2x/day, 1x/day, 2x/hour, 1x/hour)
- [x] Discord channel ID input
- [x] Save settings on campaign edit form

### Phase 4: UI/UX Polish
- [x] Inline add/remove for subreddits (HTMX)
- [x] Inline add/remove for keywords (HTMX)
- [x] Visual feedback on add/remove actions

### Phase 5: Testing
- [x] Unit tests for subreddit CRUD
- [x] Unit tests for keyword CRUD
- [x] Integration tests for configuration endpoints
- [x] Multi-tenancy isolation tests

---

## Acceptance Criteria
- [x] Users can add/remove subreddits from a campaign
- [x] Users can add/remove keywords from a campaign
- [x] Users can set scan frequency from predefined options
- [x] Users can set Discord channel ID
- [x] All configurations persist correctly
- [x] Users cannot modify other users' campaigns
- [x] Tests pass for all new functionality

---

## Technical Notes

### Existing Models (from database)
- `CampaignSubreddit` - name, campaign_id
- `CampaignKeyword` - keyword, campaign_id
- `Campaign` - scan_frequency_minutes, discord_channel_id

### New Routes
```
POST   /campaigns/{id}/subreddits          Add subreddit
DELETE /campaigns/{id}/subreddits/{sub_id} Remove subreddit
POST   /campaigns/{id}/keywords            Add keyword
DELETE /campaigns/{id}/keywords/{kw_id}    Remove keyword
```

### Scan Frequency Options
| Display     | Minutes |
|-------------|---------|
| 2x/day      | 720     |
| 1x/day      | 1440    |
| 2x/hour     | 30      |
| 1x/hour     | 60      |

---

## Dependencies
- Campaign CRUD from Sprint 02
- CampaignSubreddit and CampaignKeyword models exist

---

## Progress Log

### 2026-01-14

**Implemented:**
- Created subreddit management routes (POST add, DELETE remove)
- Created keyword management routes (POST add, DELETE remove)
- Added HTMX partial templates for inline add/remove:
  - `templates/campaigns/partials/subreddit_list.html`
  - `templates/campaigns/partials/keyword_list.html`
- Updated campaign detail page to use HTMX partials
- Added scan frequency dropdown to edit form (4 options)
- Added Discord channel ID input to edit form
- Updated campaign settings display with human-readable scan frequency

**Key features:**
- Subreddit names automatically strip r/ prefix
- Names converted to lowercase for consistency
- Duplicate detection prevents adding same subreddit/keyword twice
- Inline validation with error messages
- Delete confirmation dialogs
- Multi-tenancy isolation (users can only modify their own campaigns)

**Automated test results:**
- 37 tests passing (17 new tests for Sprint 03)
- Ruff linting: All checks passed
- Mypy: Success, no issues found

**Files changed:**
- `src/reddit_scout/api/routes/campaigns.py` - Added subreddit/keyword routes, settings update
- `src/reddit_scout/templates/campaigns/partials/subreddit_list.html` - New HTMX partial
- `src/reddit_scout/templates/campaigns/partials/keyword_list.html` - New HTMX partial
- `src/reddit_scout/templates/campaigns/detail.html` - Use partials, fix scan frequency display
- `src/reddit_scout/templates/campaigns/edit.html` - Add scan frequency dropdown, Discord input
- `tests/test_campaigns.py` - Added 17 new tests
