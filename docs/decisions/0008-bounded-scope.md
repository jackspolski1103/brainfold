# 0008 Bounded scope

Date: 2026-11-12. Status: accepted by the author.

## The author's choice

"Let's define the scope well and build something composable, with judgment. I don't want something that does everything."

1. The exclusions in [scope.md](../scope.md) are accepted. In particular there is no draft, review and approval engine: write permission on a folder is the authority to publish there, and history is git.
2. The own harness was deleted: runtime, model adapter, conversational CLI, HTTP service and capability registry. They remain in git history.
3. Deployment is one server per team, run by the team. A local mode per person synced through git was rejected because it voids read permissions.

A web panel limited to administration was requested in the same exchange; see 0009.
