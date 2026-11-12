# 0007 Harness-agnostic shared brain

Date: 2026-11-12. Status: accepted by the author. Replaces the own harness as first product.

## The author's choice

"Harness-agnostic. I even want to be able to connect Claude Code."

The product is the shared brain: folders and files with permissions, exposed over MCP so Claude Code, Codex or any other harness can use them. The project does not compete with those harnesses.

## Alternative rejected

Keeping the own harness as the product and adding the server: twice the surface to maintain, and it would never catch up with existing harnesses.

## Consequences

Real folders and files on disk. Each folder may carry a `.brainfold.toml` with `description`, `start_here`, `read` and `write`. Read is denied unless granted and narrows down the tree. Write follows the nearest folder that declares it and is denied by default. Metadata files, `.git` and symlinks are never visible to an agent. Skills are folders with a `SKILL.md` inside the same tree.
