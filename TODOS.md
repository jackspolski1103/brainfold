# TODOS

## Core

### Review before publishing

**What:** Hold what an agent writes into a shared folder as a proposal until a person approves it.

**Why:** Today write permission publishes directly (decision 0008). A wrong or malicious skill written by a member with write reaches every reader of that folder with no human check.

**Context:** Deferred in the CEO review of 2026-11-12 (D10). The author is interested, but it reverses decision 0008 and is the largest addition considered. The current bound is the skill trust model: write permission declared only by an administrator, path and author shown on use, history. Start from the revision records of phase 2, which already carry author and a read-list snapshot; a proposal could be a revision that is not yet current.

**Effort:** L (human) / M (CC)
**Priority:** P2
**Depends on:** Phase 2 revision records; real skills in circulation to design against.

### One-time download links for agents without a shell

**What:** Issue a short-lived, single-use link for one path so a chat client without a terminal can open a binary file.

**Why:** Binary files move through `brainfold put` and `brainfold get`, which need a shell. A client without one knows the file exists but cannot open it.

**Context:** Deferred in the CEO review of 2026-11-12 (D14). First targets (Claude Code, Codex) have a shell. A link grants access without a token and passes through the model's context, which the design avoids for tokens, so it needs a tight lifetime and its own tests.

**Effort:** M (human) / S (CC)
**Priority:** P3
**Depends on:** Phase 2 binary files and cross-machine exposure.

## Found by QA on 2026-11-12 (low severity, deferred)

### Panel: clear the new-group form after creating a group

**What:** The Members field of the new-group form keeps its text after the group is created.

**Why:** The next group starts with the previous members typed in.

**Context:** `web/src/Admin.tsx`, `saveGroup` clears the name but not the `"+"` draft. Repro: Members, fill New group and Members, Create.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Panel: say "administrators only" instead of an empty page

**What:** A member who opens `#/members` or `#/activity` sees an empty page.

**Why:** It looks broken.

**Context:** `web/src/App.tsx` renders nothing for those routes when the user is not an administrator.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Panel: link to the person's own folder

**What:** Show "Your folder" on the Brain page, using `home` from the root listing.

**Why:** A member has to know to look under `people`.

**Context:** `Listing.home` is already returned by `/api/tree?path=/` and unused in `web/src/Brain.tsx`.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Agent: reading a folder should point to `list`

**What:** `read` on a folder the caller can read answers "The path is not available."

**Why:** The agent cannot tell a wrong tool from a missing path.

**Context:** `Brain._bytes` in `src/brainfold/brain.py`. Only do it when the caller can read the folder, so nothing new is revealed.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Command line: do not announce the server before it binds

**What:** With the port in use, `brainfold serve` prints "Brainfold · MCP at ..." and then the bind error.

**Why:** The first line says it is running when it is not.

**Context:** `src/brainfold/cli.py` prints before `uvicorn.run`.

**Effort:** S
**Priority:** P3
**Depends on:** None

### Panel: check dark mode

**What:** The panel has dark styles that were never looked at.

**Why:** Not verified by any QA pass.

**Context:** Styles use Tailwind `dark:` variants following the system setting.

**Effort:** S
**Priority:** P3
**Depends on:** None

## Completed
