import { ChevronRight, File as FileIcon, Folder, Lock } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, type FileView, type Listing, api } from "./api";
import { Badge, Button, Card, Copyable, Field, Input, Notice, Table, Td } from "./ui";

const GRANT = /^(\*|@[a-z0-9][a-z0-9_-]{0,62}|[^@\s]+@[^@\s]+)$/;
const name = (path: string) => path.split("/").filter(Boolean).pop() ?? "/";
const parse = (text: string) => text.split(/[\s,]+/).filter(Boolean);

function Crumbs({ path }: { path: string }) {
  const parts = path.split("/").filter(Boolean);
  return (
    <nav aria-label="Path" className="flex flex-wrap items-center gap-1 text-sm">
      <a href="#/brain/" className="font-medium hover:underline">brain</a>
      {parts.map((part, index) => (
        <span key={index} className="flex items-center gap-1">
          <ChevronRight size={14} className="text-zinc-400" aria-hidden />
          <a href={`#/brain/${parts.slice(0, index + 1).join("/")}`} className="hover:underline">{part}</a>
        </span>
      ))}
    </nav>
  );
}

function Grants({ label, value, root }: { label: string; value: string[] | null | undefined; root: boolean }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-sm">
      <span className="w-12 text-zinc-500">{label}</span>
      {value == null ? (root ? <Badge tone="red">nobody</Badge> : <Badge>inherited</Badge>) : value.length === 0 ? <Badge tone="red">nobody</Badge> : value.map((grant) => <Badge key={grant} tone="green">{grant}</Badge>)}
    </div>
  );
}

function Access({ listing, onSaved }: { listing: Listing; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [description, setDescription] = useState(listing.description);
  const [inheritRead, setInheritRead] = useState(listing.read == null);
  const [inheritWrite, setInheritWrite] = useState(listing.write == null);
  const [read, setRead] = useState((listing.read ?? []).join(", "));
  const [write, setWrite] = useState((listing.write ?? []).join(", "));
  const [error, setError] = useState("");
  const personal = /^\/people\/[^/]+/.test(listing.path);

  async function save(event: FormEvent) {
    event.preventDefault();
    const invalid = [...(inheritRead ? [] : parse(read)), ...(inheritWrite ? [] : parse(write))].find((grant) => !GRANT.test(grant));
    if (invalid) return setError(`"${invalid}" is not an email, an @group or *.`);
    try {
      await api("PUT", "/api/folder", {
        path: listing.path,
        description,
        start_here: listing.guide ?? [],
        read: inheritRead ? null : parse(read),
        write: inheritWrite ? null : parse(write),
      });
      setEditing(false);
      onSaved();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "The change was not saved.");
    }
  }

  if (personal) return <Card title="Access"><p className="text-sm text-zinc-500">Personal folder: only its owner can read or write it.</p></Card>;
  if (!editing)
    return (
      <Card title="Access" action={<Button variant="outline" onClick={() => setEditing(true)}>Edit</Button>}>
        <div className="space-y-2">
          <Grants label="Read" value={listing.read} root={listing.path === "/"} />
          <Grants label="Write" value={listing.write} root={listing.path === "/"} />
          <p className="pt-1 text-xs text-zinc-500">Read narrows down the tree. Write follows the nearest folder that declares it.</p>
        </div>
      </Card>
    );
  const list = (label: string, inherit: boolean, setInherit: (value: boolean) => void, value: string, setValue: (value: string) => void) => (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{label}</legend>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={inherit} onChange={(e) => setInherit(e.target.checked)} /> {listing.path === "/" ? "Nobody (nothing declared at the root)" : "Inherit from the parent folder"}
      </label>
      {!inherit && <Input aria-label={`${label} list`} placeholder="@group, person@example.com, *" value={value} onChange={(e) => setValue(e.target.value)} />}
    </fieldset>
  );
  return (
    <Card title="Access">
      <form onSubmit={save} className="space-y-4">
        <Field label="Description" hint="What agents read first when they enter this folder.">
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        {list("Read", inheritRead, setInheritRead, read, setRead)}
        {list("Write", inheritWrite, setInheritWrite, write, setWrite)}
        {error && <Notice>{error}</Notice>}
        <div className="flex gap-2">
          <Button type="submit">Save</Button>
          <Button type="button" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
        </div>
      </form>
    </Card>
  );
}

