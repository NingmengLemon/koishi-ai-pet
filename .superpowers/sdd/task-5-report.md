# Task 5 Report: todo_list Storage Layer

## Status
**Complete**

## Commits
- `3dd35a0` feat(todo): add SQLite storage layer

## Files Created
- `pet/skills/plugins/todo_list/__init__.py` (empty)
- `pet/skills/plugins/todo_list/storage.py` (TodoStorage class)

## Test Summary
All 5 assertions passed:
- **add**: Returns correct row dict with auto-generated id
- **list**: Returns single item after add
- **update**: Modifies title and priority
- **complete**: Sets status='done' and populates completed_at
- **delete**: Returns True and removes row

## Concerns
- The `list` method name shadows the built-in `list` type, causing annotation evaluation errors. Added `from __future__ import annotations` to defer annotation evaluation and resolve the conflict.

## Fix Round 1

### Status
**Complete** — all three code-review findings fixed and verified.

### Changes
Fixed three issues in `pet/skills/plugins/todo_list/storage.py`:

1. **`get_due` now respects `precision_minutes`** (Critical): The method computes `window_end` by adding `precision_minutes` to `now_iso` via `datetime.timedelta`. When `precision_minutes > 0`, it queries `due_date <= window_end`; when `0`, it queries `due_date <= now_iso` (exact due/overdue only).

2. **`update` early-return thread safety** (Important): The SELECT when `updates` is empty was running outside `self._lock`. Wrapped it with `with self._lock:`.

3. **`get_pending_alarms` timezone consistency** (Important): Removed the hardcoded `datetime('now')` (SQLite UTC) that mismatched the app's local-time storage. Added an optional `now_iso` parameter — callers pass the same local-time ISO string used elsewhere. Legacy `datetime('now')` behavior is preserved when `now_iso` is `None`.

### Test Summary
All 6 assertions passed:
- **get_due window** (precision_minutes=5): Found 2 tasks within window (future + past)
- **get_due exact** (precision_minutes=0): Found 1 past/overdue task only
- **update thread safety (nonexistent id)**: Returns None without crash
- **update thread safety (existing id)**: Returns dict without crash
- **get_pending_alarms with now_iso**: Returns list, future task found
- **get_pending_alarms without arg**: Backward-compatible, returns list
