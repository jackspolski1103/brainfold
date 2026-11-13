import { Folder, Globe, Lock, Pencil, ShieldCheck, User, Users, X } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useId, useState } from "react";
import { type Listing, type Member, api, baseName, message, tree } from "./api";
import { Badge, Button, Dialog, Empty, Field, Input, Notice, PageHeader, SearchInput, Section, Segmented, Table, Td, Tr } from "./ui";

const GRANT = /^(\*|@[a-z0-9][a-z0-9_-]{0,62}|[^@\s]+@[^@\s]+)$/;
export const isPersonal = (path: string) => /^\/people\/[^/]+/.test(path);

/** People and groups an administrator can pick from when granting access. */
export function useDirectory(admin: boolean): string[] {
  const [names, setNames] = useState<string[]>([]);
  useEffect(() => {
    if (!admin) return;
    Promise.all([api<{ groups: Record<string, string[]> }>("GET", "/api/groups"), api<{ users: Member[] }>("GET", "/api/users")]).then(
      ([groups, users]) => setNames(["*", ...Object.keys(groups.groups).map((name) => `@${name}`), ...users.users.map((user) => user.email)]),
      () => setNames(["*"]),
    );
  }, [admin]);
  return names;
}

export function Grant({ grant, dim, onRemove }: { grant: string; dim?: boolean; onRemove?: () => void }) {
  const Icon = grant === "*" ? Globe : grant.startsWith("@") ? Users : User;
  return (
    <span className={dim ? "opacity-55" : undefined}>
      <Badge tone={grant === "*" ? "warning" : grant.startsWith("@") ? "accent" : "neutral"}>
        <Icon size={11} aria-hidden />
        {grant === "*" ? "Everyone" : grant}
        {onRemove && (
          <button type="button" aria-label={`Remove ${grant}`} onClick={onRemove} className="-mr-0.5 cursor-pointer rounded hover:bg-fg/10">
            <X size={12} aria-hidden />
          </button>
        )}
      </Badge>
    </span>
  );
}

/** What a folder declares, or what it takes from the nearest folder above that declares. */
export function Grants({ value, inherited }: { value: string[] | null | undefined; inherited?: string[] | null }) {
  const shown = value ?? inherited;
  return (
    <span className="flex flex-wrap items-center gap-1">
      {shown == null || shown.length === 0 ? <Badge tone="danger">Nobody</Badge> : shown.map((grant) => <Grant key={grant} grant={grant} dim={value == null} />)}
      {value == null && shown != null && shown.length > 0 && <span className="text-xs text-faint">inherited</span>}
    </span>
  );
}

function GrantInput({ label, value, onChange, suggestions }: { label: string; value: string[]; onChange: (value: string[]) => void; suggestions: string[] }) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const list = useId();
  const add = (raw: string) => {
    const grants = raw.split(/[\s,]+/).filter(Boolean);
    const invalid = grants.find((grant) => !GRANT.test(grant));
    setError(invalid ? `"${invalid}" is not an email, an @group or * for everyone.` : "");
    if (invalid) return;
    onChange([...new Set([...value, ...grants])]);
    setDraft("");
  };
  return (
    <div className="space-y-1.5">
      <div data-invalid={error && draft ? "" : undefined} className="flex min-h-9 flex-wrap items-center gap-1.5 rounded-md border border-line p-1.5 focus-within:border-accent/60 focus-within:ring-2 focus-within:ring-accent/15">
        {value.map((grant) => (
          <Grant key={grant} grant={grant} onRemove={() => onChange(value.filter((item) => item !== grant))} />
        ))}
        <input
          aria-label={label}
          list={list}
          value={draft}
          placeholder={value.length ? "Add another…" : "@group, person@example.com or * for everyone"}
          className="h-6 min-w-40 flex-1 bg-transparent px-1 text-sm outline-none placeholder:text-faint"
          onChange={(event) => (suggestions.includes(event.target.value) ? add(event.target.value) : setDraft(event.target.value))}
          onBlur={() => draft.trim() && add(draft)}
          onKeyDown={(event) => {
            if (["Enter", ",", " "].includes(event.key) && draft.trim()) {
              event.preventDefault();
              add(draft);
            } else if (event.key === "Enter") event.preventDefault();
            else if (event.key === "Backspace" && !draft) onChange(value.slice(0, -1));
          }}
        />
        <datalist id={list}>
          {suggestions.filter((name) => !value.includes(name)).map((name) => (
            <option key={name} value={name}>
              {name === "*" ? "Everyone with an account" : undefined}
            </option>
          ))}
        </datalist>
      </div>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}

