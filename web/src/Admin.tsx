import { type FormEvent, useCallback, useEffect, useState } from "react";
import { type Activity, ApiError, type Member, type Token, api, when } from "./api";
import { Badge, Button, Card, Copyable, Field, Input, Notice, Table, Td } from "./ui";

const message = (failure: unknown) => (failure instanceof ApiError ? failure.message : "Something went wrong.");
const parse = (text: string) => text.split(/[\s,]+/).filter(Boolean);

export function Members({ self }: { self: string }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [groups, setGroups] = useState<Record<string, string[]>>({});
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");
  const [invite, setInvite] = useState("");
  const [group, setGroup] = useState("");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    try {
      setMembers((await api<{ users: Member[] }>("GET", "/api/users")).users);
      setGroups((await api<{ groups: Record<string, string[]> }>("GET", "/api/groups")).groups);
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
  const sendInvite = (event: FormEvent) => {
    event.preventDefault();
    void attempt(async () => {
      const result = await api<{ invite: string }>("POST", "/api/users", { email, role });
      setInvite(`${location.origin}/#/accept/${result.invite}`);
      setEmail("");
    });
  };
  const saveGroup = (groupName: string, list: string) =>
    attempt(async () => {
      await api("PUT", `/api/groups/${encodeURIComponent(groupName)}`, { members: parse(list) });
      setDrafts(({ [groupName]: _saved, ...rest }) => rest);
      setGroup("");
    });

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Members</h1>
      {error && <Notice>{error}</Notice>}
      <Card title="Invite someone">
        <form onSubmit={sendInvite} className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1"><Field label="Email"><Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Field></div>
          <Field label="Role">
            <select value={role} onChange={(e) => setRole(e.target.value)} className="h-9 rounded-md border border-zinc-300 bg-white px-2 text-sm dark:border-zinc-700 dark:bg-zinc-900">
              <option value="member">member</option>
              <option value="admin">admin</option>
            </select>
          </Field>
          <Button type="submit">Create invitation</Button>
        </form>
        {invite && (
          <div className="mt-4 space-y-2">
            <Notice tone="blue">Send this link to the person. It works once and is not shown again.</Notice>
            <Copyable text={invite} />
          </div>
        )}
      </Card>
      <Card title="People">
        <Table head={["Email", "Role", "Groups", ""]} empty={members.length === 0}>
          {members.map((member) => (
            <tr key={member.email}>
              <Td>{member.email} {member.pending && <Badge tone="amber">invited</Badge>}</Td>
              <Td>{member.role}</Td>
              <Td><span className="flex flex-wrap gap-1">{member.groups.map((item) => <Badge key={item}>@{item}</Badge>)}</span></Td>
              <Td>
                {member.email !== self && (
                  <Button variant="danger" onClick={() => confirm(`Remove ${member.email}? Their tokens stop working at once.`) && void attempt(() => api("DELETE", `/api/users/${encodeURIComponent(member.email)}`))}>
                    Remove
                  </Button>
                )}
              </Td>
            </tr>
          ))}
        </Table>
      </Card>
      <Card title="Groups">
        <div className="space-y-3">
          {Object.entries(groups).map(([groupName, list]) => (
            <div key={groupName} className="flex flex-wrap items-center gap-2">
              <span className="w-32 shrink-0 font-mono text-sm">@{groupName}</span>
              <Input aria-label={`Members of ${groupName}`} className="min-w-56 flex-1" value={drafts[groupName] ?? list.join(", ")} onChange={(e) => setDrafts({ ...drafts, [groupName]: e.target.value })} />
              <Button variant="outline" disabled={drafts[groupName] === undefined} onClick={() => void saveGroup(groupName, drafts[groupName])}>Save</Button>
            </div>
          ))}
          <form onSubmit={(event) => { event.preventDefault(); void saveGroup(group, drafts["+"] ?? ""); }} className="flex flex-wrap items-end gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-800">
            <div className="w-32"><Field label="New group"><Input required pattern="[a-z0-9][a-z0-9_\-]*" placeholder="finance" value={group} onChange={(e) => setGroup(e.target.value)} /></Field></div>
            <div className="min-w-56 flex-1"><Field label="Members"><Input required placeholder="ana@example.com, leo@example.com" value={drafts["+"] ?? ""} onChange={(e) => setDrafts({ ...drafts, "+": e.target.value })} /></Field></div>
            <Button type="submit" variant="outline">Create</Button>
          </form>
          <p className="text-xs text-zinc-500">Emptying a group retires its name for good, so nobody inherits its history.</p>
        </div>
      </Card>
    </>
  );
}

