# Run it for your team

One server per team. Exactly one process: the brain keeps a single lock, so do not run replicas.

## With Docker Compose

The repository includes a compose file that runs Brainfold behind a proxy that obtains a TLS certificate for your domain.

```bash
BRAINFOLD_DOMAIN=brain.example.com docker compose up -d
docker compose logs brainfold      # prints the setup code for the first account
```

Two volumes hold everything: `/brain` (the brain) and `/data` (accounts, tokens, activity and revision records).

## On a hosting platform

The container image reads its settings from the environment, so it runs on any platform that builds a Dockerfile and gives you a persistent volume. The repository includes a `railway.json` for Railway.

1. Create a service from the repository and attach **one volume**.
2. Point both the brain and the accounts database inside that volume, in different folders.
3. Set the public address so cookies are secure and the first account needs the setup code.

```bash
BRAINFOLD_ROOT=/data/brain
BRAINFOLD_DB=/data/accounts/brainfold.db
BRAINFOLD_PUBLIC_URL=https://your-server
```

4. Read the setup code in the service logs (`Setup code for the first account: …`) and create the first account in the panel.

> Without a volume, the brain is lost on every redeploy. Add a [mirror](#/docs/durability) as well.

## On your own machine

```bash
uv sync
uv run brainfold serve --root ./my-brain
```

By default the server listens only on this machine. It refuses to listen on other addresses unless you set a public URL, because that means traffic must go through a TLS proxy.

## Health check

`GET /api/health` answers without signing in:

```json
{ "git": true, "database": true, "unversioned_writes": 0, "mirror": "ok" }
```
