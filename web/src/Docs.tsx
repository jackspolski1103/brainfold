import { ArrowLeft, ArrowRight, Menu as MenuIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Markdown, SearchInput, cx, slug } from "./ui";

const pages = import.meta.glob<string>("./docs/*.md", { query: "?raw", import: "default", eager: true });
const text = (name: string) => pages[`./docs/${name}.md`] ?? "";

const NAV: { group: string; items: [string, string][] }[] = [
  { group: "Get started", items: [["introduction", "What is Brainfold?"], ["quickstart", "Quickstart"], ["connect", "Connect a harness"]] },
  { group: "Concepts", items: [["folders", "Folders and guidance"], ["permissions", "Permissions"], ["skills", "Skills and learnings"], ["history", "Versions, history and restore"], ["files", "Files of any type"]] },
  { group: "Administration", items: [["members", "Members and groups"], ["activity", "Activity"]] },
  { group: "Self-hosting", items: [["deploy", "Run it for your team"], ["configuration", "Configuration"], ["durability", "Durability and recovery"]] },
  { group: "Reference", items: [["tools", "MCP tools"], ["cli", "Command line"]] },
];
const ORDER = NAV.flatMap((section) => section.items);

export function Docs({ page }: { page: string }) {
  const current = ORDER.some(([name]) => name === page) ? page : "introduction";
  const index = ORDER.findIndex(([name]) => name === current);
  const source = text(current);
  const [query, setQuery] = useState("");
  const [menu, setMenu] = useState(false);
  const headings = useMemo(() => [...source.matchAll(/^## (.+)$/gm)].map((match) => match[1]), [source]);
  useEffect(() => {
    document.getElementById("docs-content")?.scrollTo(0, 0);
    setMenu(false);
  }, [current]);

  const needle = query.trim().toLowerCase();
  const found = needle
    ? ORDER.filter(([name, title]) => `${title} ${text(name)}`.toLowerCase().includes(needle)).map(([name, title]) => {
        const line = text(name).split("\n").find((row) => row.toLowerCase().includes(needle) && !row.startsWith("#")) ?? "";
        return { name, title, line: line.replace(/[`*|>#]/g, "").trim().slice(0, 140) };
      })
    : null;

  return (
    <div className="flex min-h-0 flex-1">
      <aside className={cx("w-[255px] shrink-0 overflow-y-auto border-r border-shell px-3 py-5 md:block", menu ? "absolute inset-y-12 left-0 z-20 block bg-bg" : "hidden")}>
        <SearchInput aria-label="Search the documentation" placeholder="Search docs…" className="mb-5" value={query} onChange={(event) => setQuery(event.target.value)} />
        {NAV.map((section) => (
          <div key={section.group} className="mb-5">
            <p className="mb-1 px-3 text-xs font-medium tracking-wide text-faint">{section.group}</p>
            {section.items.map(([name, title]) => (
              <a
                key={name}
                href={`#/docs/${name}`}
                aria-current={name === current ? "page" : undefined}
                className={cx("block rounded px-3 py-1.5 text-sm", name === current ? "bg-fg/5 font-medium text-fg" : "text-muted hover:text-fg")}
              >
                {title}
              </a>
            ))}
          </div>
        ))}
      </aside>
      <div id="docs-content" className="min-w-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-5xl gap-12 px-5 py-8 md:px-10 md:py-12">
          <article className="min-w-0 flex-1">
            <button type="button" onClick={() => setMenu(!menu)} className="mb-5 flex cursor-pointer items-center gap-2 text-sm text-muted md:hidden">
              <MenuIcon size={15} aria-hidden /> All pages
            </button>
            {found ? (
              <>
                <h1 className="mb-6 text-3xl font-medium tracking-tight">Results for “{query.trim()}”</h1>
                {found.length === 0 && <p className="text-muted">No page mentions that.</p>}
                <div className="space-y-3">
                  {found.map((hit) => (
                    <a key={hit.name} href={`#/docs/${hit.name}`} onClick={() => setQuery("")} className="block rounded-lg border border-line bg-card p-4 hover:border-accent/40">
                      <p className="font-medium">{hit.title}</p>
                      <p className="mt-1 text-sm text-muted">{hit.line}</p>
                    </a>
                  ))}
                </div>
              </>
            ) : (
              <>
                <p className="mb-2 text-sm text-accent">{NAV.find((section) => section.items.some(([name]) => name === current))?.group}</p>
                <Markdown text={source} />
                <nav aria-label="More pages" className="mt-12 grid gap-4 border-t border-line pt-6 sm:grid-cols-2">
                  {index > 0 ? (
                    <a href={`#/docs/${ORDER[index - 1][0]}`} className="rounded-lg border border-line p-4 hover:border-accent/40">
                      <span className="flex items-center gap-1 text-xs text-faint"><ArrowLeft size={12} aria-hidden /> Previous</span>
                      <span className="mt-1 block font-medium">{ORDER[index - 1][1]}</span>
                    </a>
                  ) : <span />}
                  {index < ORDER.length - 1 && (
                    <a href={`#/docs/${ORDER[index + 1][0]}`} className="rounded-lg border border-line p-4 text-right hover:border-accent/40">
                      <span className="flex items-center justify-end gap-1 text-xs text-faint">Next <ArrowRight size={12} aria-hidden /></span>
                      <span className="mt-1 block font-medium">{ORDER[index + 1][1]}</span>
                    </a>
                  )}
                </nav>
              </>
            )}
          </article>
          {!found && headings.length > 1 && (
            <nav aria-label="On this page" className="sticky top-8 hidden w-52 shrink-0 self-start xl:block">
              <p className="mb-2 text-xs font-medium tracking-wide text-faint">On this page</p>
              {headings.map((heading) => (
                <button
                  key={heading}
                  type="button"
                  onClick={() => document.getElementById(slug(heading.replace(/`/g, "")))?.scrollIntoView({ behavior: "smooth" })}
                  className="block w-full cursor-pointer py-1 text-left text-sm text-muted hover:text-fg"
                >
                  {heading.replace(/`/g, "")}
                </button>
              ))}
            </nav>
          )}
        </div>
      </div>
    </div>
  );
}
