# Command line

The `brainfold` command runs the server and moves files.

## brainfold serve

Serve a folder as a shared brain. See [Configuration](#/docs/configuration) for every setting.

```bash
brainfold serve --root ./my-brain
```

## brainfold put

Upload a file of any type.

```bash
brainfold put <file> <path-in-the-brain> [--replace]
```

## brainfold get

Download a file.

```bash
brainfold get <path-in-the-brain> <destination>
```

`put` and `get` read the server address and your token from `BRAINFOLD_URL` and `BRAINFOLD_TOKEN`, or from `~/.config/brainfold/config.toml`. See [Files of any type](#/docs/files).

## brainfold reset-password

Run on the server to recover an account. Prints a one-time link.

```bash
brainfold reset-password <email> [--db <database>] [--public-url <address>]
```
