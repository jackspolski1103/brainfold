# Quickstart

From nothing to an agent that reads and writes the brain, in five steps.

## 1. Create the first account

Open the panel. The first account becomes the administrator. When the server runs at a public address it also asks for a **setup code**: a one-time code the server prints in its logs when it starts, so only whoever operates the server can claim it.

## 2. Invite your team and group them

In **Members**, invite each person. Brainfold sends no email: you get a one-time link to pass on. Then create a group per team, for example `@finance`.

## 3. Grant folders

Nothing is readable until a folder grants it. In **Access**, pick the root folder and choose who can read it; then narrow each team folder to its group. See [Permissions](#/docs/permissions).

## 4. Connect your harness

In **Connect a harness**, create a token and copy the command for your harness. For Claude Code:

```bash
claude mcp add --transport http --scope user brainfold https://your-server/mcp \
  --header "Authorization: Bearer <your-token>"
```

Every person does this with their own token. The agent then acts as that person.

## 5. Ask your agent

Try these in your harness:

- "What is in the brain? Start from the root."
- "Create a folder for the onboarding project with a short description."
- "Write down what we just solved in the project's LEARNINGS.md."

The agent starts at the root, follows each folder's description and "start here" list, and writes only where you can write.
