# MCP tools

What every connected agent can call. Paths are absolute inside the brain, for example `/projects/costs/process.md`.

## Finding the way

| Tool | What it does |
| --- | --- |
| `list` | A folder's description, where to start, and the entries you can see: folders with their description, files with their size and description. The root listing also names your personal folder. |
| `read` | A text file and its `version`. Long files come in parts. |
| `search` | Text search across the files you can read under a folder. |

## Writing

| Tool | What it does |
| --- | --- |
| `write` | Create a file, or replace one by passing the `version` you last read. Folders created on the way are named in `new_folders`, to be described. |
| `edit` | Replace one exact fragment of a text file. The fragment must appear exactly once. |
| `append` | Add to the end of a file, creating it if missing. Entries in a `LEARNINGS.md` are stamped with date and author. |
| `move` | Move or rename a file or a whole folder. Needs write on both sides. |
| `delete` | Delete a file, or an empty folder. |
| `create_folder` | Create a folder with a description and a start here list. |
| `describe_folder` | Update a folder's description and start here list. Access does not change. |
| `describe_file` | Say in one line what a file is. It shows next to the file in `list`. |

## History

| Tool | What it does |
| --- | --- |
| `history` | Who changed a file and when, including deleted files. |
| `restore` | Bring a file back to one of its revisions. |

## Team knowledge

| Tool | What it does |
| --- | --- |
| `use_skill` | Load a shared procedure by name and follow it. |
| `list_learnings` | The newest notes from the `LEARNINGS.md` files you can read. |

## Errors

Every error has a stable code and a message written for the agent.

| Code | Meaning |
| --- | --- |
| `unavailable` | The path does not exist or you cannot read it. The two are indistinguishable. |
| `write_denied` | You can read here but not write. The message names the administrators who can grant it. |
| `conflict` | The file changed since the version you read. Read again. |
| `already_exists` | Something is already at that path. |
| `folder_not_empty` | Only empty folders can be deleted. |
| `folder_not_movable` | The folder has access set by an administrator, or content you cannot see. |
| `invalid_edit` | The fragment to replace was not found exactly once. |
| `file_too_large` | Over the size limit for this channel. |
| `no_history` | There is no revision you are allowed to restore. |
| `unauthenticated` | The token is missing, wrong or revoked. |
