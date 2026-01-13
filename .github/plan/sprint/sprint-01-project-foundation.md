# Sprint 01: Project Foundation

**Goal:** Set up the foundational project structure with working database, migrations, and basic auth.

---

## Tasks

### Phase 1: Project Structure
- [x] Initialize Python project with pyproject.toml
- [x] Create Docker Compose for PostgreSQL
- [x] Set up FastAPI application structure
- [x] Create SQLAlchemy models (User, Campaign, Match, DraftResponse)
- [x] Create base templates with HTMX + DaisyUI
- [x] Add basic health check endpoint

### Phase 2: Database Migrations
- [x] Initialize Alembic
- [x] Create initial migration with all models
- [x] Test migration up/down

### Phase 3: Authentication
- [x] Configure session-based auth for MVP (using bcrypt + signed cookies)
- [x] Create login/register pages
- [x] Protect routes requiring authentication
- [x] Add current user to request context

---

## Acceptance Criteria

- [x] `docker compose up` starts PostgreSQL and web app
- [x] Database migrations run successfully
- [x] User can register and log in
- [x] Protected routes redirect to login
- [x] Health check returns 200

---

## Notes

- Using HTMX + Jinja2 for frontend (no JS build step)
- DaisyUI provides component styling on top of Tailwind
- Implemented simple session-based auth with bcrypt for MVP (SuperTokens can be added later)
- Sessions use signed cookies via itsdangerous

## Decisions Made

- Used bcrypt directly instead of passlib due to compatibility issues with Python 3.14
- Implemented session-based auth instead of SuperTokens for MVP simplicity
- Added greenlet dependency for async Alembic migrations
