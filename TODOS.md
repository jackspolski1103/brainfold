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

**Why:** Binary files move through `oif put` and `oif get`, which need a shell. A client without one knows the file exists but cannot open it.

**Context:** Deferred in the CEO review of 2026-11-12 (D14). First targets (Claude Code, Codex) have a shell. A link grants access without a token and passes through the model's context, which the design avoids for tokens, so it needs a tight lifetime and its own tests.

**Effort:** M (human) / S (CC)
**Priority:** P3
**Depends on:** Phase 2 binary files and cross-machine exposure.

## Completed
