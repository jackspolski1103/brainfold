# Files of any type

Text files travel over MCP. Everything else (a PDF manual, a spreadsheet, an image) travels through the `brainfold` command, with the same token and the same permissions.

## Upload and download

```bash
export BRAINFOLD_URL="https://your-server"
export BRAINFOLD_TOKEN="<your-token>"

brainfold put salaries.xlsx /hr/salaries.xlsx
brainfold get /hr/salaries.xlsx ./salaries.xlsx
```

Use `--replace` with `put` to replace a file that already exists. Files up to 25 MB are accepted.

Instead of environment variables you can keep the address and token in `~/.config/brainfold/config.toml`, readable only by you:

```toml
url = "https://your-server"
token = "<your-token>"
```

The command refuses to send a token over plain HTTP unless the server is on your own machine.

## What the agent does with them

When an agent reads a file that is not text, it does not receive the bytes. It receives the exact `brainfold get` command to fetch the file to disk, and then opens it with its own tools.

## In this panel

The panel shows text files, with Markdown rendered. It never downloads other files; it shows the command to fetch them.
