import { KeyRound, Pencil, Plus, Trash2, UserPlus, Users } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { type Member, api, message } from "./api";
import { Badge, Button, Code, Dialog, Empty, Field, Input, Notice, PageHeader, SearchInput, Section, Select, Table, Tabs, Td, Tr } from "./ui";

type Groups = Record<string, string[]>;
type Link = { url: string; note: string };

function InviteDialog({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: (link: Link) => void }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const result = await api<{ invite: string }>("POST", "/api/users", { email, role });
      onDone({ url: `${location.origin}/#/accept/${result.invite}`, note: `Send this link to ${email}. It works once and is not shown again.` });
      setEmail("");
      setError("");
      onClose();
    } catch (failure) {
      setError(message(failure));
    }
  }
  return (
    <Dialog open={open} onClose={onClose} title="Invite someone" description="Brainfold sends no email: you get a one-time link to pass on yourself.">
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email">
          <Input type="email" required autoFocus placeholder="ana@example.com" value={email} onChange={(event) => setEmail(event.target.value)} />
        </Field>
        <Field label="Role" hint="Administrators manage members, groups and folder access. Members only use what they were granted.">
          <Select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="member">Member</option>
            <option value="admin">Administrator</option>
          </Select>
        </Field>
        {error && <Notice>{error}</Notice>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary">Create invitation</Button>
        </div>
      </form>
    </Dialog>
  );
}

