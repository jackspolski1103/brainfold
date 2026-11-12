# Project instructions

## Confirmed context

- This is the author's personal project, independent of their job. Never use work data, accounts, repositories, services or credentials.
- The author's personal GitHub account is `jackspolski1103`. Any creation or publication must use that account; verify the authenticated identity before writing to GitHub.
- Current scope is in `docs/scope.md`; the plan in progress is `docs/designs/core-permissioned-memory.md` (decision `0010`). Before proposing or building something, check it is not in the scope's "what it is not" table.
- The product is a harness-agnostic shared brain: folders and files with permissions exposed over MCP to Claude Code, Codex or others. Do not build or propose an own harness.
- Collaboration is the core: one server per team, each person connecting their own harness. The author rejected a local mode per person; do not propose it again.
- Python is the confirmed language. The web panel follows the style of Infisical or Langfuse: React over the Python server's API, own email and password accounts (decision `0009`). Do not build a web content editor or a review and approval engine.
- **Everything in the repository is in English**: code, tool names, error codes and messages, docs, examples and this file. Conversation with the author is in Spanish.
- The author wants to take part in product and architecture decisions.

## How to collaborate

- Work in small, reviewable increments, one commit per finished task on the working branch.
- When a task list is already agreed, continue through it without asking between tasks.
- Before committing to infrastructure, an identity provider, scope changes, a license or an external publication, present one concrete recommendation with its main alternative and ask. Do not reopen confirmed choices without a concrete reason.
- Ask few decisions at a time, and keep doing independent work while waiting.
- Record confirmed decisions in `docs/decisions/`; tell proposals from agreements.
- Never present a demo, a simulated adapter or an interface as working production functionality.
- Explain changes, verification and the next decision to the author in Spanish.

## Credentials and permissions

- Never ask the author to paste passwords or tokens in the chat.
- Never commit secrets, real environment files or user data.
- Keep identity, authorization, tool connections and model credentials separate.
- Secrets never go into prompts or model results.
- Private content and anything derived from it keeps its scope unless explicitly promoted.

## Implementation and verification

- Test denials, isolation and revocation whenever such behavior is implemented.
- Keep tests proportional to the change.
- Avoid spending, deployments and external services until they are part of the chosen increment.
