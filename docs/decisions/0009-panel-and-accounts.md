# 0009 Web panel and own accounts

Date: 2026-11-12. Status: accepted by the author. The panel UI is not built yet.

## The author's choice

"I want to do it very well, with the web panel too, in the style of Infisical or Langfuse."

1. **Panel:** a React application (Vite, shadcn/ui) over an API of the same Python server, in one container.
2. **Sign-in:** own email and password. The first account creates the organization and invites the rest; each person creates the token their harness uses.
3. **First version of the panel:** access per folder, members and tokens, a read-only file explorer, and activity.

## Built so far

`src/oif/accounts.py` (accounts, invites, groups, tokens, activity in SQLite; scrypt passwords; tokens stored as digests) and the `/api` routes in `src/oif/server.py`.

## Adopted criteria

- An administrator sees the folder structure and its access lists, but does not read content they were not granted.
- A person is identified in access lists by their email.
