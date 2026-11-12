# Plan: OIF core, permissioned memory that spreads on its own

Status: scope decided in CEO review (SELECTIVE EXPANSION), 2026-11-12; not yet implemented. Branch: main.
Source design: approved /office-hours design of 2026-11-12 (Spanish original kept outside the repo in the author's local gstack store).
Approving this plan implies updating `docs/scope.md` and recording a new decision in `docs/decisions/`.

## Goal

OIF is an MCP server that turns a folder into a team's shared brain: files with per-folder permissions that any harness reads and writes. This plan covers the core only. The web panel comes after.

Two scenes define success:

1. **The skill that spreads.** An agent solves something hard and writes it as a skill. The next day a teammate's agent, on a different harness, can do it without anyone telling it.
2. **Day one without asking.** A new person connects their agent and it walks the folders, guided by each folder's description and "start here", until it can explain how the team works.

Strong permissions are a necessary condition, not the pitch. Being harness-agnostic is a requirement, not the value.

## Premises (accepted by the author)

1. The hook is that knowledge spreads on its own.
2. The agent is the main author: within its permissions it creates folders with guidance, edits, moves and writes skills without waiting for an administrator.
3. OIF stores files and controls access. It does not interpret them. Reading a PDF or a spreadsheet is the harness's job.
4. Skills reach the harness natively.
5. It installs with one command.
6. First proof is a built example case, plus OIF's own brain (`brain/`, its own git repository, ignored by the code repository) used daily.

## Constraints

- No own harness, connectors, embeddings, format readers or multi-tenant hosting (`docs/scope.md`).
- Python. One server per team, one organization per server. Own accounts with email and password (decision 0009).
- Personal project: no work data, accounts or credentials.
- Folder permissions live in plain `.oif.toml` files. Accounts, groups, tokens and activity live in one SQLite file, which must not be inside the brain root.
- **The whole repository is in English** (author instruction, 2026-11-12): code, tool names, error codes and messages, docs, examples, `AGENTS.md`.
- Today: 831 lines in `src/oif/`, 11 passing tests, dependencies `mcp` and `uvicorn`.

## Scope

### Rules common to every write

- **One process lock** around compare-version, write and git commit, for MCP and HTTP alike.
- **Version.** Every read returns `version`, a digest of the whole file. It is required to replace, move or delete an existing file; a mismatch returns `conflict` with the current version and writes nothing. Optional for `edit` (the unique fragment already detects change). Not applicable to `append`. Creating a file that already exists fails with `already_exists`.
- **Text and binary.** Text is valid UTF-8 with no NUL bytes; everything else is binary. Over MCP, text files can be written, edited and appended up to 1 MB. `read` returns at most 64 KB per call with `offset` and `limit` in lines and a `truncated` flag; a line longer than the cap is cut and flagged. `append` that would exceed 1 MB fails with `file_too_large` and suggests rotating the file. `search` scans text files up to 1 MB and reports how many it skipped.
- **History in git.** `oif serve` initializes a git repository in the brain root if there is none and commits existing content. If the root already has `.git`, it is used and a warning is printed. Without git installed the server starts with a warning and every write answers `versioned: false`. Everything saved is committed, text or binary, up to the size limit. If a commit fails the operation answers `versioned: false`.
- **Activity.** Every operation over MCP or HTTP is logged, denials included.

### Layer 1: complete file operations

Tool names are English: `list`, `read`, `write`, `edit`, `append`, `move`, `delete`, `create_folder`, `describe_folder`, `search`.

- `edit(path, old, new)` replaces one exact, unique fragment.
- `append(path, content)` appends; creates the file if missing.
- `move(source, destination, version)` and `delete(path, version)` for files. Write is required on both sides. Existing destination fails with `already_exists`. `move` creates intermediate folders. Moving a file into a folder with more readers is allowed to whoever can write both sides (writing into a folder already publishes to its readers, decision 0008); activity records both paths.
- `create_folder(path, description, start_here)` and `describe_folder(path, description, start_here)`: the agent creates folders and writes their guidance where it can write. They only touch `description` and `start_here` and never change `read` or `write`. `start_here` entries are paths relative to the folder with no `..`, so guidance survives a move; the existing example's absolute entries are converted in step 2, together with the validation change.
- **Personal folder** `/people/<alias>/`. The alias derives from the email (sanitized local part plus a short digest), is UNIQUE in the accounts database (lengthened on collision) and is assigned when the account is created. `/people` is reserved: only the server creates its direct children, and any agent operation on `/people/<x>` fails unless `<x>` is the requester's alias. The owner rule is absolute and takes precedence over any `.oif.toml`: `read` and `write` keys inside a personal folder are ignored, and the panel API rejects editing access there. The folder is created on first authenticated use. When a member is removed the folder stays on disk and becomes inaccessible, and the alias is kept as a tombstone so re-inviting the same email gets a new alias and never reopens the old folder; an administrator handles the old folder on disk. An administrator's manage listing shows the names under `/people` and nothing inside them. Moving a shared file into one's personal folder is treated like deleting it from the shared folder: it needs write there and is logged with both paths.
- **Binary files are uploaded and downloaded by the person with a command.** `oif put <file> <path>` and `oif get <path> <dest>`. The command reads the server URL and token from `OIF_URL` and `OIF_TOKEN`, or from `~/.config/oif/config.toml` with mode 0600; it never prints them or accepts them as arguments. The guarantee is that neither the server nor the command exposes the token. An agent with a shell in that same environment could read it, like any other credential there: that boundary belongs to the harness sandbox, not to OIF. Over MCP, `read` of a binary returns type, size, version and the command to fetch it, never a URL with credentials. Default limit 25 MB per file, configurable, enforced while receiving.
- **HTTP file routes.** `PUT` and `GET /files/<path>` accept only `Authorization: Bearer`, never the panel cookie. `GET` returns `ETag`; `PUT` over an existing file requires `If-Match`. `oif put` on an existing path fails with `already_exists` unless `--replace`, which fetches the current version and sends it; a change in between fails with `conflict`. Downloads answer with `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` and `application/octet-stream`.

### Layer 2: the brain arrives on its own

- **Skills through a `use_skill` tool (author decision D18).** The description of `use_skill` lists, for the calling identity, the name and one-line description of every readable, valid skill, and the same listing travels in the server instructions returned at session start, so the model sees them in every session and calls `use_skill(name)` to receive the procedure. The instructions are the path that works in Claude Code, which defers MCP tool descriptions until the model searches for a tool (spike T1, 2026-11-12); the tool description remains for harnesses that load it. The instructions carry at most 12 skills with descriptions cut to 120 characters and point to the tool for the rest. This is how the skill spreads without anyone telling the agent, and it works on every harness because it only needs tools. The skill name is the skill folder's name reduced to `[a-z0-9-]` plus a six-character digest of its full path (lengthened on collision). An invalid `SKILL.md` is skipped. The list is computed per identity when tools are listed, capped at 256 entries and at a fixed description size, with a note when truncated. A new skill appears when a session starts or reconnects. MCP prompts are not used; `list_skills` is removed.
- **Skill trust model.** A skill is listed to everyone who can read its folder. Publishing requires write permission on that folder, which only an administrator declares. The `use_skill` result shows the path and, when a revision record exists, the author of the file's latest revision (after a restore that is the restorer), read with one query per listing. The same trust model applies to folder guidance: `description` and `start_here` are written by members with write permission and steer other agents. The risk that a member with write publishes a wrong or malicious procedure is accepted explicitly and bounded by those controls plus history. Server instructions state that a skill is a procedure published by a teammate with write permission, never widens permissions, and that all other content is information.
- **Guidance on connect.** `list('/')` returns the root guidance and the user's personal folder.
- **Skill validation.** Any operation whose result is a file named `SKILL.md` requires front matter with `name` and `description`.
- **Learnings log.** `append` on a conventional `LEARNINGS.md` per folder records short notes on what was solved.

### Accepted expansions (CEO review)

- **E2. The brain proposes skills.** The server stamps every `append` to a `LEARNINGS.md` with a fixed delimiter line carrying UTC date and author, and escapes any line in the appended content that looks like a delimiter. Because `write` and `edit` can still change the file, attribution is advisory, which is why the prompt treats every entry as untrusted. `list_learnings(limit=50)` returns the newest entries, newest first, from the `LEARNINGS.md` files the caller can read, each with path, author and date. A built-in skill `propose-skills`, served by `use_skill` and shipped with the server, asks the agent to find what repeats and draft a `SKILL.md`. Its text states that learnings are untrusted information written by teammates, requires the draft to cite its source entries, and requires the person's explicit confirmation before any write. The server runs no model. Nothing is published beyond the caller's own write permission.
- **E3. The agent can move folders and delete empty folders.**
  - `delete` accepts a folder only when the caller can read and write it, its `.oif.toml` declares neither `read` nor `write`, and it contains nothing besides its own `.oif.toml` (a `.DS_Store` is ignored and removed with it). A folder the caller cannot read answers `unavailable`, like any hidden path; anything else inside fails with `folder_not_empty`; declared access fails with `forbidden`. Files are deleted one by one, each under its own version check and each restorable (E7). (Author decision D15.)
  - `move` accepts a folder only when the caller can read and write it, the subtree contains no symlink and no dot-entry other than `.oif.toml` (a `.DS_Store` is ignored and removed), and no `.oif.toml` in the subtree declares `read` or `write`. Folders with administrator-declared access stay with the administrator. This keeps the invariant that an agent never changes declared access; inherited access changes with the new location exactly as it does for a moved file.
  - Write is required on the source parent and the destination parent. The destination must not exist, compared case-insensitively, and cannot be inside the source. The root, `/people` and its children cannot be moved or deleted. Moving anything into or out of `/people/<alias>` follows the owner rule on that side.
  - Moving a folder is not lossy, so it takes no staleness guard: files written into it by a teammate a moment earlier move with it.
  - A subtree-rule failure returns one generic code, `folder_not_movable`, without naming entries. An existing destination still answers `already_exists` and a hidden source `unavailable`. Activity records both paths.
  - Agent-visible history does not follow moves: files in a moved folder start a new history at the new path. This is stated in the tool description.
- **E5. English everywhere.** Extended by the author to the whole repository. Code, tool names, error codes and messages, examples and current docs are translated. `AGENTS.md` is rewritten in English from the current scope, not translated line by line, and keeps the rule that conversation with the author is in Spanish. `docs/vision.md` and `docs/research/` are removed from the repository and replaced by one short English page on prior art and how OIF differs (author decision D16); they remain in git history. Every error code and every activity action name in `src/` is renamed to English; step 1 produces the full table and ends with a one-time search showing that no identifier from the fixed list of current Spanish codes and action names remains in `src/`, `tests/` or `examples/`. `docs/decisions/0007` to `0009` are translated and `0001` to `0006`, all superseded, are replaced by one English summary of superseded decisions. Main renames: `ruta_no_disponible` to `unavailable`, `sin_permiso_escritura` to `write_denied`, `archivo_demasiado_grande` to `file_too_large`, `no_autenticado` to `unauthenticated`, `sin_permiso` to `forbidden`, `metadata_invalida` to `invalid_metadata`, `solicitud_invalida` to `invalid_request`; new codes are `conflict`, `already_exists`, `folder_not_empty`, `folder_not_movable`, `no_history`, `invalid_skill`.
- **E6. Usable across machines.**
  - `oif serve` may listen beyond loopback only with `--public-url https://…`, meaning it runs behind a TLS-terminating proxy on the same host or network. Session cookies are then always `Secure`.
  - **Claiming the server.** Whenever `--public-url` is set, wherever the server binds, `/api/setup` requires a setup code that `oif serve` prints at startup while no account exists. The code is single-use and stops working once an account exists. Without it the first administrator cannot be created.
  - **Login throttle** stays in process memory (the compose file runs exactly one server process, consistent with the single lock) and is keyed by email plus client address. The client address is taken from the proxy's forwarded header only when `--public-url` is set, and the compose file does not publish the server's own port, so clients cannot reach it directly and spoof that header.
  - `oif put` and `oif get` refuse URLs that are neither HTTPS nor loopback.
  - A `Dockerfile` (with git installed) and a `compose.yaml` with a TLS proxy ship with the repository. The brain root and the accounts database are separate volumes owned by the server user. The server refuses to start when the database is inside the brain root.
- **E7. History and restore.**
  - **Revision records.** Under the write lock, every OIF change to a file (write, edit, append, move in, move out, delete, restore) adds a row to a `revisions` table in the accounts database: path, git commit, author, UTC time, change type, and a snapshot of the `read` lists that governed the path at that moment (every ancestor `.oif.toml` `read` list as it was on disk, or the personal-folder owner). Rows are only written when the commit succeeded. When a change hits a file that has no revision at that path (committed at `oif serve` start, added by hand, or never recorded), the server first commits it as it is and records a `baseline` row with the current snapshot, so the prior content is always restorable. A folder move writes a move-out and a move-in row for every file in it.
  - **Who sees a revision.** A caller sees or restores a revision only if they would have been allowed to read the path under that revision's snapshot, evaluated with today's group membership, and they can read the path today (for a missing file: read and write on its parent folder, which must exist). Joining a group later reveals that group's earlier revisions and leaving hides them; that is intended. To keep names from being reused against old snapshots, a deleted group name cannot be recreated, and a direct email grant in a snapshot does not match revisions older than the caller's account. This replaces any git-based cut-off: reusing a path, hand-editing `.oif.toml`, widening `read` later or a pre-existing `.git` cannot expose earlier restricted content, and editing grants does not erase history for people who already had access.
  - `history(path)` returns revision id, author, date and change type of the revisions the caller may see for that exact path: no content, no other paths, no following of moves.
  - `restore(path, revision, version)` requires write on the path (for a missing file: write on its existing parent folder; restore never creates folders), a revision the caller may see whose change type left content (not a delete or move out), and `version` when the file currently exists. It sets the file to the content at that revision's commit and records a new revision. Restoring a `SKILL.md` re-runs validation.
  - Folders are not restorable by agents. Files deleted before their folder was deleted are restorable only once a folder exists at that path again and the caller passes the snapshot rule.
  - Without git, for paths with no recorded revision, when no revision is visible to the caller, or when the revision id belongs to another path, both answer `no_history`.
  - `restore` works for binary files too, since it happens on the server. Binary versions accumulate in git with no pruning; pruning is an administrator task outside this plan.

## NOT in scope

- **E1. Review before publishing** (deferred to TODOS.md): reverses decision 0008; design it after real usage.
- **E4. One-time download links for agents without a shell** (deferred to TODOS.md): first targets have a shell; adds token-less access.
- MCP resources: duplicates `read`, serves neither scene.
- MCP prompts for skills: they are invoked by a person, not by the model, so they do not make a skill spread (D18).
- Automatic skill proposal run by the server (needs a model).
- Synced-folder client (approach C): sync conflicts, one client per machine, local copies revocation cannot delete.
- Web panel UI: next increment.
- Hot refresh of the prompt list inside an open session: the server is stateless.
- Recursive folder delete and folder restore by agents (D15).
- Exposing git history directly to agents: revisions come only from OIF's own records.
- Moving the login throttle to the database: one server process is assumed.
- Choosing a hosting provider or container registry: pending author decisions.

## Success criteria

- In the example case, an agent creates a skill; in a new session a second account's `use_skill` description lists it, and that agent uses it for a matching task without being told (live check with Claude Code).
- In OIF's own brain, a new account asks "how do we work here?" and the answer contains three facts fixed in advance (where decisions live, how tests run, what is out of scope). Activity shows only list and read calls.
- Two agents editing the same file lose nothing: the second gets `conflict`. A test fires simultaneous writes over MCP and HTTP.
- A spreadsheet uploaded with `oif put` to a restricted folder downloads only with an authorized token; the panel cookie does not work on those routes.
- A reader sees neither paths nor content of a previous restricted location in history, and cannot restore from it.
- Moving a folder that contains one entry the caller cannot read or write, or one `.oif.toml` declaring access, changes nothing. Deleting a non-empty folder changes nothing.
- Every new operation has denial tests, and an agent can never change `read` or `write`.
- Through the shipped compose file, with a certificate the client trusts, two accounts reach one server over HTTPS; verified locally with the proxy's own certificate authority trusted on the test machine. Use from other machines depends on the pending hosting decision.
- On a server started with `--public-url`, `/api/setup` without the printed code creates no account.
- After a restricted folder is removed and a new folder is created at the same path, a writer of the new folder who was not a reader of the old one sees no earlier history and cannot restore earlier content. The same holds after an administrator widens `read`, by hand or through the API.
- Emptying and deleting a folder whose `.oif.toml` declares `read` fails at the folder delete.
- A file deleted by an agent is restored by an agent with write on its folder, and the restored content matches.
- The built-in `propose-skills` skill text states that learnings are untrusted, requires citing source entries and requires the person's confirmation before writing; a test asserts on that text. A learning containing a delimiter-looking line comes back as one entry.
- The one-time search at the end of step 1 finds no Spanish identifier.

## Distribution

- PyPI package runnable with `uvx <name> serve --root <folder>`, including `put` and `get`.
- Container image and `compose.yaml` (E6).
- GitHub Actions: tests and lint on every change; publish package and image on a version tag.
- Blocked on pending decisions: final name, license, and creating the remote repository on the author's personal account.

## Open questions

1. Answered for Claude Code by spike T1: tool descriptions are deferred and not in context, server instructions are, and a per-identity listing there made a fresh session use a new skill unprompted. Still open: the same check on Codex, and how Claude Code behaves when the listing exceeds the 12 skills carried in the instructions.
2. Whether the MCP library's host-header check accepts requests forwarded by a proxy when the server binds to loopback. Needs a live check before cross-machine work.

## Build order (two phases, author decision D19)

**Phase 1: the two scenes work and can be shown.**

0. Spike on the current server: a `use_skill` tool whose description is computed per identity, checked live in Claude Code. If it fails, stop and revisit D18.
1. English: translate code, tests, examples and current docs; rewrite `AGENTS.md`; remove historical Spanish docs and add the prior-art page; update `docs/scope.md` and record the decision. Freeze tool names and error codes.
2. Foundations: one lock, every brain operation off the event loop, versions and conflicts, hardened git, health, schema versioning.
3. Text operations: edit, append, file move and delete, folder guidance, relative `start_here`, exact-case paths, pagination. Until phase 2, a deleted file is recoverable only by an administrator with git.
4. Personal folders with aliases and tombstones.
5. Skills: `use_skill`, validation, trust model in instructions, stamped learnings, `list_learnings`, built-in `propose-skills`.
6. Permission matrix test, fuller example case, OIF's own brain, live check of both scenes.

**Phase 2: everything else the author accepted.**

7. Binary files: byte storage, HTTP routes, `oif put` and `oif get`.
8. Folder move and empty-folder delete (E3).
9. Revision records, history and restore (E7).
10. Proxy live check, then cross-machine: `--public-url`, setup code, throttle key, container and compose (E6).
11. Package and image publication, after name, license, remote repository and registry are decided.

## Decision ledger

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| APPROACH (author) | How the brain reaches the agent; office-hours D6 | Tools only | B: full protocol | approved | D6 answer "B. Protocolo completo" |
| DESIGN (author) | Design document; office-hours D7 | Draft | Approved design | approved | D7 answer "Aprobar" |
| E2 (author) | Brain proposes skills; D8 | Learnings log only | `list_learnings` + `propose-skills` prompt | approved | D8 "Agregar" |
| E6 (author) | Cross-machine use and container; D9 | Loopback only | `--public-url`, Secure cookies, setup code, in-memory throttle keyed by email and address, compose | approved | D9 "Agregar" |
| E1 (author) | Review before publishing; D10; decision 0008 | Write permission publishes | Proposal and approval flow | deferred | D10 "Postergar a TODOS.md" |
| E5 (author) | English across the repository; D11 plus instruction "todo el repo debe estar en ingles" | Spanish | English across the repository | approved | D11 "Agregar", widened by the author's message |
| E3 (author) | Agent moves and deletes folders; D12 | Files only | All-or-nothing subtree rule | approved | D12 "Agregar" |
| E7 (author) | Restore previous version; D13 | No history tool exists | `history` + `restore` over OIF revision records with a read-list snapshot | approved | D13 "Agregar" |
| E3-DELETE (author) | Which folders an agent deletes; D15; spec review issues 3 and 4 | All-or-nothing recursive | Empty folders only | approved | D15 "Solo carpetas vacías" |
| E5-HISTORICAL (author) | Spanish `docs/vision.md` and `docs/research/`; D16 | In repository, Spanish | Removed, replaced by a short English prior-art page | approved | D16 "Sacar y resumir" |
| SAFETY-FIXES (review; affects rows E2, E3, E6, E7) | Spec review rounds 1 to 3: baseline revisions, no folder creation on restore, group-name and email reuse guards, revision snapshot rule, no agent move or delete of folders with declared access, setup code under `--public-url`, stamped and untrusted learnings | Missing | Repairs needed to keep approved invariants | approved | D17 "Aprobar y seguir" |
| E4 (author) | Downloads without a shell; D14 | `oif get` only | One-time links | deferred | D14 "Postergar a TODOS.md" |
| DOCS-APPROVAL (author) | Working plan and CEO summary, including SAFETY-FIXES; D17 | Unapproved documents | These document versions | approved | D17 "Aprobar y seguir"; also signs off SAFETY-FIXES and accepts that round 3 fixes were not re-read by a reviewer |
| REVIEW-REPAIRS (review, sections 2 to 9) | Requirements needed to keep approved invariants and operability: case-insensitive reserved names, visible commit failures, storage errors, pagination, upload outside the lock, schema versioning | Missing | Listed under "Review requirements" | approved | In scope as repairs to approved criteria under D17 ("an agent can never change read or write", "nobody else can", no silent loss) |
| SKILL-DELIVERY (author) | How skills reach the agent; outside review finding 1; D18 | MCP prompts (person-invoked) | `use_skill` tool with a per-identity listing; no MCP prompts | approved | D18 "Herramienta use_skill" |
| PHASING (author) | Delivery order; outside review findings 2 to 4; D19 | One sequence of nine steps | Two phases, spike first | approved | D19 "Dos tandas" |
| OUTSIDE-REPAIRS (review) | Outside review findings 5 to 10: R11 to R15 and the changed R2 | Missing | Listed under "Review requirements" | approved | Repairs to approved criteria under D17 (no silent loss, visible failures); announced to the author before D18 and D19 |

Approval readiness: PASS. Checked rows: APPROACH (D6), DESIGN (D7), E2 (D8), E6 (D9), E1 deferred (D10), E5 (D11 and the author's message), E3 (D12), E7 (D13), E4 deferred (D14), E3-DELETE (D15), E5-HISTORICAL (D16), SAFETY-FIXES and DOCS-APPROVAL (D17), SKILL-DELIVERY (D18), PHASING (D19), REVIEW-REPAIRS and OUTSIDE-REPAIRS (repairs under D17).

## Temporal interrogation

- **Hour 1 (foundations).** The implementer needs the fixed list of English tool names and error codes before touching anything; they become public API. Human: half a day. CC: 20 min.
- **Hours 2 to 3 (core logic).** Ambiguity: what "version" hashes (raw bytes, sha256 hex). Where the lock lives (one `threading.Lock` in `Brain`, taken by every mutating method, never across network I/O). Human: 4 days. CC: 2 hours.
- **Hours 4 to 5 (integration).** Surprises: sync MCP tools run on the event loop while HTTP handlers run in a thread pool; replacing FastMCP's `list_prompts` and `get_prompt` handlers needs the request to authenticate; a proxy in front may trip the MCP host-header check (open question 2). Human: 4 days. CC: 2 hours.
- **Hour 6+ (polish and tests).** The permission matrix test is the one to plan first, not last. Human: 3 days. CC: 1 hour.
- **Feasibility blockers.** None for steps 1 to 5. Step 6 is gated by open question 2.

## Review requirements (Sections 1 to 10)

- **R1 (security, CRITICAL).** Reserved names (`people`, a personal alias, `SKILL.md`, `LEARNINGS.md`, `.oif.toml`) are compared case-insensitively after Unicode NFC normalization, because the development file system is case-insensitive. Tests use `/PEOPLE/<alias>` and `skill.md`.
- **R2 (errors, CRITICAL).** A `.git/index.lock` found at startup is never deleted, because a person may be running git there: the server refuses to start and says how to clear it. Every activity row records whether the change was versioned. `GET /api/health` reports git availability, database availability and the count of unversioned changes since start; the compose file uses it as health check.
- **R3 (errors).** Any `OSError` while writing answers `storage_error`, removes the temporary file and is logged with path and actor. Temporary files left by a crash are removed at startup.
- **R4 (flows).** `list` and `search` take `offset`; results stay capped and flagged.
- **R5 (flows).** Uploads are received into a temporary file outside the lock; the lock covers only compare, rename, commit and revision row.
- **R6 (deploy).** The accounts database carries a schema version (`PRAGMA user_version`); migrations are additive and run at startup.
- **R7 (quality).** One shared helper produces "sanitized name plus short digest" for personal aliases and prompt names.
- **R8 (tests).** One table-driven test runs every tool against every permission situation: no read, read only, write, folder with declared access, another person's folder, reserved folder, missing path.
- **R9 (performance, accepted ceiling).** Skill listing and search walk the readable tree per request; acceptable to a few thousand files and marked in code with that ceiling.
- **R10 (trajectory).** Tool names and error codes are frozen at step 1.
- **R11 (outside review 6).** Every git call has a timeout, closed stdin, and ignores user and system configuration and hooks (no signing, no hooks). A timeout counts as a failed commit.
- **R12 (outside review 7).** Every brain operation, MCP tools included, runs in a worker thread so the event loop stays responsive. `/api/health` never takes the brain lock.
- **R13 (outside review 5 and 8).** Before any change, if the file's current content differs from its latest recorded version (a hand edit, or a crash between rename and commit), the server first commits it and records a baseline. Until revision records exist in phase 2 this is the commit alone. A commit includes only the path being changed, never whatever a person has staged. If a recorded commit no longer exists because someone rewrote history, `restore` answers `no_history`. People may read and hand-edit files in the brain root but must not rewrite its git history.
- **R14 (outside review 9).** Every path segment must match the on-disk name exactly, including case; a mismatch answers `unavailable`. Creating an entry that differs from a sibling only by case answers `unavailable` as well. Behaviour is then the same on macOS and in the Linux container. This subsumes the path half of R1.
- **R15 (outside review 10).** The Spanish-identifier check is a one-time search at the end of step 1, not a permanent test.
- **Estimates.** The CC time estimates in this plan are optimistic for a surface this size; treat them as lower bounds.

## What already exists

- `src/oif/brain.py`: path validation, ancestor-intersected read, nearest-folder write, list, read, write, search, skill discovery, `.oif.toml` editing, git commit per write. Reused and extended.
- `src/oif/accounts.py`: accounts, invites, groups, tokens, login throttle, activity. Reused; gains aliases, tombstones, revisions and schema versioning.
- `src/oif/server.py`: MCP tools, panel JSON API, cookie and bearer authentication. Reused; gains prompts, file routes and health.
- `src/oif/cli.py`: `oif serve`. Gains `put`, `get`, `--public-url`.

## Dream state delta

After this plan the brain is complete for agents on harnesses with a shell: full file operations, guidance written by agents, skills that arrive as commands, proposals of new skills on request, safe undo, and real use across machines. Still missing for the 12-month ideal: the web panel, review before publishing, clients without a shell, automatic (unprompted) skill proposals, and semantic search.

## Error & Rescue registry

| Codepath | What can go wrong | Error | Rescued | Rescue action | Caller sees |
|---|---|---|---|---|---|
| any path argument | invalid, hidden, denied, wrong kind | `OIFError unavailable` | yes | none; uniform answer | "path not available" |
| `write`, `move`, `delete`, `restore`, `PUT /files` | stale or missing `version` | `OIFError conflict` | yes | nothing written; current version returned | conflict with current version |
| `write`, `move` | target exists without `version` | `OIFError already_exists` | yes | nothing written | already exists |
| `edit` | fragment missing or not unique | `OIFError invalid_edit` | yes | nothing written | which of the two |
| any write | disk full, permission error | `OSError` to `storage_error` | yes (R3) | temp file removed, logged | storage error, retry later |
| any write | git missing, lock stale, commit fails | subprocess non-zero | yes (R2) | file kept, `versioned: false`, activity flag, health counter | success with `versioned: false` |
| `PUT /files` | body over limit, client disconnects | size check, `ClientDisconnect` | yes | temp file removed | 413, or nothing |
| `SKILL.md` result | missing front matter | `OIFError invalid_skill` | yes | nothing written | expected format |
| folder `move`, `delete` | subtree rule, not empty, declared access | `folder_not_movable`, `folder_not_empty`, `forbidden` | yes | nothing changed | generic code |
| `history`, `restore` | no git, no visible revision, foreign revision | `OIFError no_history` | yes | none | no history |
| `use_skill` listing | unreadable or invalid `SKILL.md` | skipped | yes | omitted, list continues | shorter list |
| accounts database | locked or corrupt | `sqlite3.Error` | partial | request fails with `storage_error`; health reports database down | storage error |
| `.oif.toml` | malformed | `ValueError` | yes | fails closed | path not available |
| `/api/setup` with `--public-url` | missing or wrong code | `OIFError forbidden` | yes | no account created | forbidden |

## Failure modes registry

| Codepath | Failure mode | Rescued | Test | Caller sees | Logged |
|---|---|---|---|---|---|
| commit after write | git fails repeatedly | yes | yes (R2) | `versioned: false` | activity flag, health |
| compare and write | two writers race | yes | yes (barrier test) | `conflict` | activity |
| reserved folder | case-variant path | yes | yes (R1) | `unavailable` | activity |
| restore | revision under an old restriction | yes | yes | `no_history` | activity |
| upload | interrupted mid-body | yes | yes | nothing stored | server log |
| startup | leftover temp files or git lock | yes | yes | none | startup log |
| setup | unclaimed public server | yes | yes | forbidden without code | activity |
| `use_skill` listing | harness defers tool descriptions (Claude Code does) | yes | spike T1 live, plus unit test | listing arrives in server instructions | no |
| git call | hangs on signing or a hook | yes (R11) | yes | `versioned: false` after timeout | activity flag |
| any write | hand edit or crash left uncommitted content | yes (R13) | yes | none; content preserved as baseline | activity |
| path | case-variant of an existing name | yes (R14) | yes | `unavailable` or `already_exists` | activity |
| proxy | host-header check rejects forwarded requests | unknown | live check before step 6 | connection refused | server log |

No row is unrescued, untested and silent. Two rows are unknowns owned by live checks: the `use_skill` listing (step 0) and the proxy (step 10).

## Diagrams

```
System
  harness (Claude Code, Codex, ...)          person's shell            browser (later: panel)
        | MCP over HTTP, Bearer                | oif put / oif get         | cookie
        v                                      v                           v
  +---------------------------------- server.py (one process) -------------------------------+
  |  MCP tools (use_skill lists skills per identity)    /files (Bearer only)   /api   /health |
  +-------------------------------+----------------------------------+------------------------+
                                  |                                  |
                        brain.py (one lock)                  accounts.py (SQLite, outside root)
              paths, ACL, text/binary, folders          users, aliases, tombstones, groups,
                                  |                      tokens, activity, revisions
                     brain root on disk  <-- git commit per change
                     (.oif.toml per folder)

Write flow, with shadow paths
  input -> authenticate -> canonical path -> ACL -> [lock] compare version -> temp file -> rename -> git commit -> revision row -> activity [unlock] -> answer
   |           |               |             |              |                    |            |            |
  empty      401          unavailable   unavailable      conflict          storage_error  storage_error  versioned:false
                                         write_denied   already_exists                                  (no revision row)

Revision visibility
  revision row {path, commit, author, time, type, read-list snapshot}
  visible to caller  <=>  caller passes snapshot with today's groups  AND  can read path today (or read+write parent if file is missing)
  invalid: restore of a delete or move-out row; revision of another path; restore that would create a folder  -> no_history

Deployment and rollback
  build image -> compose up (proxy with TLS, server not published, two volumes) -> /api/health -> claim with setup code
  broken release -> compose up with previous image tag; migrations are additive, so the old code reads the new database
```

Stale diagram audit: the repository has no other ASCII diagrams in files this plan touches.

## Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific
finding above. Run with Claude Code or Codex; checkbox as you ship.
Effort ratios assume features ~30x and tests ~50x human to CC; the CC figures are lower bounds (see Estimates).
T1 to T11 are phase 1; T12 to T16 are phase 2.

- [x] **T1 (P1, human: ~3h / CC: ~1h)** — server — Spike: use_skill tool with a per-identity description, checked live in Claude Code
  - Surfaced by: Outside review 1 and 2; D18
  - Files: src/oif/server.py
  - Verify: New Claude Code session with a second account lists a skill created by the first and uses it unprompted
  - Done 2026-11-12: one account wrote `/skills/cierre-mensual/SKILL.md`; a fresh headless Claude Code 2.1.322 session for a second account, given a matching task with no mention of skills, called `use_skill` and followed the procedure (activity row `usar_skill`, output carried the skill's marker line). A first run showed the tool description is deferred, so the listing was moved into the per-identity server instructions. Code: `src/oif/server.py`, test in `tests/test_server.py`.
- [x] **T2 (P1, human: ~2d / CC: ~1h)** — repo — Translate the repository to English, freeze tool names and error codes, remove historical docs, add prior-art page, update scope and decisions
  - Surfaced by: E5; D11, D16; R10, R15
  - Files: src/oif/, tests/, examples/, docs/, AGENTS.md, README.md
  - Verify: One-time search for the fixed Spanish identifier list returns nothing; `uv run pytest -q` passes
- [x] **T3 (P1, human: ~3d / CC: ~1.5h)** — brain — One lock, worker-thread execution, versions and conflict errors
  - Surfaced by: Common write rules; R5, R12
  - Files: src/oif/brain.py, src/oif/server.py, tests/test_brain.py
  - Verify: Barrier test with simultaneous writers: second gets `conflict`
- [x] **T4 (P1, human: ~2d / CC: ~1h)** — brain — Hardened git: init, timeout, no user config or hooks, path-limited commit, refuse foreign index lock, baseline on divergent content
  - Surfaced by: R2, R11, R13
  - Files: src/oif/brain.py, src/oif/cli.py, tests/test_brain.py
  - Verify: Tests: commit with a hanging hook times out; staged foreign file is not committed; divergent content is committed before change
- [x] **T5 (P1, human: ~2d / CC: ~1h)** — server — Health endpoint, versioned flag in activity, storage_error mapping, startup temp cleanup, schema versioning
  - Surfaced by: R2, R3, R6
  - Files: src/oif/server.py, src/oif/accounts.py, tests/test_server.py
  - Verify: `GET /api/health` reports git and database; simulated `OSError` answers `storage_error` and leaves no temp file
- [x] **T6 (P1, human: ~4d / CC: ~2h)** — brain — Text operations: edit, append, file move and delete, create_folder, describe_folder, relative start_here, exact-case paths, pagination, text limits
  - Surfaced by: Layer 1; R4, R14
  - Files: src/oif/brain.py, src/oif/server.py, examples/brain/, tests/test_brain.py
  - Verify: Unit tests per operation including denial, case-variant path and offset
- [x] **T7 (P1, human: ~2d / CC: ~1h)** — accounts — Personal folders: unique alias, reserved /people, owner rule, alias tombstones
  - Surfaced by: Layer 1 personal folder; R1, R7
  - Files: src/oif/accounts.py, src/oif/brain.py, src/oif/server.py, tests/
  - Verify: Tests: `/PEOPLE/<alias>` denied, re-invited email gets a new alias, panel cannot edit access under `/people`
- [x] **T8 (P1, human: ~2d / CC: ~1h)** — server — Skills: use_skill with per-identity listing, SKILL.md validation, trust model in instructions, remove list_skills
  - Surfaced by: D18; skill trust model
  - Files: src/oif/server.py, src/oif/brain.py, tests/test_server.py
  - Verify: Tool listing differs per identity; invalid `SKILL.md` skipped; write of invalid `SKILL.md` answers `invalid_skill`
- [x] **T9 (P1, human: ~1d / CC: ~30min)** — server — Learnings: stamped append, list_learnings, built-in propose-skills skill
  - Surfaced by: E2; D8
  - Files: src/oif/brain.py, src/oif/server.py, tests/
  - Verify: A learning containing a delimiter-looking line returns as one entry; skill text asserts untrusted, cite, confirm
- [x] **T10 (P1, human: ~2d / CC: ~40min)** — tests — Permission matrix test: every tool against every permission situation
  - Surfaced by: R8
  - Files: tests/test_matrix.py
  - Verify: `uv run pytest -q tests/test_matrix.py`
- [ ] **T11 (P1, human: ~2d / CC: ~1h)** — examples — Fuller example case, OIF's own brain in brain/, live check of both scenes
  - Surfaced by: Premise 6; success criteria 1 and 2
  - Files: examples/brain/, .gitignore
  - Verify: Activity log shows only list and read for the day-one question; answer contains the three fixed facts
- [ ] **T12 (P2, human: ~4d / CC: ~2h)** — server — Binary files: byte storage, /files routes with ETag and If-Match, oif put and oif get
  - Surfaced by: Layer 1 binary files; phase 2
  - Files: src/oif/brain.py, src/oif/server.py, src/oif/cli.py, tests/
  - Verify: Upload to a restricted folder downloads only with an authorized token; cookie rejected
- [ ] **T13 (P2, human: ~2d / CC: ~1h)** — brain — Folder move and empty-folder delete
  - Surfaced by: E3; D12, D15
  - Files: src/oif/brain.py, src/oif/server.py, tests/
  - Verify: Move with one hidden entry or declared access changes nothing; non-empty delete changes nothing
- [ ] **T14 (P2, human: ~5d / CC: ~3h)** — accounts — Revision records with read-list snapshot, history, restore, group-name and email reuse guards
  - Surfaced by: E7; D13; SAFETY-FIXES
  - Files: src/oif/accounts.py, src/oif/brain.py, src/oif/server.py, tests/
  - Verify: Path reuse and widened read expose no earlier revision; deleted file restores with matching content
- [ ] **T15 (P2, human: ~4d / CC: ~2h)** — deploy — Proxy live check, then --public-url, setup code, throttle key, Dockerfile and compose
  - Surfaced by: E6; D9; open question 2
  - Files: src/oif/cli.py, src/oif/server.py, src/oif/accounts.py, Dockerfile, compose.yaml, tests/
  - Verify: Compose with locally trusted certificate: two accounts over HTTPS; setup without code creates no account
- [ ] **T16 (P3, human: ~1d / CC: ~30min)** — release — CI and publication of package and image, after name, license, remote repository and registry are decided
  - Surfaced by: Distribution; pending author decisions
  - Files: to be determined
  - Verify: Tagged release publishes package and image

_No new tasks from Section 7 (performance): the tree-walk ceiling is accepted and marked in code as part of T8._
_No new tasks from Section 10 (trajectory) beyond freezing names in T2._

## Test map

| New thing | Test type | Happy path | Failure path | Edge case |
|---|---|---|---|---|
| Version and lock | unit, integration | write with current version | stale version gives `conflict` | simultaneous writers over MCP and HTTP |
| Text operations | unit | each operation succeeds with write | each denied without write | fragment not unique, empty content, offset past end |
| Folder guidance | unit | agent sets description and `start_here` | cannot touch `read` or `write` | relative path with `..` rejected |
| Personal folder | unit, integration | owner reads and writes | anyone else gets `unavailable` | case-variant path, re-invited email |
| `use_skill` | integration | listed and returned per identity | unreadable skill absent | invalid `SKILL.md`, 256 cap |
| Learnings | unit | stamped entry listed | unreadable folder excluded | delimiter-looking line |
| Git | unit | commit recorded | hook or signing hangs, times out | foreign staged file, hand edit before change |
| Health | integration | reports healthy | git missing reported | never blocked by the brain lock |
| Phase 2 additions | unit, integration | put and get, folder move, restore | each denial listed in success criteria | path reuse, widened read, interrupted upload |

The test to trust at 2am is the permission matrix (T10). The hostile test is the case-variant and Unicode-variant path set. The chaos test kills the server between rename and commit and checks the next write preserves the content. Flakiness risk: the race test, controlled with a barrier, never with sleeps.

## Scope expansion decisions

Full record in the CEO plan at `~/.gstack/projects/oif/ceo-plans/2026-11-12-core-permissioned-memory.md`.

- Accepted: E2 brain proposes skills, E3 folder move and empty-folder delete, E5 English everywhere, E6 cross-machine use, E7 history and restore.
- Deferred to TODOS.md: E1 review before publishing, E4 one-time download links.
- Skipped: none.

## Reality rows

```
REALITY: premise-table finding 5 claims, unverified=1 (harness re-reads per-identity tool descriptions each session: no live check yet; owned by T1) src/oif/brain.py:173
REALITY: already-done finding skill listing and basic write exist; nothing else in the plan is built (single commit 3776e3e, no remote) src/oif/brain.py:254
REALITY: surface-check pass `oif serve` and `/api/folder` exist; `oif put`, `oif get`, `/files`, `/api/health` are new surface src/oif/cli.py:28
REALITY: binding-decisions finding decision 0008 excludes a review-and-approval engine; E1 stays deferred, not reintroduced docs/scope.md:32
REALITY: numbers pass 831 lines [measured: wc -l src/oif/*.py]; 11 tests [measured: uv run pytest -q]; limits 64 KB, 1 MB, 25 MB [estimated] src/oif/brain.py:28
REALITY: deferred-asks pass no linked issue docs/designs/core-permissioned-memory.md:1
REALITY: pr-count pass no ship policy and no remote; two phases by author decision D19 docs/designs/core-permissioned-memory.md:135
PLAN_REALITY: phase=ceo rows=7/7 missing=none unverified=1 verdict=complete
```

## Completion Summary

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | 831 lines, 11 tests, one commit, no remote; |
  |                      | last-write-wins and no agent folder guidance|
  | Step 0               | Approach B, design approved, 7 proposals,   |
  |                      | 5 accepted, 2 deferred, two phases          |
  | Section 1  (Arch)    | 2 issues found                              |
  | Section 2  (Errors)  | 14 error paths mapped, 2 GAPS (repaired)    |
  | Section 3  (Security)| 3 issues found, 1 High severity (repaired)  |
  | Section 4  (Data/UX) | 9 edge cases mapped, 2 unhandled (repaired) |
  | Section 5  (Quality) | 1 issue found                               |
  | Section 6  (Tests)   | Diagram produced, 1 gap (matrix, now T10)   |
  | Section 7  (Perf)    | 1 issue found (accepted ceiling)            |
  | Section 8  (Observ)  | 2 gaps found (repaired)                     |
  | Section 9  (Deploy)  | 2 risks flagged                             |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 3           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (12 items)                          |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 14 rows, 0 CRITICAL GAPS                    |
  | Failure modes        | 12 total, 0 CRITICAL GAPS                   |
  | TODOS.md updates     | 2 items proposed, 2 written                 |
  | Scope proposals      | 7 proposed, 5 accepted (EXP + SEL)          |
  | CEO plan             | written                                     |
  | Outside voice        | codex not installed; native fallback        |
  |                      | completed, 10 findings, 10 resolved         |
  | Lake Score           | 0/1 recommendations chose complete option   |
  | Diagrams produced    | 4 (system, write flow, revision visibility, |
  |                      | deployment and rollback)                    |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 1 unverified       |
  +====================================================================+
```

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR | 7 proposals, 5 accepted, 2 deferred |
| Outside Review | native fallback after `/plan-ceo-review` (Codex not installed) | Independent 2nd opinion | 1 | unavailable (external); native completed | 10 findings; 10 resolved; 0 unresolved (native, not external coverage) |
| Eng Review | `/autoplan` | Architecture & tests (required) | 0 | not run | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | not run | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | not run | — |

- **OUTSIDE COVERAGE:** provider codex, phase plan-review, unavailable (not installed); no completed external review. A native read-only fallback completed inside the five-minute bound with 10 findings, all dispositioned: 2 by author decision (D18, D19), 6 as requirements R11 to R15 and the changed R2, 2 folded into the phasing.
- **VERDICT:** CEO CLEARED. Eng review required before implementation.

NO UNRESOLVED DECISIONS
