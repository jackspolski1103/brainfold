# Permissions

Access is decided per folder, for two actions: **read** and **write**. An agent has exactly the access of the person whose token it uses.

## Who can be granted

| Grant | Meaning |
| --- | --- |
| `ana@example.com` | One person |
| `@finance` | Every member of the group |
| `*` | Everyone with an account |

## Read

Reading is denied unless a folder grants it. Every folder that declares a read list **narrows** what hangs below it: to read a file you must be granted by every folder on the path that declares one.

```
/                  read = *              ← everyone with an account
└── hr/            read = @hr           ← only @hr members who can also read /
    └── salaries/  (nothing declared)   ← same as hr/
```

A folder can never give back what a folder above took away.

## Write

Writing follows the **nearest** folder that declares a write list, looking upward. With no declaration anywhere, nobody can write. Writing always requires being able to read.

## What a person without access sees

Nothing. A path you cannot read behaves exactly like a path that does not exist: the same answer, the same error. An agent cannot learn that a hidden folder is there.

## Administrators

An administrator sees the structure of the whole brain and the rules of every folder, and can change them. An administrator does **not** read the content of folders they were not granted, and cannot open anyone's personal folder.

## Changing access

Two ways, both for administrators only:

- **Access** in this panel lists every folder with what it declares or inherits.
- **From a harness**, with a token created in **Connect a harness** with *Can manage access and groups*. The agent then has `get_access`, `set_access` and `set_group`. See [MCP tools](#/docs/tools).

Every other token, including an administrator's everyday one, cannot change access lists: its agent can only create folders, which start with the rules of the folder above. Keep the managing token for the harness where you administer: an agent that reads the brain reads text written by teammates, and a token that cannot manage cannot be talked into opening a folder.

A folder whose access was declared cannot be moved or deleted by an agent.
