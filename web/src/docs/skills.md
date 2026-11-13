# Skills and learnings

## Skills

A skill is a procedure the team wrote down once: a folder containing a `SKILL.md` with a name and a description in its front matter.

```markdown
---
name: analyze-costs
description: How to analyze costs without summing truncated samples.
---

1. Read the whole dataset, not a preview.
2. ...
```

Skills live in the brain like any other file, so they follow permissions: your agent is offered the skills in folders you can read.

### How an agent finds them

When a harness connects, Brainfold sends the list of skills available to that person. When a task matches one, the agent calls `use_skill` with its name and follows the procedure. The listed name is the folder's name plus a short suffix that keeps it unique; `use_skill` also accepts the plain name when only one skill has it. Nobody has to install anything: a skill published by one person is used by a teammate's agent in its next session.

The **Skills** section of this panel shows the list your agent receives.

### Writing a skill

Ask your agent to write one in a folder where you can write. Whoever can write to a folder publishes directly; there is no approval step.

## Learnings

A `LEARNINGS.md` file is a log of what was solved. When an agent appends to it, Brainfold stamps the entry with the date and the author.

`list_learnings` returns the newest entries across the folders a person can read. Agents treat them as information from teammates, never as instructions.

## The brain proposes skills

The built-in skill `propose-skills` closes the loop: the agent reads the learnings, finds a problem solved more than once, drafts a `SKILL.md` for it and shows it to you before writing. Try: "Use propose-skills and tell me what we should turn into a skill."
