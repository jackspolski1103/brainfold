import { ChevronRight, Download, File as FileIcon, FileText, Folder, FolderOpen, FolderTree, Home, Pencil, Sparkles, Upload } from "lucide-react";
import { type DragEvent, type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AccessDialog, Grants, isPersonal, useDirectory } from "./Access";
import { ApiError, type Entry, type FileView, type Hit, type Listing, api, baseName, bytes, fileUrl, message, parent, tree, upload } from "./api";
import { Badge, Button, Code, Dialog, Empty, Field, Input, Markdown, Notice, SearchInput, Section, Segmented, Table, Td, Tr, button, cx } from "./ui";

const isFile = (path: string) => /\.[a-z0-9]+$/i.test(path);
const link = (path: string, kind?: string) => `#/${(kind ? kind === "file" : isFile(path)) ? "file" : "brain"}${path}`;

function Node({ entry, depth, current }: { entry: Entry; depth: number; current: string }) {
  const folder = entry.kind === "directory";
  const inside = folder && (current === entry.path || current.startsWith(`${entry.path}/`));
  const [open, setOpen] = useState(inside);
  const [children, setChildren] = useState<Entry[] | null>(null);
  useEffect(() => {
    if (inside) setOpen(true);
  }, [inside]);
  useEffect(() => {
    if (open && folder && children === null) tree(entry.path).then((listing) => setChildren(listing.entries), () => setChildren([]));
  }, [open, folder, children, entry.path]);
  const selected = current === entry.path;
  const Icon = folder ? (open ? FolderOpen : Folder) : baseName(entry.path) === "SKILL.md" ? Sparkles : FileText;
  return (
    <li>
      <div className={cx("flex h-8 items-center rounded pr-2", selected ? "bg-fg/10" : "hover:bg-fg/5")} style={{ paddingLeft: depth * 14 + 4 }}>
        {folder ? (
          <button type="button" aria-label={`${open ? "Collapse" : "Expand"} ${baseName(entry.path)}`} aria-expanded={open} onClick={() => setOpen(!open)} className="flex h-6 w-5 shrink-0 cursor-pointer items-center justify-center text-faint hover:text-fg">
            <ChevronRight size={14} className={cx("transition-transform", open && "rotate-90")} aria-hidden />
          </button>
        ) : (
          <span className="w-5 shrink-0" />
        )}
        <a href={link(entry.path, entry.kind === "file" ? "file" : "folder")} aria-current={selected ? "page" : undefined} className={cx("flex min-w-0 flex-1 items-center gap-2 text-sm", selected ? "text-fg" : "text-muted")}>
          <Icon size={15} className={cx("shrink-0", folder ? "text-accent" : "text-faint")} aria-hidden />
          <span className="truncate">{baseName(entry.path)}</span>
        </a>
      </div>
      {open && children && children.length > 0 && (
        <ul>
          {children.map((child) => (
            <Node key={child.path} entry={child} depth={depth + 1} current={current} />
          ))}
        </ul>
      )}
    </li>
  );
}

function Tree({ current }: { current: string }) {
  const [entries, setEntries] = useState<Entry[] | null>(null);
  useEffect(() => {
    tree("/").then((listing) => setEntries(listing.entries), () => setEntries([]));
  }, []);
  return (
    <nav aria-label="Brain folders" className="rounded-lg border border-line bg-card p-2">
      <a href="#/brain/" aria-current={current === "/" ? "page" : undefined} className={cx("flex h-8 items-center gap-2 rounded px-2 text-sm", current === "/" ? "bg-fg/10" : "text-muted hover:bg-fg/5")}>
        <Home size={15} className="text-accent" aria-hidden /> Brain
      </a>
      <ul>
        {(entries ?? []).map((entry) => (
          <Node key={entry.path} entry={entry} depth={1} current={current} />
        ))}
      </ul>
      {entries?.length === 0 && <p className="px-2 py-3 text-xs text-faint">Nothing you can read yet.</p>}
    </nav>
  );
}

