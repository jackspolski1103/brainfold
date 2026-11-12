# 0000 Superseded decisions (summary)

Date of summary: 2026-11-12. The original records were written in Spanish and remain in git history.

The project started on 2026-11-11 as an agent harness used from the terminal. These decisions shaped that first cut and were later replaced:

- **CLI, Python and documentation first.** Python stays. The own harness was removed by 0007.
- **Natural conversation as the main experience.** Still true, but it now happens inside each person's own harness.
- **Agents consume only approved, published shared knowledge.** Replaced by 0008: write permission on a folder is the authority to publish there.
- **Collaboration as the core, no standalone personal mode.** Still true: one server per team.
- **First cut: two agents sharing one versioned capability over MCP, with OpenAI as the first model.** Removed with the harness.
- **Memory as a navigable repository of folders and files with permissions.** This is the idea the product is now built on.
