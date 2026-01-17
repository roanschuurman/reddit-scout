# Sprint 07: Discord Enhancements

**Goal:** Complete the Discord workflow with regenerate, refine, and copy functionality for AI drafts.

---

## Tasks

### Phase 1: Regenerate Button

- [ ] Add "Regenerate" button to `MatchActionView`
  - Calls existing `ResponseGenerator.regenerate_response()` method
  - Updates embed with new draft content
  - Shows loading state while generating
- [ ] Update embed to show draft version number (v1, v2, etc.)
- [ ] Handle rate limiting / cooldown for regenerate requests

### Phase 2: Refine Button with Thread Conversation

- [ ] Add "Refine" button to `MatchActionView`
  - Creates a Discord thread attached to the notification message
  - Thread title: "Refine: [first 50 chars of post title]"
- [ ] Implement thread-based conversation handler
  - Bot listens for messages in refine threads
  - Each user message treated as feedback
  - Generates new draft incorporating feedback via `regenerate_response(feedback=...)`
  - Posts new draft in thread
- [ ] Add "Use This Draft" button in thread to finalize
  - Updates main notification embed with selected draft
  - Optionally archives the thread
- [ ] Track thread-to-match mapping for persistence

### Phase 3: Copy Button

- [ ] Add "Copy" button to `MatchActionView`
  - Sends ephemeral message with just the draft text (easy to copy)
  - Includes "Copy this response:" header for clarity
- [ ] Format the copy-friendly message
  - Plain text only (no embed formatting)
  - Include the Reddit permalink for context

### Phase 4: Polish

- [ ] Ensure buttons remain functional after bot restart (persistent views)
- [ ] Add loading indicators for async operations
- [ ] Handle edge cases (no draft exists, thread already created, etc.)
- [ ] Update button states after actions (disable used buttons where appropriate)
- [ ] Error handling with user-friendly messages

---

## Acceptance Criteria

- [ ] User can click "Regenerate" to get a fresh AI draft
- [ ] Regenerated draft updates the notification embed
- [ ] User can click "Refine" to open a conversation thread
- [ ] User messages in thread generate revised drafts
- [ ] User can click "Copy" to get a copy-friendly version of the draft
- [ ] All buttons work after bot restarts
- [ ] All new code has tests
- [ ] Ruff + mypy pass

---

## Technical Notes

**Existing code to leverage:**
- `bot/views.py` - `MatchActionView` with Done/Skip buttons
- `bot/notifications.py` - `build_match_embed()` for updating embeds
- `ai/generator.py` - `ResponseGenerator.regenerate_response(feedback=...)` already exists!

**Discord.py patterns needed:**
- `discord.ui.Button` - Already using this
- `interaction.channel.create_thread()` - For creating refine threads
- `@bot.event on_message` - For handling thread messages
- `interaction.response.send_message(ephemeral=True)` - For copy button

**Button layout:**
```
[✅ Done] [⏭️ Skip] [🔄 Regenerate] [✏️ Refine] [📋 Copy]
```

**Persistent view registration:**
- Views with `timeout=None` persist across restarts
- Need unique `custom_id` for each button
- Match ID stored in view, not custom_id (custom_id must be static for persistence)

**Thread handling considerations:**
- Store thread_id on Match model? Or use in-memory mapping?
- Consider: what if user creates multiple threads?
- Thread auto-archive after inactivity

---

## Database Changes

Consider adding to `Match` model (optional, can use in-memory first):
- `discord_thread_id: str | None` - Track refine thread

---

## Out of Scope

- Voice channel notifications
- Reaction-based interactions
- Scheduled regeneration
- Multi-draft comparison view
