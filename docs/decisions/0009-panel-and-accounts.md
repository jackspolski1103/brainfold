# 0009 Web panel and own accounts

Date: 2026-11-12. Status: accepted by the author. A first version of the panel is built.

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

## First version of the panel (2026-11-12)

`web/` holds a React and TypeScript application built with Vite and Tailwind. `npm run build` writes it to `src/oif/panel/`, which the Python server serves at `/`; the container image builds it in its own stage.

- **Brain:** browse folders with their description and "start here", read text files, and for administrators see and edit each folder's description, read list and write list.
- **Members:** invite by email (the invitation link is shown once), remove people, create and edit groups.
- **Tokens:** create and revoke personal tokens, with the command that connects Claude Code.
- **Activity:** the latest events with a filter.

Differences from what was decided: the interface components are written by hand in the visual style of shadcn/ui; the shadcn/ui library itself is not installed. The panel never downloads files: binary files show the `oif get` command, because the file routes refuse the panel's cookie.

Checked in a headless browser at desktop and phone width in light mode. Not checked: dark mode, the setup and accept-invitation screens, and the view of a member who is not an administrator.