export function Brain({ admin, kind, path }: { admin: boolean; kind: "folder" | "file"; path: string }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [file, setFile] = useState<FileView | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    setListing(null);
    setFile(null);
    const query = `?path=${encodeURIComponent(path || "/")}`;
    const request = kind === "folder" ? api<Listing>("GET", `/api/tree${query}`).then(setListing) : api<FileView>("GET", `/api/file${query}`).then(setFile);
    request.catch((failure) => setError(failure instanceof ApiError && failure.code === "unavailable" ? "This path does not exist or you cannot read it." : "The brain could not be loaded."));
  }, [kind, path]);
  useEffect(load, [load]);

  return (
    <>
      <Crumbs path={path} />
      {error && <Notice>{error}</Notice>}
      {listing && (
        <>
          <Card title={name(listing.path)}>
            <p className="text-sm">{listing.description || <span className="text-zinc-500">No description yet.</span>}</p>
            {listing.home && (
              <p className="mt-3 text-sm">
                <a href={`#/brain${listing.home}`} className="font-medium text-blue-700 hover:underline dark:text-blue-300">Your personal folder</a>
                <span className="text-zinc-500"> · only you can read or write it</span>
              </p>
            )}
            {listing.start_here.length > 0 && (
              <p className="mt-3 flex flex-wrap items-center gap-2 text-sm">
                <span className="text-zinc-500">Start here</span>
                {listing.start_here.map((item) => (
                  <a key={item} href={`#/${/\.[a-z0-9]+$/i.test(item) ? "file" : "brain"}${item}`} className="rounded bg-blue-50 px-1.5 py-0.5 text-blue-800 hover:underline dark:bg-blue-950 dark:text-blue-200">
                    {item.slice(listing.path === "/" ? 1 : listing.path.length + 1)}
                  </a>
                ))}
              </p>
            )}
          </Card>
          <Card>
            <Table head={["Name", "About", admin ? "Declared access" : ""]} empty={listing.entries.length === 0}>
              {listing.entries.map((entry) => (
                <tr key={entry.path}>
                  <Td>
                    <a href={`#/${entry.kind === "directory" ? "brain" : "file"}${entry.path}`} className="flex items-center gap-2 font-medium hover:underline">
                      {entry.kind === "directory" ? <Folder size={16} className="text-blue-600" aria-hidden /> : <FileIcon size={16} className="text-zinc-400" aria-hidden />}
                      {name(entry.path)}
                    </a>
                  </Td>
                  <Td><span className="text-zinc-500">{entry.description}</span></Td>
                  <Td>
                    {admin && entry.kind === "directory" && (entry.read || entry.write) && (
                      <span className="flex flex-wrap items-center gap-1"><Lock size={12} className="text-zinc-400" aria-hidden />{[...(entry.read ?? []), ...(entry.write ?? [])].filter((grant, index, all) => all.indexOf(grant) === index).map((grant) => <Badge key={grant}>{grant}</Badge>)}</span>
                    )}
                  </Td>
                </tr>
              ))}
            </Table>
            {listing.truncated && <p className="px-3 pt-3 text-xs text-zinc-500">Showing the first 256 entries.</p>}
          </Card>
          {admin && <Access key={listing.path + JSON.stringify([listing.read, listing.write, listing.description])} listing={listing} onSaved={load} />}
        </>
      )}
      {file && (
        <Card title={name(file.path)} action={<span className="text-xs text-zinc-500">{file.size.toLocaleString()} bytes · version {file.version.slice(0, 12)}</span>}>
          {file.kind === "text" ? (
            <>
              <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap break-words font-mono text-sm leading-relaxed">{file.content}</pre>
              {file.truncated && <p className="pt-3 text-xs text-zinc-500">Showing the first part of a long file.</p>}
            </>
          ) : (
            <div className="space-y-3">
              <p className="text-sm">This file is not text. The panel does not download files; fetch it from a terminal:</p>
              <Copyable text={file.fetch ?? ""} />
            </div>
          )}
        </Card>
      )}
    </>
  );
}
