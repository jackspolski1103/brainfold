# OIF: a shared brain for agents

A personal, independent project with open source intent. **OIF is a working name.** There is no remote repository or license yet.

OIF is an MCP server that turns a folder into a team's shared brain: files with permissions that any harness (Claude Code, Codex or another) reads and writes. Full scope, including what it deliberately does not do, is in [docs/scope.md](docs/scope.md).

## Status

Development implementation. What works today: the MCP server over a folder on disk, read and write permissions per folder, file operations with conflict detection, files of any type through `oif put` and `oif get`, history and restore, folder guidance written by agents, personal folders, text search, skills delivered to each agent through `use_skill`, a learnings log, email and password accounts, personal tokens, groups, an activity log, and the JSON API for the future panel. **The web interface does not exist yet.** The server listens on loopback only. Example data is synthetic. The plan in progress is [docs/designs/core-permissioned-memory.md](docs/designs/core-permissioned-memory.md).

## Try it

```bash
uv sync
cp -R examples/brain /tmp/oif-brain            # the server turns the brain folder into a git repository
uv run oif serve --root /tmp/oif-brain        # accounts and activity go to ./oif.db

# In another terminal: create the administrator, a group and a harness token.
J='Content-Type: application/json'; U=http://127.0.0.1:8020
curl -c cookies.txt -H "$J" -d '{"email":"you@example.com","password":"a-long-password"}' $U/api/setup
curl -b cookies.txt -X PUT -H "$J" -d '{"members":["you@example.com"]}' $U/api/groups/costs
curl -b cookies.txt -H "$J" -d '{"name":"claude code"}' $U/api/tokens   # shows the token once

claude mcp add --transport http oif $U/mcp --header "Authorization: Bearer <token>"
```

MCP tools: `list`, `read`, `write`, `edit`, `append`, `move`, `delete`, `create_folder`, `describe_folder`, `search`, `history`, `restore`, `list_learnings`, `use_skill`.

Files of any type (a manual, a spreadsheet) go through the command line, which reads `OIF_URL` and `OIF_TOKEN` from the environment or from `~/.config/oif/config.toml` (mode 0600):

```bash
oif put salaries.xlsx /hr/salaries.xlsx
oif get /hr/salaries.xlsx ./salaries.xlsx
```

## Brain format

Each folder may carry a `.oif.toml`:

```toml
description = "Process and learnings of the costs team."
start_here = ["process.md"]      # relative to the folder
read = ["@costs"]     # emails, @group or "*"
write = ["@costs"]
```

- **Read** is denied unless some folder on the path grants it; every folder that declares `read` narrows what hangs below it.
- **Write** is decided by the nearest folder that declares `write`; with no declaration it is denied.
- Groups and their members are managed in the accounts database through the API.
- An administrator sees the structure and access lists of every folder, but does not read content they were not granted.
- Files starting with a dot and symlinks are never visible to an agent.
- Every change is committed to a git repository in the brain root under the author's name. Replacing, moving or deleting a file needs the `version` returned by `read`, so two agents never overwrite each other silently.
- Each account gets a personal folder under `/people/` that only its owner can read or write.
- A skill is a folder with a `SKILL.md`. See `examples/brain/`.

## Verify

```bash
uv run pytest -q
uv run ruff check src tests
```

## Documentation

- [Scope](docs/scope.md)
- [Decision log](docs/decisions/README.md)
- [Prior art](docs/prior-art.md)
- [Core plan](docs/designs/core-permissioned-memory.md) and [TODOS](TODOS.md)
- [How to collaborate](AGENTS.md)
