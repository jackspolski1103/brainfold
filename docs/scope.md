# Scope

Confirmed by the author on 2026-11-12. See decisions [0008](decisions/0008-bounded-scope.md), [0009](decisions/0009-panel-and-accounts.md) and [0010](decisions/0010-core-plan.md).

**OIF is an MCP server that turns a folder into a team's shared brain: files with permissions that any harness reads and writes.**

## What it is

1. **A format.** A folder with one `.oif.toml` per folder: `description`, `start_here`, `read`, `write`. Plain files: they open, edit and version without the server.
2. **An MCP server** with file tools for agents: list, read, write, search, and (phase 1) edit, append, move, delete and folder guidance.
3. **Permissions per folder**, with groups, denied by default.
4. **Skills inside the tree.** A skill is a folder with a `SKILL.md`. The server lists to each agent the skills it can read and serves them through `use_skill`. Running the procedure is the harness's job.
5. **Own accounts.** Email and password; the first account administers and invites the rest; each person creates the token their harness uses. One organization per server.
6. **A web panel** in the style of Infisical or Langfuse (API built, UI not built).

A team runs its own server and each person connects their harness with their token.

## What it is not

| Out of scope | Who solves it |
|---|---|
| Harness, runtime, model adapters | Claude Code, Codex or another |
| Connectors to mail, databases and so on | The MCP servers each harness already has |
| Running skills | The harness |
| Extracting memory automatically from conversations | The agent decides what to write |
| Embeddings, RAG, semantic search | Text search and folder guidance |
| Draft, review and approval engine | Write permission publishes; deferred as a TODO |
| Web content editor, web chat | A text editor, git and the harness |
| Reading file formats (PDF, spreadsheets) | The harness, after fetching the file |
| Multi-tenant hosting | Each team runs its own |
| Local mode per person synced through git | Rejected: it voids read permissions |

## What makes it composable

- The brain is a folder: it combines with git, grep, an editor or a backup.
- The server is one more MCP server next to the ones a team already has.
- Folders and their permissions live in files; accounts, groups, tokens and activity live in one SQLite file outside the brain.

## Criteria

- Deny by default; what is denied looks the same as what does not exist.
- Everything is a file; history is git.
- Each folder's metadata guides the agent to what matters.
- Before adding something, check it is not in the "what it is not" table.
