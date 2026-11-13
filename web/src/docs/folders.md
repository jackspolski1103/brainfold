# Folders and guidance

The brain is a tree of folders. What makes it usable by agents is that every folder explains itself.

## Folder guidance

Each folder can carry two things an agent reads before anything else:

- A **description**: one line saying what the folder holds.
- A **start here** list: the files or subfolders to read first.

An agent that connects for the first time calls `list` on the root, reads the description and the start here list, and follows them down. No index to maintain, no search needed to get oriented.

Agents write this guidance themselves: `create_folder` asks for a description, and `describe_folder` updates it. Administrators can also edit the description from **Access**.

## Where it is stored

Guidance and access rules live in a `.brainfold.toml` file inside the folder:

```toml
description = "Process and learnings of the costs team."
start_here = ["process.md"]     # relative to the folder
read = ["@costs"]
write = ["@costs"]
```

Agents never see this file, or any file starting with a dot. Symbolic links are never followed.

## Personal folders

Every account gets a folder under `/people/`, created by the server. Only its owner can read or write it. No access rule widens or narrows that, and administrators cannot open it either. It is the place for an agent's notes that are not ready to share.

The folder name is an alias derived from the email; it is never reused, even after the account is removed.

## Limits

| What | Limit |
| --- | --- |
| Entries returned by one `list` call | 256, then continue with `offset` |
| Text returned by one `read` call | 64 KB, then continue from `next_offset` |
| Text file written or searched over MCP | 1 MB |
| File uploaded with `brainfold put` | 25 MB |
| Folder depth | 32 levels |
