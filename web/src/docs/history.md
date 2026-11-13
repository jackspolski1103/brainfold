# Versions, history and restore

## Every change is kept

The brain folder is its own git repository. Every write, move and delete is a commit under the author's name. Nothing is overwritten silently.

## Versions prevent lost updates

`read` returns the file's `version`. Replacing, moving or deleting a file requires passing that version back. If someone else changed the file in between, the call fails with `conflict` and the agent reads again before retrying. Two agents never overwrite each other.

Creating a file that already exists fails with `already_exists`.

## History

`history` lists who changed a file and when, including a file that was deleted. It returns revision numbers, no content.

## Restore

`restore` brings a file back to one of its revisions. It works on deleted files too.

A revision is restorable only by someone who could read the file **when that revision was written** and can write there now. Tightening a folder's access later does not expose its older content.

## Edits made outside Brainfold

If someone edits the brain folder by hand on the server, Brainfold records that content in the history when it starts, and again before it next changes the file, so nothing is replaced without a copy.
