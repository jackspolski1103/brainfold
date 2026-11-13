# Connect a harness

A harness connects with a **personal token**. The token carries your identity: the agent reads and writes exactly what you can, and its actions appear under your email in **Activity**.

Create tokens in **Connect a harness**. A token is shown once; only a digest is stored. Use one token per harness and machine so you can revoke one without touching the rest.

## Claude Code

```bash
claude mcp add --transport http --scope user brainfold https://your-server/mcp \
  --header "Authorization: Bearer <your-token>"
```

Run `/mcp` inside Claude Code to check that `brainfold` is connected. This is the harness Brainfold is tested with.

## Codex

Keep the token in an environment variable and point Codex at the server in `~/.codex/config.toml`:

```toml
[mcp_servers.brainfold]
url = "https://your-server/mcp"
bearer_token_env_var = "BRAINFOLD_TOKEN"
```

## Cursor

Add the server to `~/.cursor/mcp.json` and restart Cursor:

```json
{
  "mcpServers": {
    "brainfold": {
      "url": "https://your-server/mcp",
      "headers": { "Authorization": "Bearer <your-token>" }
    }
  }
}
```

## Any other MCP client

Brainfold speaks MCP over streamable HTTP at `/mcp` and expects the header `Authorization: Bearer <your-token>`. Any client that supports that transport works.

> The Codex and Cursor settings follow those products' documentation; they have not been checked against a live Brainfold server yet.

## What the token cannot do

A harness token works only for the brain: the MCP tools and file transfer. It cannot sign in to this panel, invite people or change access. The panel uses a separate session that a harness never sees.

## Revoking

Revoke a token in **Connect a harness** and the harness loses access at once. Removing a member revokes all of their tokens.
