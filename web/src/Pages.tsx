import { BookOpen, FolderTree, LayoutGrid, type LucideIcon, Plug, ScrollText, ShieldCheck, Sparkles, UserRound, Users } from "lucide-react";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { type Activity, type Health, type Listing, type Member, type Skill, type Token, type User, api, message, tree, when } from "./api";
import { Badge, Button, Empty, Field, Input, Notice, PageHeader, SearchInput, Section, Segmented, Table, Td, Tr } from "./ui";

function Product({ href, icon: Icon, title, children, stats }: { href: string; icon: LucideIcon; title: string; children: ReactNode; stats: [number | string, string][] }) {
  return (
    <a href={href} className="group flex flex-col rounded-lg border border-line bg-card p-5 transition-colors hover:border-accent/40">
      <div className="flex gap-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-accent/25 bg-accent/10 text-accent">
          <Icon size={17} aria-hidden />
        </span>
        <div className="min-w-0">
          <h2 className="text-lg leading-8 underline decoration-accent/60 underline-offset-4 group-hover:decoration-accent">{title}</h2>
          <p className="mt-1 text-sm text-muted">{children}</p>
        </div>
      </div>
      <div className="mt-5 flex flex-wrap gap-x-4 gap-y-1 border-t border-line pt-4 text-sm">
        {stats.map(([value, label], index) => (
          <span key={label} className={index ? "border-l border-line pl-4" : undefined}>
            <span className="font-semibold">{value}</span> <span className="text-xs text-muted">{label}</span>
          </span>
        ))}
      </div>
    </a>
  );
}

