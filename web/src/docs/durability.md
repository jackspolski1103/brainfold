# Durability and recovery

The brain should never be lost. Three layers protect it.

## 1. Version history

Every change is a git commit inside the brain folder. A deleted or overwritten file can be [restored](#/docs/history).

## 2. A persistent volume

The brain folder and the accounts database must live on a volume that survives redeploys. See [Run it for your team](#/docs/deploy).

## 3. An off-site mirror

The server can push every change to a git repository somewhere else. Any git server reachable over SSH works: GitHub, GitLab, Bitbucket or your own.

### Set it up

1. Create a **private, empty** repository, for example `your-org/brain-backup`. It must start empty: the server never force-pushes over existing history.
2. Generate a key used only for this, with no passphrase:

```bash
ssh-keygen -t ed25519 -N "" -f brainfold-mirror -C "brainfold mirror"
```

3. Add the public half, `brainfold-mirror.pub`, to that repository as a **deploy key with write access**. A deploy key opens that one repository and nothing else in your organization.
4. Give the server the repository address and the private half, as environment variables. The key can be pasted as it is or encoded in base64:

```bash
BRAINFOLD_MIRROR=git@github.com:your-org/brain-backup.git
BRAINFOLD_MIRROR_KEY=<contents of the brainfold-mirror file>
```

5. Restart the server and check the mirror state on the **Overview** page or in `/api/health`.

The mirror is configured by whoever deploys the server. It cannot be changed from this panel.

### How it behaves

After every change the server pushes the history to the `main` branch in the background.

| State | Meaning |
| --- | --- |
| `ok` | The mirror has every change. |
| `pending` | A push is on its way. |
| `failing` | The last push failed. The brain keeps working and the server tries again on the next change. Check the key and the address. |
| `off` | No mirror is configured. |

### Who can read the mirror

The mirror holds the **whole brain, without permissions applied**: every folder, including the restricted ones. Anyone who can read that repository reads everything. Give access to it only to the people who operate the server.

### Restoring from the mirror

Start the server with an **empty** brain folder and the same two variables: it clones the mirror before serving. Nothing is restored over a folder that already has content.

## What the mirror does not cover

The mirror holds the brain: files, guidance and access rules. It does **not** hold the accounts database: members, groups, tokens, activity and revision records. Back up the volume itself to keep those. Without the database you keep all content, and recreate accounts and groups.

## Recovering access

If an administrator forgets their password and no other administrator can reset it, run this on the server:

```bash
brainfold reset-password admin@example.com
```

It prints a one-time link to choose a new password.