export function Tokens() {
  const [tokens, setTokens] = useState<Token[]>([]);
  const [label, setLabel] = useState("");
  const [created, setCreated] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => api<{ tokens: Token[] }>("GET", "/api/tokens").then((result) => setTokens(result.tokens), (failure) => setError(message(failure))), []);
  useEffect(() => void load(), [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      setCreated((await api<{ token: string }>("POST", "/api/tokens", { name: label })).token);
      setLabel("");
      await load();
    } catch (failure) {
      setError(message(failure));
    }
  }

  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Tokens</h1>
      <p className="text-sm text-zinc-500">A token connects your harness to the brain with your permissions.</p>
      {error && <Notice>{error}</Notice>}
      <Card title="New token">
        <form onSubmit={create} className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1"><Field label="Name" hint="For example the harness and machine that will use it."><Input required maxLength={80} value={label} onChange={(e) => setLabel(e.target.value)} /></Field></div>
          <Button type="submit">Create token</Button>
        </form>
        {created && (
          <div className="mt-4 space-y-2">
            <Notice tone="blue">Copy the token now. It is not shown again.</Notice>
            <Copyable text={created} />
            <p className="pt-2 text-sm font-medium">Connect Claude Code</p>
            <Copyable text={`claude mcp add --transport http oif ${location.origin}/mcp --header "Authorization: Bearer ${created}"`} />
          </div>
        )}
      </Card>
      <Card title="Your tokens">
        <Table head={["Name", "Created", "Last used", ""]} empty={tokens.length === 0}>
          {tokens.map((token) => (
            <tr key={token.id}>
              <Td>{token.name}</Td>
              <Td>{when(token.created)}</Td>
              <Td>{when(token.last_used)}</Td>
              <Td><Button variant="danger" onClick={() => confirm(`Revoke "${token.name}"?`) && void api("DELETE", `/api/tokens/${token.id}`).then(load)}>Revoke</Button></Td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  );
}

export function ActivityPage() {
  const [rows, setRows] = useState<Activity[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ activity: Activity[] }>("GET", "/api/activity?limit=500").then((result) => setRows(result.activity), (failure) => setError(message(failure)));
  }, []);
  const needle = filter.toLowerCase();
  const shown = rows.filter((row) => `${row.actor} ${row.action} ${row.path}`.toLowerCase().includes(needle));
  return (
    <>
      <h1 className="text-xl font-semibold tracking-tight">Activity</h1>
      {error && <Notice>{error}</Notice>}
      <Card title="Latest 500 events" action={<Input aria-label="Filter activity" placeholder="Filter by person, action or path" className="w-64" value={filter} onChange={(e) => setFilter(e.target.value)} />}>
        <Table head={["When", "Who", "Action", "Path", "Result"]} empty={shown.length === 0}>
          {shown.map((row, index) => (
            <tr key={index}>
              <Td>{when(row.at)}</Td>
              <Td>{row.actor}</Td>
              <Td mono>{row.action}</Td>
              <Td mono>{row.path}</Td>
              <Td>
                <span className="flex gap-1">
                  <Badge tone={row.ok ? "green" : "red"}>{row.ok ? "ok" : "denied"}</Badge>
                  {row.versioned === false && <Badge tone="amber">not in history</Badge>}
                </span>
              </Td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  );
}
