# Sprint 02: Campaign CRUD

**Goal:** Implement core campaign management functionality - create, read, update, and delete campaigns.

---

## Tasks

### Phase 1: Backend Routes
- [x] Create campaign router (`/campaigns`)
- [x] GET `/campaigns` - List user's campaigns
- [x] GET `/campaigns/new` - New campaign form
- [x] POST `/campaigns` - Create campaign
- [x] GET `/campaigns/{id}` - View campaign details
- [x] GET `/campaigns/{id}/edit` - Edit campaign form
- [x] POST `/campaigns/{id}` - Update campaign (using POST instead of PUT for HTML forms)
- [x] POST `/campaigns/{id}/delete` - Delete campaign (using POST instead of DELETE for HTML forms)

### Phase 2: Templates
- [x] Campaign list page (cards layout)
- [x] New campaign form (name, system prompt, active toggle)
- [x] Campaign detail page
- [x] Edit campaign form
- [x] Delete confirmation modal (DaisyUI dialog)

### Phase 3: Navigation & UX
- [x] Campaigns link in main navigation (already existed)
- [x] Empty state for no campaigns
- [x] Success/error flash messages via query params
- [x] Form validation with error display

### Phase 4: Testing
- [x] Unit tests for campaign CRUD operations
- [x] Integration tests for campaign routes
- [x] Multi-tenancy isolation tests

---

## Acceptance Criteria
- [x] Authenticated users can create new campaigns
- [x] Users can view a list of their own campaigns only (multi-tenant)
- [x] Users can edit campaign name, system prompt, and active status
- [x] Users can delete campaigns with confirmation
- [x] All forms show validation errors appropriately
- [x] Navigation includes link to campaigns section
- [x] Tests pass for all CRUD operations (20 tests passing)

---

## Technical Notes

### Campaign Fields (from existing model)
- `name` - Campaign name (required)
- `system_prompt` - AI system prompt for response generation (required)
- `scan_frequency_minutes` - How often to scan (will configure in future sprint)
- `discord_channel_id` - Discord channel for notifications (will configure in future sprint)
- `is_active` - Enable/disable campaign

### Routes Structure
```
/campaigns           GET    List campaigns
/campaigns/new       GET    New campaign form
/campaigns           POST   Create campaign
/campaigns/{id}      GET    View campaign
/campaigns/{id}/edit GET    Edit form
/campaigns/{id}      POST   Update campaign
/campaigns/{id}/delete POST Delete campaign
```

---

## Dependencies
- Session-based auth from Sprint 01
- Campaign model already exists in database

---

## Progress Log

### 2026-01-14

**Implemented:**
- Created `src/reddit_scout/api/routes/campaigns.py` with all CRUD endpoints
- Created templates in `src/reddit_scout/templates/campaigns/`:
  - `list.html` - Card-based campaign list with empty state
  - `new.html` - Create campaign form
  - `detail.html` - Campaign detail view with subreddits, keywords, settings
  - `edit.html` - Edit campaign form
- Registered campaigns router in `api/routes/__init__.py` and `api/main.py`
- Added `aiosqlite` to dev dependencies for async SQLite testing
- Created test fixtures in `tests/conftest.py`
- Created comprehensive tests in `tests/test_campaigns.py` (19 tests)

**Key decisions:**
- Used POST for update/delete instead of PUT/DELETE (HTML forms don't support PUT/DELETE)
- Used query params (`?created=1`, `?updated=1`, `?deleted=1`) for flash messages
- Used `selectinload` to eagerly load subreddits/keywords relationships
- Made form fields have default empty strings to allow custom validation

**Automated test results:**
- 20 tests passing (19 campaign tests + 1 health check)
- Ruff linting: All checks passed
- Mypy: Success, no issues found
