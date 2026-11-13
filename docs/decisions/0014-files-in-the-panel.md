# 0014 Files in the panel

Date: 2026-11-13. Status: accepted by the author ("dale, descarga y subida"), after asking why the panel could not download files.

- **Change:** a signed-in person downloads any file they can read and uploads files to folders where they can write, from the Brain section. This replaces the earlier rule that the panel never transfers files (security review of 2026-11-12, restated in decision 0013).
- **Why it is safe:** the earlier rule avoided a stored file running in the panel's origin with a session. The same risk is covered by how files are sent: always as an attachment with a generic type, `nosniff` and a sandbox policy, so the browser saves them and never renders them.
- **Route:** `/api/files?path=` takes only the session cookie. `/files/<path>` still takes only a harness token. A harness token cannot use the panel route and a session cannot use the harness route.
- **Uploads from another site:** refused twice. The session cookie is SameSite=Strict, and an upload must declare a binary body, which a page on another site cannot send without a preflight the server never grants.
- **Unchanged:** permissions, the 25 MB limit, versions for replacing, history, and the activity log (`upload`, `download`). The panel still does not edit file content.