function GroupDialog({ group, members, groups, onClose, onSaved }: { group: string | null; members: Member[]; groups: Groups; onClose: () => void; onSaved: () => void }) {
  const creating = group === "";
  const [name, setName] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    setName(group ?? "");
    setPicked(group ? (groups[group] ?? []) : []);
    setError("");
  }, [group, groups]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      await api("PUT", `/api/groups/${encodeURIComponent(name)}`, { members: picked });
      onSaved();
      onClose();
    } catch (failure) {
      setError(message(failure));
    }
  }
  const people = members.filter((member) => !member.pending);
  return (
    <Dialog open={group !== null} onClose={onClose} title={creating ? "New group" : `Group @${group}`} description="A group is a name for several people. Grant a folder to @name and all of them get it.">
      <form onSubmit={submit} className="space-y-4">
        {creating && (
          <Field label="Name" hint="Lowercase letters, digits, hyphen and underscore.">
            <Input required autoFocus pattern="[a-z0-9][a-z0-9_\-]*" maxLength={63} placeholder="finance" value={name} onChange={(event) => setName(event.target.value)} />
          </Field>
        )}
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">Members</legend>
          <div className="max-h-64 space-y-0.5 overflow-y-auto rounded-md border border-line p-1.5">
            {people.map((member) => (
              <label key={member.email} className="flex cursor-pointer items-center gap-2.5 rounded px-2 py-1.5 text-sm hover:bg-fg/5">
                <input
                  type="checkbox"
                  className="accent-(--accent)"
                  checked={picked.includes(member.email)}
                  onChange={(event) => setPicked(event.target.checked ? [...picked, member.email] : picked.filter((email) => email !== member.email))}
                />
                {member.email}
              </label>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-faint">
            {picked.length === 0 && !creating ? "Saving with nobody selected deletes the group and retires its name for good." : "People appear here once they accepted their invitation."}
          </p>
        </fieldset>
        {error && <Notice>{error}</Notice>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button type="submit" variant={picked.length === 0 && !creating ? "danger" : "primary"} disabled={creating && picked.length === 0}>
            {picked.length === 0 && !creating ? "Delete group" : "Save group"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

export function Members({ self, tab }: { self: string; tab: "users" | "groups" }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [groups, setGroups] = useState<Groups>({});
  const [filter, setFilter] = useState("");
  const [inviting, setInviting] = useState(location.hash.endsWith("?invite"));
  const [group, setGroup] = useState<string | null>(null);
  const [link, setLink] = useState<Link | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setMembers((await api<{ users: Member[] }>("GET", "/api/users")).users);
      setGroups((await api<{ groups: Groups }>("GET", "/api/groups")).groups);
    } catch (failure) {
      setError(message(failure));
    }
  }, []);
  useEffect(() => void load(), [load]);

  const attempt = async (action: () => Promise<unknown>) => {
    setError("");
    try {
      await action();
      await load();
    } catch (failure) {
      setError(message(failure));
    }
  };
  const reset = (email: string, pending: boolean) =>
    attempt(async () => {
      const result = await api<{ invite: string }>("POST", `/api/users/${encodeURIComponent(email)}/reset`, {});
      setLink({ url: `${location.origin}/#/accept/${result.invite}`, note: pending ? `Send this link to ${email}. It works once and replaces the invitation sent before.` : `Send this link to ${email} to choose a new password. It works once; their current password keeps working until they use it.` });
    });
  const needle = filter.trim().toLowerCase();
  const shown = members.filter((member) => `${member.email} ${member.role} ${member.groups.join(" ")}`.toLowerCase().includes(needle));
  const names = Object.keys(groups).filter((name) => `${name} ${groups[name].join(" ")}`.toLowerCase().includes(needle));

  return (
    <>
      <PageHeader icon={Users} title="Members">
        The people of this brain and the groups used to grant folders to several of them at once.
      </PageHeader>
      <Tabs
        value={tab}
        onChange={(id) => (location.hash = id === "users" ? "#/members" : "#/members/groups")}
        tabs={[
          { id: "users", label: `Users · ${members.length}` },
          { id: "groups", label: `Groups · ${Object.keys(groups).length}` },
        ]}
      />
      <div className="space-y-5">
        {error && <Notice>{error}</Notice>}
        {link && (
          <Section title="One-time link" description={link.note} action={<Button size="sm" variant="ghost" onClick={() => setLink(null)}>Dismiss</Button>}>
            <Code title="Link" text={link.url} />
          </Section>
        )}
        {tab === "users" ? (
          <Section
            title="Users"
            docs="members"
            description="Invite people and manage their accounts. Each person connects their own harness with their own token."
            action={<Button variant="primary" onClick={() => setInviting(true)}><UserPlus size={15} aria-hidden /> Invite</Button>}
          >
            <SearchInput aria-label="Filter users" placeholder="Search users by email, role or group…" className="mb-4" value={filter} onChange={(event) => setFilter(event.target.value)} />
            <Table head={["Email", "Role", "Groups", "Status", ""]}>
              {shown.map((member) => (
                <Tr key={member.email}>
                  <Td>
                    <span className="font-medium">{member.email}</span>
                    {member.email === self && <span className="ml-2 text-xs text-faint">you</span>}
                  </Td>
                  <Td>{member.role === "admin" ? <Badge tone="accent">Administrator</Badge> : <Badge>Member</Badge>}</Td>
                  <Td>
                    <span className="flex flex-wrap gap-1">
                      {member.groups.length ? member.groups.map((name) => <Badge key={name} tone="accent">@{name}</Badge>) : <span className="text-faint">—</span>}
                    </span>
                  </Td>
                  <Td>{member.pending ? <Badge tone="warning">Invited</Badge> : <Badge tone="success">Active</Badge>}</Td>
                  <Td className="w-px">
                    <span className="flex justify-end gap-1">
                      <Button size="sm" variant="ghost" onClick={() => void reset(member.email, member.pending)}>
                        <KeyRound size={13} aria-hidden /> {member.pending ? "New invite link" : "Reset password"}
                      </Button>
                      {member.email !== self && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="hover:text-danger"
                          onClick={() => confirm(`Remove ${member.email}? Their tokens stop working at once.`) && void attempt(() => api("DELETE", `/api/users/${encodeURIComponent(member.email)}`))}
                        >
                          <Trash2 size={13} aria-hidden /> Remove
                        </Button>
                      )}
                    </span>
                  </Td>
                </Tr>
              ))}
            </Table>
          </Section>
        ) : (
          <Section
            title="Groups"
            docs="members"
            description="Grant a folder to @group instead of naming each person."
            action={<Button variant="primary" onClick={() => setGroup("")}><Plus size={15} aria-hidden /> Create</Button>}
          >
            {Object.keys(groups).length === 0 ? (
              <Empty icon={Users} title="No groups yet" action={<Button variant="primary" onClick={() => setGroup("")}><Plus size={15} aria-hidden /> Create group</Button>}>
                Create one per team, then grant folders to it in the Access section.
              </Empty>
            ) : (
              <>
                <SearchInput aria-label="Filter groups" placeholder="Search groups by name or member…" className="mb-4" value={filter} onChange={(event) => setFilter(event.target.value)} />
                <Table head={["Group", "Members", ""]}>
                  {names.map((name) => (
                    <Tr key={name} onClick={() => setGroup(name)}>
                      <Td><Badge tone="accent">@{name}</Badge></Td>
                      <Td>
                        <span className="flex flex-wrap gap-1">{groups[name].map((email) => <Badge key={email}>{email}</Badge>)}</span>
                      </Td>
                      <Td className="w-px text-right">
                        <Button size="sm" variant="ghost" aria-label={`Edit group ${name}`} onClick={(event) => { event.stopPropagation(); setGroup(name); }}><Pencil size={13} aria-hidden /> Edit</Button>
                      </Td>
                    </Tr>
                  ))}
                </Table>
              </>
            )}
          </Section>
        )}
      </div>
      <InviteDialog open={inviting} onClose={() => setInviting(false)} onDone={setLink} />
      <GroupDialog group={group} members={members} groups={groups} onClose={() => setGroup(null)} onSaved={() => void load()} />
    </>
  );
}