function Crumbs({ path }: { path: string }) {
  const parts = path.split("/").filter(Boolean);
  return (
    <nav aria-label="Path" className="flex min-w-0 flex-wrap items-center gap-1 text-sm text-muted">
      <a href="#/brain/" className="hover:text-fg">Brain</a>
      {parts.map((part, index) => (
        <span key={index} className="flex items-center gap-1">
          <ChevronRight size={13} className="text-faint" aria-hidden />
          <a href={link(`/${parts.slice(0, index + 1).join("/")}`, index === parts.length - 1 ? undefined : "folder")} className={cx("hover:text-fg", index === parts.length - 1 && "text-fg")}>
            {part}
          </a>
        </span>
      ))}
    </nav>
  );
}

/** A relative link inside a brain file points to another brain path, never outside. */
const resolver = (file: string) => (href: string) => {
  if (/^[a-z][a-z0-9+.-]*:|^#/i.test(href)) return href;
  const parts = href.startsWith("/") ? [] : file.split("/").filter(Boolean).slice(0, -1);
  for (const part of href.split("#")[0].split("/")) {
    if (part === "..") parts.pop();
    else if (part && part !== ".") parts.push(part);
  }
  return link(`/${parts.join("/")}`);
};

// The stamp the server puts before each entry appended to a LEARNINGS.md.
const STAMP = /<!-- brainfold:learning (\S+) (\S+) -->/g;

function FileCard({ file }: { file: FileView }) {
  const markdown = file.kind === "text" && /\.(md|markdown)$/i.test(file.path);
  const [view, setView] = useState<"rendered" | "source">("rendered");
  const resolve = useMemo(() => resolver(file.path), [file.path]);
  const [, front, body] = /^---\n([\s\S]*?)\n---\n?([\s\S]*)$/.exec(file.content ?? "") ?? [null, "", file.content ?? ""];
  return (
    <Section
      title={baseName(file.path)}
      description={<span className="font-mono text-xs text-faint">{bytes(file.size)} · version {file.version.slice(0, 12)}</span>}
      action={
        <span className="flex flex-wrap items-center gap-2">
          {markdown && <Segmented label="View" value={view} onChange={setView} options={[{ id: "rendered", label: "Rendered" }, { id: "source", label: "Source" }]} />}
          <a href={fileUrl(file.path)} download className={button("primary")}><Download size={15} aria-hidden /> Download</a>
        </span>
      }
    >
      {file.kind !== "text" ? (
        <div className="space-y-3">
          <p className="text-muted">This file is not text, so the panel does not show it. Download it, or let an agent fetch it from a terminal:</p>
          <Code title="Terminal" text={file.fetch ?? ""} />
        </div>
      ) : markdown && view === "rendered" ? (
        <div className="border-t border-line pt-5">
          {front && <pre className="mb-5 overflow-x-auto rounded-md border border-line bg-panel p-3 font-mono text-xs leading-5 text-muted">{front}</pre>}
          <Markdown text={body.replace(STAMP, (_, at, who) => `\n\n---\n\n**${who}** · ${new Date(at).toLocaleString()}\n\n`)} link={resolve} />
        </div>
      ) : (
        <pre className="max-h-[70vh] overflow-auto rounded-md border border-line bg-panel p-4 font-mono text-[13px] leading-6 whitespace-pre-wrap break-words">{file.content}</pre>
      )}
      {file.truncated && <p className="pt-3 text-xs text-faint">Showing the first part of a long file.</p>}
    </Section>
  );
}

const LIMIT = 25 * 1024 * 1024; // the server's limit for one file

type Note = { ok: boolean; text: string; path?: string };

function DescribeDialog({ path, current, onClose, onSaved }: { path: string | null; current: string; onClose: () => void; onSaved: () => void }) {
  const [text, setText] = useState(current);
  const [error, setError] = useState("");
  useEffect(() => {
    setText(current);
    setError("");
  }, [path, current]);
  async function save(event: FormEvent) {
    event.preventDefault();
    try {
      await api("PUT", "/api/describe", { path, description: text });
      onSaved();
      onClose();
    } catch (failure) {
      setError(message(failure));
    }
  }
  return (
    <Dialog open={path !== null} onClose={onClose} title="Describe this file" description={<code className="font-mono text-xs">{path}</code>}>
      <form onSubmit={save} className="space-y-4">
        <Field label="What is it?" hint="One line. Agents and people see it next to the file, before opening it. Leave it empty to remove it.">
          <Input autoFocus maxLength={300} placeholder="Employee handbook, 2026 edition." value={text} onChange={(event) => setText(event.target.value)} />
        </Field>
        {error && <Notice>{error}</Notice>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>Not now</Button>
          <Button type="submit" variant="primary">Save description</Button>
        </div>
      </form>
    </Dialog>
  );
}

function FolderView({ listing, admin, onEdit, onChanged }: { listing: Listing; admin: boolean; onEdit: () => void; onChanged: () => void }) {
  const root = listing.path === "/";
  const picker = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState("");
  const [notes, setNotes] = useState<Note[]>([]);
  const [over, setOver] = useState(false);
  const [describing, setDescribing] = useState<string | null>(null);

  async function send(files: File[]) {
    const done: Note[] = [];
    for (const [index, file] of files.entries()) {
      setBusy(`Uploading ${file.name} (${index + 1} of ${files.length})…`);
      const path = `${root ? "" : listing.path}/${file.name}`;
      try {
        if (file.size > LIMIT) throw new ApiError("file_too_large", "The file is over the 25 MB limit.");
        try {
          await upload(path, file);
        } catch (failure) {
          const exists = failure instanceof ApiError && failure.code === "already_exists";
          if (!exists) throw failure;
          if (!confirm(`${file.name} already exists in this folder. Replace it? The current version stays in the history.`)) {
            done.push({ ok: false, text: `${file.name}: kept the existing file.` });
            continue;
          }
          const current = await api<FileView>("GET", `/api/file?path=${encodeURIComponent(path)}`);
          await upload(path, file, current.version);
        }
        done.push({ ok: true, text: `${file.name} uploaded (${bytes(file.size)}).`, path });
      } catch (failure) {
        done.push({ ok: false, text: `${file.name}: ${message(failure)}` });
      }
    }
    setBusy("");
    setNotes(done);
    if (picker.current) picker.current.value = "";
    onChanged();
    // One new file: ask what it is right away. Several: each note offers it.
    const stored = done.filter((note) => note.path);
    const known = listing.entries.find((entry) => entry.path === stored[0]?.path)?.description;
    if (stored.length === 1 && !known) setDescribing(stored[0].path ?? null);
  }
  const drop = (event: DragEvent) => {
    if (!listing.can_write || !event.dataTransfer.types.includes("Files")) return;
    event.preventDefault();
    setOver(event.type === "dragover");
    if (event.type === "drop") void send([...event.dataTransfer.files]);
  };
  const uploadButton = listing.can_write && (
    <Button variant="primary" disabled={!!busy} onClick={() => picker.current?.click()}><Upload size={15} aria-hidden /> Upload files</Button>
  );

  return (
    <div onDragOver={drop} onDragLeave={drop} onDrop={drop} className={cx("space-y-4 rounded-lg", over && "outline-2 outline-offset-4 outline-accent outline-dashed")}>
      <input ref={picker} type="file" multiple hidden aria-label="Files to upload" onChange={(event) => event.target.files?.length && void send([...event.target.files])} />
      <Section
        title={root ? "Brain" : baseName(listing.path)}
        description={listing.description || <span className="text-faint">{listing.home ? "No shared folder has been granted to you yet. Ask an administrator for access; meanwhile your personal folder works." : "No description yet. Agents see this text first when they enter the folder."}</span>}
        action={<Badge tone={listing.can_write ? "success" : "neutral"}>{listing.can_write ? "You can write here" : "Read only for you"}</Badge>}
      >
        <div className="space-y-3">
          {listing.home && (
            <p>
              <a href={`#/brain${listing.home}`} className="text-accent hover:underline">Your personal folder</a>
              <span className="text-faint"> · only you can read or write it</span>
            </p>
          )}
          {listing.start_here.length > 0 && (
            <p className="flex flex-wrap items-center gap-2">
              <span className="text-faint">Start here</span>
              {listing.start_here.map((item) => (
                <a key={item} href={link(item)} className="inline-flex h-[22px] items-center rounded border border-accent/10 bg-accent/15 px-1.5 text-xs text-accent hover:bg-accent/25">
                  {item.slice(root ? 1 : listing.path.length + 1)}
                </a>
              ))}
            </p>
          )}
          {admin && (
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-line pt-3">
              {isPersonal(listing.path) ? (
                <span className="text-faint">Personal folder: only its owner reads and writes it.</span>
              ) : (
                <>
                  {(["read", "write"] as const).map((key) => (
                    <span key={key} className="flex items-center gap-2">
                      <span className="text-faint capitalize">{key}</span>
                      {listing[key] == null && !root ? <Badge>Same as the folder above</Badge> : <Grants value={listing[key]} />}
                    </span>
                  ))}
                  <Button size="sm" className="ml-auto" onClick={onEdit}><Pencil size={13} aria-hidden /> Edit access</Button>
                </>
              )}
            </div>
          )}
        </div>
      </Section>
      {listing.can_write && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-faint" role="status">{busy || "Drop files anywhere on this folder to add them, up to 25 MB each."}</p>
          {uploadButton}
        </div>
      )}
      {notes.map((note) => (
        <Notice key={note.text} tone={note.ok ? "success" : "danger"}>
          {note.text}{" "}
          {note.path && <button type="button" onClick={() => setDescribing(note.path ?? null)} className="cursor-pointer underline">Describe it</button>}
        </Notice>
      ))}
      {listing.entries.length === 0 ? (
        <Empty icon={FolderOpen} title="This folder is empty">Agents create files and folders here through the brain's tools, wherever their person can write.</Empty>
      ) : (
        <Table head={["Name", "About", "Size", ...(admin ? ["Declared access"] : []), ""]}>
          {listing.entries.map((entry) => (
            <Tr key={entry.path} onClick={() => (location.hash = link(entry.path, entry.kind === "file" ? "file" : "folder"))}>
              <Td>
                <a href={link(entry.path, entry.kind === "file" ? "file" : "folder")} className="flex items-center gap-2 font-medium whitespace-nowrap hover:underline">
                  {entry.kind === "directory" ? <Folder size={15} className="text-accent" aria-hidden /> : <FileIcon size={15} className="text-faint" aria-hidden />}
                  {baseName(entry.path)}
                </a>
              </Td>
              <Td><span className="text-muted">{entry.description}</span></Td>
              <Td><span className="font-mono text-xs whitespace-nowrap text-faint">{entry.size == null ? "" : bytes(entry.size)}</span></Td>
              {admin && (
                <Td>
                  {entry.kind === "directory" && (entry.read || entry.write) && (
                    <span className="flex flex-wrap gap-1">
                      {[...new Set([...(entry.read ?? []), ...(entry.write ?? [])])].map((grant) => <Badge key={grant}>{grant === "*" ? "Everyone" : grant}</Badge>)}
                    </span>
                  )}
                </Td>
              )}
              <Td className="w-px text-right whitespace-nowrap">
                {entry.size != null && listing.can_write && (
                  <Button size="icon" variant="ghost" aria-label={`Describe ${baseName(entry.path)}`} title="Describe" onClick={(event) => { event.stopPropagation(); setDescribing(entry.path); }}>
                    <Pencil size={14} aria-hidden />
                  </Button>
                )}
                {entry.size != null && (
                  <a href={fileUrl(entry.path)} download aria-label={`Download ${baseName(entry.path)}`} title="Download" onClick={(event) => event.stopPropagation()} className={button("ghost", "icon")}>
                    <Download size={14} aria-hidden />
                  </a>
                )}
              </Td>
            </Tr>
          ))}
        </Table>
      )}
      {listing.truncated && <p className="text-xs text-faint">Showing the first 256 entries.</p>}
      <DescribeDialog path={describing} current={listing.entries.find((entry) => entry.path === describing)?.description ?? ""} onClose={() => setDescribing(null)} onSaved={onChanged} />
    </div>
  );
}

export function Brain({ admin, kind, path }: { admin: boolean; kind: "folder" | "file"; path: string }) {
  const current = path.length > 1 ? path.replace(/\/$/, "") : "/";
  const [listing, setListing] = useState<Listing | null>(null);
  const [file, setFile] = useState<FileView | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [shown, setShown] = useState(0); // bumped after an upload so the tree reads again
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<{ query: string; hits: Hit[]; truncated: boolean } | null>(null);
  const suggestions = useDirectory(admin);
  const load = useCallback(() => {
    setError("");
    setListing(null);
    setFile(null);
    setHits(null);
    const request = kind === "folder" ? tree(current).then(setListing) : api<FileView>("GET", `/api/file?path=${encodeURIComponent(current)}`).then(setFile);
    request.catch((failure) => setError(failure instanceof ApiError && failure.code === "unavailable" ? "This path does not exist or you cannot read it." : "The brain could not be loaded."));
  }, [kind, current]);
  useEffect(load, [load]);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return setHits(null);
    try {
      const found = await api<{ hits: Hit[]; truncated: boolean }>("GET", `/api/search?q=${encodeURIComponent(query)}`);
      setHits({ query, ...found });
    } catch {
      setHits({ query, hits: [], truncated: false });
    }
  }

  return (
    <>
      <header className="mb-6 flex flex-wrap items-center gap-x-6 gap-y-3">
        <div className="flex items-center gap-3">
          <FolderTree size={26} strokeWidth={1.6} className="text-accent" aria-hidden />
          <h1 className="text-2xl underline decoration-accent/90 underline-offset-4">Brain</h1>
        </div>
        <form onSubmit={search} className="min-w-56 flex-1">
          <SearchInput aria-label="Search the brain" placeholder="Search the text of every file you can read…" value={query} onChange={(event) => setQuery(event.target.value)} />
        </form>
      </header>
      <div className="flex items-start gap-6">
        <aside className="sticky top-0 hidden max-h-[calc(100vh-7rem)] w-72 shrink-0 overflow-y-auto lg:block">
          <Tree key={shown} current={current} />
        </aside>
        <div className="min-w-0 flex-1 space-y-4">
          {hits ? (
            <Section
              title={`Results for "${hits.query}"`}
              description={`${hits.hits.length}${hits.truncated ? "+" : ""} matching lines in files you can read.`}
              action={<Button size="sm" onClick={() => { setHits(null); setQuery(""); }}>Clear search</Button>}
            >
              {hits.hits.length === 0 ? (
                <Empty title="Nothing matches">Search looks at the text of files, line by line.</Empty>
              ) : (
                <Table head={["File", "Line", "Text"]}>
                  {hits.hits.map((hit, index) => (
                    <Tr key={index} onClick={() => (location.hash = `#/file${hit.path}`)}>
                      <Td mono><a href={`#/file${hit.path}`} className="whitespace-nowrap hover:underline">{hit.path}</a></Td>
                      <Td mono>{hit.line}</Td>
                      <Td><span className="text-muted">{hit.text}</span></Td>
                    </Tr>
                  ))}
                </Table>
              )}
            </Section>
          ) : (
            <>
              <Crumbs path={current} />
              {error && <Notice>{error} <a href={`#/brain${parent(current)}`} className="underline">Go up</a></Notice>}
              {listing && <FolderView key={listing.path} listing={listing} admin={admin} onEdit={() => setEditing(true)} onChanged={() => { void tree(current).then(setListing); setShown((count) => count + 1); }} />}
              {file && <FileCard file={file} />}
            </>
          )}
        </div>
      </div>
      <AccessDialog path={editing ? current : null} suggestions={suggestions} onClose={() => setEditing(false)} onSaved={load} />
    </>
  );
}
