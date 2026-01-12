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
- [ ] Initialize Alembic
- [ ] Create initial migration with all models
- [ ] Test migration up/down

### Phase 3: Authentication
- [ ] Configure SuperTokens (or simple session-based auth for MVP)
- [ ] Create login/register pages
- [ ] Protect routes requiring authentication
- [ ] Add current user to request context

---

## Acceptance Criteria

- [ ] `docker compose up` starts PostgreSQL and web app
- [ ] Database migrations run successfully
- [ ] User can register and log in
- [ ] Protected routes redirect to login
- [ ] Health check returns 200

---

## Notes

- Using HTMX + Jinja2 for frontend (no JS build step)
- DaisyUI provides component styling on top of Tailwind
- SuperTokens for auth to prepare for future multi-tenancy
