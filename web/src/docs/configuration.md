# Configuration

`brainfold serve` takes its settings from flags or from the environment.

| Flag | Environment | Default | Meaning |
| --- | --- | --- | --- |
| `--root` | `BRAINFOLD_ROOT` | | The brain folder. Created if missing. |
| `--db` | `BRAINFOLD_DB` | `brainfold.db` | Accounts database. Must be outside the brain folder. |
| `--host` | | `127.0.0.1` | Address to listen on. |
| `--port` | `PORT` | `8020` | Port to listen on. |
| `--public-url` | `BRAINFOLD_PUBLIC_URL` | | The HTTPS address people use. Required to listen beyond this machine. |
| `--mirror` | `BRAINFOLD_MIRROR` | | A git remote that receives every change. |
| | `BRAINFOLD_MIRROR_KEY` | | SSH private key for the mirror, as PEM or base64. |

## What a public URL changes

Setting a public URL tells Brainfold it sits behind a TLS proxy at that address:

- Session cookies are always marked Secure.
- Creating the first account requires the setup code printed in the logs.
- Requests for any other host name are refused.
- The client address used to throttle sign-ins comes from the proxy.

## The brain and the database belong together

On first start the server marks the brain folder and the database with the same identity. If it later starts with the database but a different or empty folder, it stops instead of showing an empty brain. That almost always means a volume is not mounted.