function AccessForm({ listing, suggestions, onClose, onSaved }: { listing: Listing; suggestions: string[]; onClose: () => void; onSaved: () => void }) {
  const root = listing.path === "/";
  const [description, setDescription] = useState(listing.description);
  const [read, setRead] = useState<string[] | null>(listing.read ?? null);
  const [write, setWrite] = useState<string[] | null>(listing.write ?? null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(event: FormEvent) {
    event.preventDefault();
    if ((event.target as HTMLElement).querySelector("[data-invalid]")) return; // a name still to fix
    setBusy(true);
    try {
      await api("PUT", "/api/folder", { path: listing.path, description, start_here: listing.guide ?? [], read, write });
      onSaved();
      onClose();
    } catch (failure) {
      setError(message(failure));
      setBusy(false);
    }
  }

  const rule = (label: string, hint: string, value: string[] | null, setValue: (value: string[] | null) => void) => (
    <fieldset className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <legend className="float-left text-sm font-medium">{label}</legend>
        <Segmented
          label={`${label} rule`}
          value={value === null ? "inherit" : "declare"}
          onChange={(mode) => setValue(mode === "inherit" ? null : [])}
          options={[
            { id: "inherit", label: root ? "Nobody" : "Same as the folder above" },
            { id: "declare", label: "Chosen people" },
          ]}
        />
      </div>
      {value !== null && <GrantInput label={`${label} list`} value={value} onChange={setValue} suggestions={suggestions} />}
      <p className="text-xs text-faint">{hint}</p>
    </fieldset>
  );

  return (
    <form onSubmit={save} className="space-y-5">
      <Field label="Description" hint="The first thing an agent reads when it enters this folder.">
        <Input value={description} maxLength={500} onChange={(event) => setDescription(event.target.value)} />
      </Field>
      {rule("Who can read", "Reading also needs every folder above to allow it: a folder can only narrow what its parents grant.", read, setRead)}
      {rule("Who can write", "Writing follows the nearest folder that declares it, and always requires being able to read.", write, setWrite)}
      {error && <Notice>{error}</Notice>}
      <div className="flex justify-end gap-2 pt-1">
        <Button variant="ghost" onClick={onClose}>Cancel</Button>
        <Button type="submit" variant="primary" disabled={busy}>Save access</Button>
      </div>
    </form>
  );
}

export function AccessDialog({ path, suggestions, onClose, onSaved }: { path: string | null; suggestions: string[]; onClose: () => void; onSaved: () => void }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setListing(null);
    setError("");
    if (path) tree(path).then(setListing, (failure) => setError(message(failure)));
  }, [path]);
  return (
    <Dialog open={path !== null} onClose={onClose} title="Folder access" description={<code className="font-mono text-xs">{path}</code>}>
      {error && <Notice>{error}</Notice>}
      {!listing && !error && <p className="text-sm text-faint">Loading…</p>}
      {listing && <AccessForm listing={listing} suggestions={suggestions} onClose={onClose} onSaved={onSaved} />}
    </Dialog>
  );
}

type Row = { path: string; depth: number; description: string; read?: string[] | null; write?: string[] | null };
const LIMIT = 300;

// ponytail: one request per folder, capped at LIMIT; add a server route that returns the
// whole folder tree when brains outgrow it.
async function walk(): Promise<{ rows: Row[]; capped: boolean }> {
  const root = await tree("/");
  const rows: Row[] = [{ path: "/", depth: 0, description: root.description, read: root.read, write: root.write }];
  const visit = async (listing: Listing, depth: number) => {
    for (const entry of listing.entries) {
      if (entry.kind !== "directory" || rows.length >= LIMIT) continue;
      rows.push({ path: entry.path, depth, description: entry.description ?? "", read: entry.read, write: entry.write });
      if (!isPersonal(entry.path)) await visit(await tree(entry.path), depth + 1);
    }
  };
  await visit(root, 1);
  return { rows, capped: rows.length >= LIMIT };
}

