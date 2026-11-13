# Members and groups

## Roles

| Role | Can do |
| --- | --- |
| Administrator | Invite and remove members, manage groups, set folder access, see activity |
| Member | Use what they were granted, manage their own tokens and password |

The first account is an administrator. The last administrator cannot be removed.

## Inviting

**Members → Invite** creates a one-time link. Brainfold does not send email: pass the link on yourself. The person opens it, chooses a password of at least 10 characters, and is in.

## Groups

A group is a name for several people. Granting a folder to `@finance` grants it to every member, today and later.

- Group names use lowercase letters, digits, hyphen and underscore.
- Only people who accepted their invitation can be added.
- Saving a group with no members deletes it and **retires its name for good**. A new group can never silently inherit the folders of an old one.

## Passwords

- Each person changes their own password in **Account**; other sessions are signed out.
- An administrator can **reset** a member's password: this creates a one-time link, and the current password keeps working until the link is used.
- After five failed sign-ins, an email is locked from that address for one minute.

If the only administrator is locked out, see [recovering access](#/docs/durability).

## Removing a member

Removing someone revokes their sessions and all of their tokens at once. Their personal folder stays on disk, and its name is never given to another account.
