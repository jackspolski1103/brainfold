# 0010 Core plan

Date: 2026-11-12. Status: accepted by the author after a design session and a plan review.

The full plan, with its decision ledger, is [docs/designs/core-permissioned-memory.md](../designs/core-permissioned-memory.md).

## What was decided

- **What defines success:** a skill written by one person's agent is used by a teammate's agent without anyone telling it, and a newcomer's agent finds its way using folder guidance alone.
- **Skill delivery:** one `use_skill` tool, with the caller's readable skills listed in the server instructions and in the tool description. MCP prompts are not used. Verified live with Claude Code on 2026-11-12.
- **The agent is the main author:** it creates folders with guidance, edits, appends, moves and deletes files, moves folders and deletes empty ones. It never changes who can read or write.
- **Accepted additions:** the brain proposes skills on request, history and restore, use across machines, binary files through `oif put` and `oif get`.
- **English everywhere** in the repository. Conversation with the author stays in Spanish.
- **Two phases.** Phase 1 makes the two scenes work. Phase 2 adds binary files, folder moves, history and restore, cross-machine use and publication.
- **Deferred:** review before publishing, and one-time download links. See [TODOS.md](../../TODOS.md).