export function Overview({ user }: { user: User }) {
  const admin = user.role === "admin";
  const [root, setRoot] = useState<Listing | null>(null);
  const [tokens, setTokens] = useState<Token[] | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [groups, setGroups] = useState<Record<string, string[]>>({});
  const [activity, setActivity] = useState<Activity[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  useEffect(() => {
    const quiet = () => undefined;
    tree("/").then(setRoot, quiet);
    api<{ tokens: Token[] }>("GET", "/api/tokens").then((result) => setTokens(result.tokens), quiet);
    api<{ skills: Skill[] }>("GET", "/api/skills").then((result) => setSkills(result.skills), quiet);
    api<Health>("GET", "/api/health").then(setHealth, quiet);
    if (!admin) return;
    api<{ users: Member[] }>("GET", "/api/users").then((result) => setMembers(result.users), quiet);
    api<{ groups: Record<string, string[]> }>("GET", "/api/groups").then((result) => setGroups(result.groups), quiet);
    api<{ activity: Activity[] }>("GET", "/api/activity?limit=500").then((result) => setActivity(result.activity), quiet);
  }, [admin]);

  const folders = root?.entries.filter((entry) => entry.kind === "directory").length ?? 0;
  const day = activity.filter((row) => row.at > Date.now() / 1000 - 86400);
  const used = (tokens ?? []).filter((token) => token.last_used).length;
  const light = (ok: boolean, good: string, bad: string, warn = false) => <Badge tone={ok ? "success" : warn ? "warning" : "danger"}>{ok ? good : bad}</Badge>;

  return (
    <>
      <PageHeader icon={LayoutGrid} title="Overview">
        One shared brain for the team's agents: folders with permissions that every harness reads and writes.
      </PageHeader>
      {tokens?.length === 0 && (
        <div className="mb-5">
          <Notice tone="accent">
            Your agent is not connected yet. <a href="#/connect" className="underline">Create a token and connect your harness</a> to start using the brain.
          </Notice>
        </div>
      )}
      <div className="grid gap-5 xl:grid-cols-2">
        <Product href="#/brain/" icon={FolderTree} title="Brain" stats={[[folders, "top-level folders"], [(root?.entries.length ?? 0) - folders, "files at the root"]]}>
          Browse every folder and file you can read, with the guidance agents follow to find what matters.
        </Product>
        <Product href="#/connect" icon={Plug} title="Connect a harness" stats={[[tokens?.length ?? 0, "tokens"], [used, "in use"]]}>
          Credentials and setup commands for Claude Code, Codex, Cursor or any other MCP client.
        </Product>
        <Product href="#/skills" icon={Sparkles} title="Skills" stats={[[skills.length, "available to your agent"]]}>
          Procedures the team wrote once. Your agent sees them listed and uses them on its own.
        </Product>
        {admin && (
          <>
            <Product href="#/access" icon={ShieldCheck} title="Access" stats={[[Object.keys(groups).length, "groups"], [folders, "top-level folders"]]}>
              Decide who reads and who writes each folder. Nothing is open until a folder grants it.
            </Product>
            <Product href="#/members" icon={Users} title="Members" stats={[[members.filter((member) => !member.pending).length, "active"], [members.filter((member) => member.pending).length, "invited"], [Object.keys(groups).length, "groups"]]}>
              Invite people, reset passwords and organize them into groups.
            </Product>
            <Product href="#/activity" icon={ScrollText} title="Activity" stats={[[day.length, "events in 24 h"], [day.filter((row) => !row.ok).length, "denied"]]}>
              Every read, write and administrative change, with who did it and whether it was allowed.
            </Product>
          </>
        )}
        <Product href="#/docs" icon={BookOpen} title="Documentation" stats={[["15", "tools for agents"]]}>
          How the brain works, how permissions are decided and how to run it for your team.
        </Product>
      </div>
      {health && (
        <div className="mt-5">
          <Section title="Server" docs="durability" description="What keeps the brain safe.">
            <div className="flex flex-wrap gap-x-8 gap-y-3">
              <span className="flex items-center gap-2"><span className="text-muted">Accounts database</span>{light(health.database, "Healthy", "Failing")}</span>
              <span className="flex items-center gap-2"><span className="text-muted">Version history</span>{light(health.git, "Every change is kept", "Off")}</span>
              <span className="flex items-center gap-2"><span className="text-muted">Changes outside history</span>{light(health.unversioned_writes === 0, "None", String(health.unversioned_writes))}</span>
              <span className="flex items-center gap-2">
                <span className="text-muted">Off-site mirror</span>
                {health.mirror === "ok" ? <Badge tone="success">Up to date</Badge> : health.mirror === "pending" ? <Badge tone="warning">Sending</Badge> : health.mirror === "failing" ? <Badge tone="danger">Failing</Badge> : <Badge>Not configured</Badge>}
              </span>
            </div>
          </Section>
        </div>
      )}
    </>
  );
}

export function Skills() {
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ skills: Skill[] }>("GET", "/api/skills").then((result) => setSkills(result.skills), (failure) => setError(message(failure)));
  }, []);
  return (
    <>
      <PageHeader icon={Sparkles} title="Skills">
        Procedures stored in the brain as folders with a SKILL.md. Your agent gets this list when it connects and runs a skill with use_skill.
      </PageHeader>
      {error && <Notice>{error}</Notice>}
      <Section title="Available to your agent" docs="skills" description="You see the skills in folders you can read. Other people may see a different list.">
        {skills?.length === 0 ? (
          <Empty icon={Sparkles} title="No skills yet">Ask your agent to write one in a folder where you can write.</Empty>
        ) : (
          <Table head={["Skill", "What it does", "Where it lives"]}>
            {(skills ?? []).map((skill) => (
              <Tr key={skill.name} onClick={skill.path ? () => (location.hash = `#/file${skill.path}`) : undefined}>
                <Td mono><span className="whitespace-nowrap text-fg">{skill.name}</span></Td>
                <Td><span className="text-muted">{skill.description}</span></Td>
                <Td mono>{skill.path ? <a href={`#/file${skill.path}`} className="hover:underline">{skill.path}</a> : <Badge>Built in</Badge>}</Td>
              </Tr>
            ))}
          </Table>
        )}
      </Section>
    </>
  );
}

