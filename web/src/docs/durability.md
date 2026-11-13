# Durability and recovery

The brain should never be lost. Three layers protect it.

## 1. Version history

Every change is a git commit inside the brain folder. A deleted or overwritten file can be [restored](#/docs/history).

## 2. A persistent volume

The brain folder and the accounts database must live on a volume that survives redeploys. See [Run it for your team](#/docs/deploy).

## 3. An off-site mirror

Set `BRAINFOLD_MIRROR` to a git remote, typically a private repository, and give the server a deploy key with write access in `BRAINFOLD_MIRROR_KEY`. After every change the server pushes the history there in the background. It never force-pushes.

```bash
BRAINFOLD_MIRROR=git@github.com:your-org/your-brain.git
BRAINFOLD_MIRROR_KEY=<private key, PEM or base64>
```

The **Overview** page and `/api/health` show the mirror state: `ok`, `pending`, `failing` or `off`.

### Restoring from the mirror

Start the server with an **empty** brain folder and the mirror configured: it clones the mirror before serving. Nothing is restored over a folder that already has content.

## What the mirror does not cover

The mirror holds the brain: files, guidance and access rules. It does **not** hold the accounts database: members, groups, tokens, activity and revision records. Back up the volume itself to keep those. Without the database you keep all content, and recreate accounts and groups.

## Recovering access

If an administrator forgets their password and no other administrator can reset it, run this on the server:

```bash
brainfold reset-password admin@example.com
```

It prints a one-time link to choose a new password.
