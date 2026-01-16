# Sprint 04: Reddit Scanner Service

**Goal:** Build the core Reddit monitoring engine that scans configured subreddits for keyword matches and stores results for processing.

---

## Tasks

### Phase 1: PRAW Integration

- [x] Add PRAW to dependencies _(already in pyproject.toml)_
- [x] Create Reddit API credentials configuration (env vars) _(already in config.py)_
- [x] Build Reddit client wrapper with connection handling
- [x] Add rate limiting / backoff handling

### Phase 2: Scanner Service Architecture

- [x] Create scanner service module structure
- [x] Design scan job model (track last scan time per campaign)
- [x] Build campaign scanner that fetches posts from configured subreddits
- [x] Implement configurable scan windows based on frequency setting

### Phase 3: Content Matching

- [x] Fetch recent posts from subreddits (title + body)
- [x] Fetch recent comments from subreddits
- [x] Implement keyword matching logic (case-insensitive, phrase support)
- [x] Extract relevant context (snippet around match)

### Phase 4: Match Storage & Deduplication

- [x] Create Match model and migration _(Match model existed, added migration for last_scanned_at)_
- [x] Store matched posts/comments with metadata (reddit_id, author, subreddit, url, etc.)
- [x] Implement deduplication (skip already-matched reddit_ids)
- [x] Set initial status = 'pending'

### Phase 5: Runner & Scheduling

- [x] Create CLI command to run scanner
- [x] Filter campaigns by scan frequency vs last scan time
- [x] Add logging for scan progress and results
- [x] Handle errors gracefully (don't crash on single campaign failure)

---

## Acceptance Criteria

- [x] Scanner can authenticate with Reddit API
- [x] Scanner fetches posts and comments from configured subreddits
- [x] Keywords are matched against post titles, bodies, and comments
- [x] Matches are stored in database with reddit_id deduplication
- [x] Scanner respects configured scan frequency
- [x] Scanner can be run via CLI command
- [x] Existing tests still pass (63 tests passing)
- [x] New tests cover scanner functionality (26 new scanner tests)

---

## Technical Notes

### Reddit API Credentials

```
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
REDDIT_USER_AGENT=reddit-scout/1.0
```

### Match Model Fields

```python
class Match:
    id: int
    campaign_id: int  # FK
    reddit_id: str    # unique constraint
    reddit_type: str  # 'post' or 'comment'
    subreddit: str
    author: str
    title: str | None       # posts only
    body: str
    url: str
    matched_keyword: str
    context_snippet: str    # text around keyword match
    status: str             # pending, done, skipped
    created_at: datetime    # Reddit's timestamp
    discovered_at: datetime # when we found it
```

### Scan Frequency Mapping

```python
FREQUENCY_HOURS = {
    "2x_per_day": 12,
    "1x_per_day": 24,
    "2x_per_hour": 0.5,
    "1x_per_hour": 1,
}
```

---

## Out of Scope

- AI response generation (Sprint 5+)
- Discord notifications (Sprint 5+)
- Web UI for match viewing (Sprint 5+)
- Background job scheduler (cron external for now)

---

## Dependencies

- Reddit API credentials (user to provide)
- Existing campaign with subreddits and keywords configured

---

## Notes

### Implementation Decisions

1. **PRAW already included**: PRAW was already in pyproject.toml dependencies, so no changes needed.

2. **Match model already existed**: The Match model was defined in Sprint 01's initial schema migration.

3. **Added `last_scanned_at` to Campaign**: Created migration `4a1b2c3d4e5f_add_scanner_fields.py` to add:
   - `last_scanned_at` column to campaigns table
   - Unique index on `(campaign_id, reddit_id)` for efficient deduplication

4. **CLI entrypoint**: Added `reddit-scout-scanner` command to pyproject.toml scripts.

5. **Rate limiting**: Using `TooManyRequests` exception (newer PRAW/prawcore versions use this instead of `RateLimitExceeded`).

6. **Type annotations**: Added proper typing for mypy strict mode compliance.

### Files Created/Modified

**New files:**
- `src/reddit_scout/scanner/client.py` - Reddit API wrapper
- `src/reddit_scout/scanner/matcher.py` - Keyword matching logic
- `src/reddit_scout/scanner/service.py` - Scanner service
- `src/reddit_scout/scanner/cli.py` - CLI runner
- `alembic/versions/4a1b2c3d4e5f_add_scanner_fields.py` - Migration
- `tests/test_scanner.py` - 26 new tests

**Modified files:**
- `src/reddit_scout/scanner/__init__.py` - Exports
- `src/reddit_scout/models/campaign.py` - Added `last_scanned_at` field
- `pyproject.toml` - Added CLI script entrypoint