export function AccessPage() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [capped, setCapped] = useState(false);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [error, setError] = useState("");
  const suggestions = useDirectory(true);
  const load = useCallback(() => {
    walk().then(
      (result) => {
        setRows(result.rows);
        setCapped(result.capped);
      },
      (failure) => setError(message(failure)),
    );
  }, []);
  useEffect(load, [load]);

  // The nearest folder above that declares a rule is the one a silent folder follows.
  const nearest = (row: Row, key: "read" | "write") => {
    let path = row.path;
    while (path !== "/") {
      path = `/${path.split("/").filter(Boolean).slice(0, -1).join("/")}`;
      const above = rows?.find((item) => item.path === path);
      if (above?.[key] != null) return above[key];
    }
    return null;
  };
  const needle = filter.trim().toLowerCase();
  const shown = (rows ?? []).filter((row) =>
    `${row.path} ${row.description} ${(row.read ?? nearest(row, "read") ?? []).join(" ")} ${(row.write ?? nearest(row, "write") ?? []).join(" ")}`.toLowerCase().includes(needle),
  );

  return (
    <>
      <PageHeader icon={ShieldCheck} title="Access">
        Decide who reads and who writes each folder of the brain. Agents get exactly the access of the person whose token they use.
      </PageHeader>
      {error && <Notice>{error}</Notice>}
      <div className="space-y-5">
        <Section
          title="Folders"
          docs="permissions"
          description="Every folder of the brain with the people and groups it grants. Pick a folder to change it."
        >
          <SearchInput aria-label="Filter folders" placeholder="Filter by folder, person or group…" className="mb-4" value={filter} onChange={(event) => setFilter(event.target.value)} />
          {rows === null && !error && <p className="py-6 text-center text-sm text-faint">Reading the brain…</p>}
          {rows !== null && shown.length === 0 && <Empty icon={Folder} title="No folder matches">Try a shorter filter.</Empty>}
          {shown.length > 0 && (
            <Table head={["Folder", "Read", "Write", ""]}>
              {shown.map((row) => {
                const personal = isPersonal(row.path);
                return (
                  <Tr key={row.path} onClick={personal ? undefined : () => setEditing(row.path)}>
                    <Td>
                      <span className="flex items-center gap-2" style={{ paddingLeft: needle ? 0 : row.depth * 18 }}>
                        <Folder size={15} className="shrink-0 text-accent" aria-hidden />
                        <span className="font-medium whitespace-nowrap">{needle ? row.path : row.path === "/" ? "Brain (root)" : baseName(row.path)}</span>
                        <span className="hidden max-w-72 truncate text-xs text-faint xl:inline">{row.description}</span>
                      </span>
                    </Td>
                    {personal ? (
                      <td colSpan={2} className="px-4 text-xs text-faint">
                        <span className="flex items-center gap-1.5"><Lock size={12} aria-hidden /> Personal folder: only its owner reads and writes it</span>
                      </td>
                    ) : (
                      <>
                        <Td><Grants value={row.read} inherited={nearest(row, "read")} /></Td>
                        <Td><Grants value={row.write} inherited={nearest(row, "write")} /></Td>
                      </>
                    )}
                    <Td className="w-px text-right">
                      {!personal && (
                        <Button size="sm" variant="ghost" aria-label={`Edit access of ${row.path}`} onClick={(event) => { event.stopPropagation(); setEditing(row.path); }}>
                          <Pencil size={13} aria-hidden /> Edit
                        </Button>
                      )}
                    </Td>
                  </Tr>
                );
              })}
            </Table>
          )}
          {capped && <p className="pt-3 text-xs text-faint">Showing the first {LIMIT} folders. Open a folder in the Brain section to edit the rest.</p>}
        </Section>
        <Section title="How access is decided">
          <ul className="list-disc space-y-1.5 pl-5 text-muted">
            <li><span className="text-fg">Nothing is open by default.</span> A folder is readable only when it, or a folder above it, grants read.</li>
            <li><span className="text-fg">Read narrows down the tree.</span> A folder that declares read keeps only those people for everything below it.</li>
            <li><span className="text-fg">Write follows the nearest declaration.</span> A folder that says nothing takes the rule of the closest folder above.</li>
            <li><span className="text-fg">Administrators manage, they do not read.</span> You see every folder and its rules here, but not content you were not granted.</li>
          </ul>
        </Section>
      </div>
      <AccessDialog path={editing} suggestions={suggestions} onClose={() => setEditing(null)} onSaved={load} />
    </>
  );
}