export function ActivityPage() {
  const [rows, setRows] = useState<Activity[] | null>(null);
  const [filter, setFilter] = useState("");
  const [result, setResult] = useState<"all" | "denied">("all");
  const [error, setError] = useState("");
  useEffect(() => {
    api<{ activity: Activity[] }>("GET", "/api/activity?limit=500").then((found) => setRows(found.activity), (failure) => setError(message(failure)));
  }, []);
  const needle = filter.toLowerCase();
  const shown = (rows ?? []).filter((row) => (result === "all" || !row.ok) && `${row.actor} ${row.action} ${row.path}`.toLowerCase().includes(needle));
  return (
    <>
      <PageHeader icon={ScrollText} title="Activity">
        What people and their agents did in the brain, including what was refused.
      </PageHeader>
      {error && <Notice>{error}</Notice>}
      <Section title="Latest 500 events" docs="activity">
        <div className="mb-4 flex flex-wrap gap-3">
          <SearchInput aria-label="Filter activity" placeholder="Filter by person, action or path…" className="min-w-56 flex-1" value={filter} onChange={(event) => setFilter(event.target.value)} />
          <Segmented label="Result" value={result} onChange={setResult} options={[{ id: "all", label: "All" }, { id: "denied", label: "Denied only" }]} />
        </div>
        {rows !== null && shown.length === 0 ? (
          <Empty icon={ScrollText} title="No events match">Activity appears as soon as someone signs in or an agent uses the brain.</Empty>
        ) : (
          <Table head={["When", "Who", "Action", "Path", "Result"]}>
            {shown.map((row, index) => (
              <Tr key={index}>
                <Td><span className="whitespace-nowrap text-muted">{when(row.at)}</span></Td>
                <Td>{row.actor}</Td>
                <Td mono>{row.action}</Td>
                <Td mono>{row.path}</Td>
                <Td>
                  <span className="flex gap-1">
                    <Badge tone={row.ok ? "success" : "danger"}>{row.ok ? "Allowed" : "Denied"}</Badge>
                    {row.versioned === false && <Badge tone="warning" title="The change was saved but could not be added to the version history.">Not in history</Badge>}
                  </span>
                </Td>
              </Tr>
            ))}
          </Table>
        )}
      </Section>
    </>
  );
}

export function Account({ user }: { user: User }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  async function change(event: FormEvent) {
    event.preventDefault();
    try {
      await api("POST", "/api/password", { current, new: next });
      setCurrent("");
      setNext("");
      setResult({ ok: true, text: "Password changed. Your other sessions were signed out." });
    } catch (failure) {
      setResult({ ok: false, text: message(failure) });
    }
  }
  return (
    <>
      <PageHeader icon={UserRound} title="Account">
        Your sign-in for this panel. Harness tokens are managed in <a href="#/connect" className="text-accent hover:underline">Connect a harness</a>.
      </PageHeader>
      <div className="max-w-2xl space-y-5">
        <Section title="Profile">
          <dl className="grid grid-cols-[8rem_1fr] gap-y-2.5">
            <dt className="text-muted">Email</dt>
            <dd>{user.email}</dd>
            <dt className="text-muted">Role</dt>
            <dd>{user.role === "admin" ? <Badge tone="accent">Administrator</Badge> : <Badge>Member</Badge>}</dd>
          </dl>
        </Section>
        <Section title="Password" description="Changing it signs out your other sessions. Tokens keep working.">
          <form onSubmit={change} className="space-y-4">
            <Field label="Current password">
              <Input type="password" autoComplete="current-password" required value={current} onChange={(event) => setCurrent(event.target.value)} />
            </Field>
            <Field label="New password" hint="At least 10 characters.">
              <Input type="password" autoComplete="new-password" required minLength={10} value={next} onChange={(event) => setNext(event.target.value)} />
            </Field>
            {result && <Notice tone={result.ok ? "success" : "danger"}>{result.text}</Notice>}
            <Button type="submit" variant="primary">Change password</Button>
          </form>
        </Section>
      </div>
    </>
  );
}
