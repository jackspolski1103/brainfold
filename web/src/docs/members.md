# Members and groups

## Roles

| Role | Can do |
| --- | --- |
| Administrator | Invite and remove members, manage groups, set folder access, see activity |
| Member | Use what they were granted, manage their own tokens and password |

The first account is an administrator. The last administrator cannot be removed.

## Inviting

**Members → Invite** creates a one-time link that works for 7 days. Brainfold does not send email: pass the link on yourself. The person opens it, chooses a password of at least 10 characters, and is in. The link is shown once: if it gets lost or expires before it is used, **New invite link** on that person's row creates another and cancels the first.

## Groups

A group is a name for several people. Granting a folder to `@finance` grants it to every member, today and later.

- Group names use lowercase letters, digits, hyphen and underscore.
- Only people who accepted their invitation can be added.
- Saving a group with no members deletes it and **retires its name for good**. A new group can never silently inherit the folders of an old one.

## Passwords

- Each person changes their own password in **Account**; other sessions are signed out and **every harness token** of that account is revoked, so the person creates new tokens in **Connect**.
- An administrator can **reset** a member's password: this creates a one-time link that works for 7 days, and the current password keeps working until the link is used. Using it ends every session and **revokes every harness token** of that account, so the person creates new tokens in **Connect**. Use it when an account may be compromised.
- After five failed sign-ins, an email is locked from that address for one minute.

If the only administrator is locked out, see [recovering access](#/docs/durability).

## Removing a member

Removing someone revokes their sessions and all of their tokens at once, and takes them out of every group and every folder's access list. Their personal folder stays on disk, and its name is never given to another account. If the same email is invited again later, it is a new account that starts with nothing.
