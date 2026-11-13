# What is Brainfold?

Brainfold is a shared brain for a team's AI agents: folders and files with permissions, served over the Model Context Protocol (MCP). Each person connects their own harness (Claude Code, Codex, Cursor or another MCP client) and their agent reads and writes the same brain, with exactly the access that person has.

> Brainfold is not an agent and does not run models. It is the memory your agents share.

## Why a shared brain

Today what an agent learns stays with one person and one harness. Brainfold changes three things:

- **Knowledge spreads on its own.** An agent writes a skill once; every teammate's agent sees it listed and uses it in its next session.
- **A newcomer finds the way.** Every folder carries a description and a "start here" list, so an agent that has never seen the brain reaches what matters by following the folders.
- **Access is decided per folder.** Salaries live next to public conventions without leaking: a folder is readable only by the people and groups it grants.

## How it fits together

| Piece | What it is |
| --- | --- |
| The brain | A folder on the server's disk. Every change is a commit in its own git history. |
| The MCP server | 14 tools any harness calls: list, read, write, search, skills and more. |
| Accounts | Email and password accounts, groups, and personal tokens for each harness. |
| This panel | Where people browse the brain, grant access, invite members and get credentials. |

## Where to go next

- [Quickstart](#/docs/quickstart): from an empty server to an agent using the brain.
- [Connect a harness](#/docs/connect): commands for Claude Code, Codex, Cursor and others.
- [Permissions](#/docs/permissions): how read and write are decided.
- [Run it for your team](#/docs/deploy): Docker, a hosting platform, and what keeps the brain safe.
