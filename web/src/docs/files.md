# Files of any type

Text files travel over MCP. Everything else (a PDF manual, a spreadsheet, an image) is uploaded and downloaded by people in this panel, and by agents through the `brainfold` command with the same token and the same permissions.

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

Open a folder in **Brain**:

- **Download** any file you can read, from its row or from the file's page.
- **Upload** files to a folder where you can write, with the button or by dropping them on the folder. Replacing a file asks first, and the previous version stays in the history.
- **Describe** a file in one line, right after uploading it or later with the pencil in its row. Agents see that line in the folder listing, which is how they know what a PDF or a spreadsheet holds before fetching it.

The panel shows text files, with Markdown rendered. Files of other types are only downloaded: the server always sends them as a file to save, never as a page to open, so a file stored in the brain cannot run inside the panel.
