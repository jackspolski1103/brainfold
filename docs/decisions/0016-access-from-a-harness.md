# 0016 Access and groups managed from a harness

Date: 2026-11-18. Status: accepted by the author ("de la tabla 1 debería poder hacerse desde el harness"; options "Admin con token habilitado" and "Acceso + grupos").

- **Change:** three MCP tools, `get_access`, `set_access` and `set_group`, let an administrator's agent see and set folder `read` and `write` lists and edit groups. They work only with a harness token that an administrator created with *Can manage access and groups* in **Connect a harness**. Every other token gets `forbidden`.
- **Replaces:** the rule in [0010](0010-core-plan.md) (D17) that an agent can never change `read` or `write`. It still holds for every token without the flag, which is every member's token and an administrator's default one.
- **Why:** people do their work through their harness; opening the panel to grant a folder is friction (author: "ya la gente hace el 100% de las cosas con claude, no podemos agregar dificultad").
- **Why a flag on the token:** an agent reads text written by teammates (skills, learnings, folder descriptions). A token that cannot manage cannot be talked into widening access. The cost is one tick when creating the token; the `forbidden` message tells the agent where it is.
- **Alternative not taken:** any administrator token manages. One line to switch (`manage` in `Accounts.authenticate`) if the tick proves to be friction.
- **Unchanged:** an administrator still does not read content they were not granted, personal folders stay closed, `move` and `delete` still refuse folders with declared access, and every change is recorded in activity as `edit_access` or `edit_group`. Inviting and removing members, password resets and activity stay in the panel: their one-time links are secrets and must not pass through a model.
