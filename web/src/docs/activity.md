# Activity

**Activity** records what people and their agents did, with the person, the action, the path and whether it was allowed.

## What is recorded

- Every brain operation an agent performs: `list`, `read`, `write`, `edit`, `append`, `move`, `delete`, `restore`, `search`, `use_skill` and the rest.
- File uploads and downloads.
- Sign-ins, including failed ones.
- Administrative changes: invitations, removed members, group edits, access edits, token creation and revocation, password changes and resets.

## Reading the result

| Result | Meaning |
| --- | --- |
| Allowed | The operation ran. |
| Denied | It was refused: no permission, a conflict, or an invalid request. |
| Not in history | The change was saved to disk but could not be committed to the version history. Check the server. |

Filter by person, action or path, or show only what was denied to spot an agent probing where it should not.
