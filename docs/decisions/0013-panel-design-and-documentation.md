# 0013 Panel design and documentation site

Date: 2026-11-13. Status: accepted by the author, who reviewed the first panel on the test deployment and asked for a rebuild modelled on Infisical, with sections for the whole brain and its access, users, harness credentials, and a documentation site.

- **Look:** modelled on Infisical's panel as browsed on 2026-11-13: dark by default with a light theme, a top bar, a full-height sidebar with grouped sections, bordered cards, and tinted buttons. Colors are tokens in `web/src/index.css`. IBM Plex Sans and IBM Plex Mono are bundled with the panel, so nothing loads from another site and the content policy stays `default-src 'self'`.
- **Sections:** Overview, Brain (folder tree, search, rendered Markdown), Skills, Connect a harness (tokens and setup for Claude Code, Codex, Cursor, other MCP clients and the file command), Access (every folder with its rules and an editor), Members (users and groups), Activity, and Account.
- **Documentation:** pages are Markdown in `web/src/docs/`, built into the panel and served at `#/docs` without signing in. A separate documentation host was the alternative; one build and one address is simpler while the project has one server.
- **Server:** two read-only routes were added for the panel, `/api/search` and `/api/skills`. Both answer with the permissions of the signed-in person.
- **Unchanged:** the panel still does not edit file content (scope, decision 0008). It did not transfer files either until decision [0014](0014-files-in-the-panel.md).
- **Markdown is untrusted:** brain files are rendered with raw HTML shown as text, images never loaded, and links limited to web, mail and brain addresses.
- **Not verified:** the Codex and Cursor setup shown in the panel follows their documentation and has not been run against a live server.
