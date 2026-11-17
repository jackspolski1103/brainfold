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

### Low-severity findings of the 2026-11-17 QA

**What:** Eight low findings left open by /qa on 2026-11-17 (ISSUE-008 to ISSUE-015).

- ISSUE-008 (CLI): a malformed `~/.config/brainfold/config.toml`, and `reset-password --db` pointing at a file that is not a database, print a Python traceback. Repro: `printf 'x [[[' > config.toml; brainfold get /a ./a`.
- ISSUE-009 (API): `PUT /api/folder` accepts `read` or `write` given as a string (`"*"`) instead of a list.
- ISSUE-010 (server): an accounts database locked by another process for more than 5 s answers HTTP 500 instead of a classified error. Repro: `BEGIN EXCLUSIVE` from `sqlite3`, then any call.
- ISSUE-011 (MCP): `write` accepts a NUL character; the file then counts as binary and cannot be read or edited over MCP.
- ISSUE-012 (MCP): `read` with a negative `limit` drops the last line without saying so.
- ISSUE-013 (MCP): `move` that changes only the capitals of a name answers `unavailable`.
- ISSUE-014 (panel): "1 tokens" on the overview; "500 events in 24 h" when the list is capped at 500; on a phone the search results need horizontal scrolling to show the text.
- ISSUE-015 (MCP): two skills with the same front-matter `name` make `use_skill` by that name answer "not available" instead of naming the ambiguity.

**Why:** None loses data or crosses a permission; each is a rough edge an agent or a person meets.

**Context:** Report in `.gstack/qa-reports/run-20261117T131822Z/`. Still to run from that QA: Codex model-driven tool calls (blocked by an account usage limit on the day) and `docker compose` behind Caddy.

**Effort:** S (human) / S (CC)
**Priority:** P3

### Findings of the 2026-11-17 Deepsec scan left open

**What:** Two of the fourteen findings are not fixed; the rest are, with regressions in `tests/test_regression_deepsec_20261117.py` and `web/markdown.check.cjs`.

- The activity log is read 1000 rows at most, with no way to reach older ones and no retention. Failed logins no longer flood it (unknown emails and throttled attempts are not recorded), but the panel still cannot page back.
- The author of a learning comes from the file's own text, so whoever can write a LEARNINGS.md can sign an entry with any name (`list_learnings` says attribution is advisory; `history` has the real author). The panel now only shows a byline for a plain date and name.

**Why:** The first needs a paging design in the panel, the second follows from write permission on a file.

**Context:** Scan output in `.deepsec/` (run 20261117134953-34a6f2fe41a91785). The quadratic `list` is under "Throughput under one lock". `npm test` in `web/` runs the markdown check; CI does not run it yet.

**Effort:** S (human) / S (CC)
**Priority:** P2

### Throughput under one lock

**What:** Decide how far to take concurrency: reads wait behind writes because one lock serializes everything, and `search`, `use_skill`, `tools/list` and `/api/skills` walk the readable tree under it.

**Why:** Measured on 2026-11-17 after fixing ISSUE-001: 27 agents get 19 calls/s and a read waits 1.2 s (p50); a search on a 3,000-file brain holds everyone for 2.4 s.

**Context:** The ceilings are marked in the code (`ponytail:` comments in `brain.py`). The Deepsec scan of 2026-11-17 added one: `list` checks every child with `_real`, which lists the same folder again, so a folder of N entries costs N² directory reads under the lock. Options: cache the skills listing per person until the brain changes; a read/write lock; a text index for search. An architecture decision for the author.

**Effort:** M (human) / S-M (CC)
**Priority:** P2

## Completed

- QA low-severity findings ISSUE-005 to ISSUE-009 (new-group form, administrators-only notice, link to the personal folder, reading a folder, busy port) and the dark mode check. Fixed on main, 2026-11-12, after /qa.
- QA findings ISSUE-001 to ISSUE-007 of 2026-11-17 (per-request tree walk, uploads removed by another caller's error, unbounded JSON bodies, cut lines, non-text descriptions, capitals in emails, CLI paths). Fixed by /qa on qa-fixes-2026-11-17, 2026-11-17.
