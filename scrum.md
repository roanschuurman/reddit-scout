# Agile Way of Working with Claude Code

This document describes a lightweight agile methodology for working with Claude Code on small-to-medium projects.

---

## Overview

- **Sprint = Context Session** - One sprint equals one Claude Code conversation
- **Daily Sprints** - Short, focused iterations
- **Subagents** - Parallelize work where possible
- **Document Size** - Max ~500 lines per document

---

## Folder Structure

```
.github/plan/
├── backlog.md                    # Product backlog with status tracking
├── [solution_design].md          # Architecture & design reference (optional)
├── sprint/                       # Active sprint document (only 1 at a time)
│   └── sprint-XX-description.md  # Detailed tasks, deleted after closure
└── sprint_backup/                # Completed sprint summaries
    └── sprint-XX-YYYY-MM-DD.md   # Archived summary after completion
```

---

## Roles

### Claude = Scrum Master
- Responsible for delivering product according to scope
- Runs ALL automated tests before handoff
- Provides clear manual test instructions to Product Owner
- Creates sprint summaries and updates backlog
- Ensures quality and completeness before asking for approval

### User = Product Owner
- Reviews and approves completed work
- Performs manual acceptance testing
- Makes scope and priority decisions
- Provides feedback on delivered features

---

## Sprint Lifecycle

```
1. START    → Create detailed sprint document in .github/plan/sprint/
2. EXECUTE  → Implement, tracking progress in sprint document
3. AUTOTEST → Run full automated test suite
4. HANDOFF  → Ask user to verify/test manually
5. CLOSE    → After approval: create summary in sprint_backup/, delete sprint doc
6. UPDATE   → Update backlog.md with status and reference to summary
```

### 1. Start Sprint

Create `.github/plan/sprint/sprint-XX-description.md` with:
- Clear goal statement
- Detailed tasks with checkboxes `- [ ]`
- Acceptance criteria
- Any dependencies or blockers

**Example:**
```markdown
# Sprint 42: Feature Name

**Goal:** Brief description of what this sprint achieves.

---

## Tasks

### Phase 1: Setup
- [ ] Task 1
- [ ] Task 2

### Phase 2: Implementation
- [ ] Task 3
- [ ] Task 4

---

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

### 2. Execute Sprint

- Check off tasks as completed: `- [x] Task 1`
- Add notes for decisions made
- Track blockers and how they were resolved
- Update progress summary if sprint spans multiple sessions

### 3. Automated Testing

Before handoff, run ALL applicable checks:
```bash
pnpm build          # TypeScript compilation
pnpm lint           # ESLint
pnpm test           # Unit tests
pnpm test:e2e       # E2E tests (if configured)
```

**Goal:** Minimize manual verification - user should only need to spot-check.

### 4. Handoff

Provide to Product Owner:
1. Summary of what was built
2. Exact test steps/commands
3. What to verify (specific flows, edge cases)
4. Any known limitations or future work

### 5. Close Sprint

After Product Owner approval:

1. **Create summary:** `.github/plan/sprint_backup/sprint-XX-YYYY-MM-DD.md`
   ```markdown
   # Sprint XX: Feature Name - Summary

   **Date:** YYYY-MM-DD
   **Status:** Completed

   ## What was done
   - Item 1
   - Item 2

   ## Key commits
   - `abc1234` - commit message

   ## Notes
   Any relevant notes for future reference.
   ```

2. **Delete** the detailed sprint document from `.github/plan/sprint/`

3. **Commit and push:**
   ```bash
   git add -A
   git commit -m "docs: close sprint XX - brief description"
   git push
   ```

### 6. Update Backlog

In `.github/plan/backlog.md`:
- Mark iteration as `DONE`
- Add reference to sprint summary file
- Note any carry-over items

---

## Backlog Format

```markdown
# Product Backlog

## Current Sprint
- Sprint XX: [Description] - IN PROGRESS

## Completed
- Sprint XX: [Description] - DONE (see sprint_backup/sprint-XX-YYYY-MM-DD.md)

## Upcoming
- [ ] Feature 1
- [ ] Feature 2

## Ideas / Someday
- Idea 1
- Idea 2
```

---

## Best Practices

### Sprint Documents
- Keep under 500 lines
- Use clear section headers
- Track progress with checkboxes
- Include commit hashes for reference

### Communication
- Explain approach before implementing
- Ask clarifying questions early
- Provide options when multiple approaches exist
- No time estimates (focus on what, not when)

### Code Quality
- Run automated tests before handoff
- Keep changes focused and minimal
- Don't over-engineer
- Commit frequently with clear messages

### Handoff
- Be specific about what to test
- Provide exact commands/steps
- Note any environment requirements
- List known limitations

---

## Sprint Naming Convention

```
sprint-XX-brief-description.md
```

- `XX` = Sprint number (zero-padded)
- `brief-description` = 2-4 words describing the sprint goal
- Use kebab-case

**Examples:**
- `sprint-01-initial-setup.md`
- `sprint-15-payment-integration.md`
- `sprint-42-hetzner-migration.md`

---

## Git Commit Format

```
type(scope): brief description

- Detail 1
- Detail 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <model>@anthropic.com
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance

---

## Quick Reference

| Action | Command/Location |
|--------|------------------|
| Start sprint | Create `.github/plan/sprint/sprint-XX-desc.md` |
| Track progress | Update checkboxes in sprint doc |
| Close sprint | Move summary to `sprint_backup/`, delete sprint doc |
| Update backlog | Edit `.github/plan/backlog.md` |
