import { Check, Copy, ExternalLink, type LucideIcon, Search, X } from "lucide-react";
import { Marked } from "marked";
import {
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

export const cx = (...names: (string | false | null | undefined)[]) => names.filter(Boolean).join(" ");

const BUTTON = {
  primary: "border-accent/25 bg-accent/10 hover:bg-accent/20",
  outline: "border-line hover:bg-fg/5",
  ghost: "border-transparent text-muted hover:bg-fg/5 hover:text-fg",
  danger: "border-danger/25 bg-danger/10 text-danger hover:bg-danger/20",
};
const SIZE = { md: "h-9 px-3", sm: "h-8 px-2.5", icon: "h-8 w-8" };

export function Button({
  variant = "outline",
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof BUTTON; size?: keyof typeof SIZE }) {
  return (
    <button
      type="button"
      {...props}
      className={cx(
        "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 rounded-md border text-sm whitespace-nowrap transition-colors",
        "active:scale-[0.99] disabled:pointer-events-none disabled:opacity-50",
        BUTTON[variant],
        SIZE[size],
        className,
      )}
    />
  );
}

const CONTROL =
  "h-9 w-full rounded-md border border-line bg-transparent px-3 text-sm outline-none placeholder:text-faint focus:border-accent/60 focus:ring-2 focus:ring-accent/15";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(CONTROL, className)} />;
}

export function SearchInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className={cx("relative", className)}>
      <Search size={15} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-faint" aria-hidden />
      <input type="search" {...props} className={cx(CONTROL, "pl-9")} />
    </div>
  );
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(CONTROL, "cursor-pointer bg-card pr-2", className)} />;
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-faint">{hint}</span>}
    </label>
  );
}

export function PageHeader({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <header className="mb-8">
      <div className="flex items-center gap-3">
        <Icon size={26} strokeWidth={1.6} className="shrink-0 text-accent" aria-hidden />
        <h1 className="truncate text-2xl underline decoration-accent/90 underline-offset-4">{title}</h1>
      </div>
      {children && <p className="mt-3 text-muted">{children}</p>}
    </header>
  );
}

export function DocsLink({ to }: { to: string }) {
  return (
    <a
      href={`#/docs/${to}`}
      className="inline-flex h-[22px] items-center gap-1 rounded border border-accent/10 bg-accent/15 px-1.5 text-xs text-accent hover:bg-accent/25"
    >
      Documentation <ExternalLink size={11} aria-hidden />
    </a>
  );
}

export function Section({
  title,
  description,
  docs,
  action,
  children,
}: {
  title?: string;
  description?: ReactNode;
  docs?: string;
  action?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-line bg-card p-5 text-sm">
      {(title || action) && (
        <header className={cx("flex flex-wrap items-start justify-between gap-3", children != null && "mb-4")}>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-lg">{title}</h2>
              {docs && <DocsLink to={docs} />}
            </div>
            {description && <p className="mt-1 text-muted">{description}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

const TONE = {
  neutral: "border-line bg-fg/5 text-muted",
  accent: "border-accent/10 bg-accent/15 text-accent",
  success: "border-success/10 bg-success/15 text-success",
  warning: "border-warning/10 bg-warning/15 text-warning",
  danger: "border-danger/10 bg-danger/15 text-danger",
};

export function Badge({ tone = "neutral", children, title }: { tone?: keyof typeof TONE; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={cx("inline-flex h-[22px] items-center gap-1 rounded border px-1.5 text-xs whitespace-nowrap", TONE[tone])}>
      {children}
    </span>
  );
}

export function Notice({ tone = "danger", children }: { tone?: "danger" | "accent" | "warning" | "success"; children: ReactNode }) {
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cx("rounded-md border px-3 py-2 text-sm", TONE[tone], "text-fg")}>
      {children}
    </div>
  );
}

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-md border border-line bg-panel">
      <table className="w-full text-left text-sm">
        <thead>
          <tr>
            {head.map((title, index) => (
              <th key={index} className="h-[34px] px-4 text-xs font-bold whitespace-nowrap text-faint">
                {title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export const Tr = ({ children, onClick }: { children: ReactNode; onClick?: () => void }) => (
  <tr onClick={onClick} className={cx("border-t border-line hover:bg-fg/[0.03]", onClick && "cursor-pointer")}>
    {children}
  </tr>
);

export const Td = ({ children, mono, className }: { children?: ReactNode; mono?: boolean; className?: string }) => (
  <td className={cx("h-[41px] px-4 py-1.5 align-middle", mono && "font-mono text-xs", className)}>{children}</td>
);

export function Empty({ icon: Icon, title, children, action }: { icon?: LucideIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-md border border-dashed border-line bg-panel px-6 py-10 text-center">
      {Icon && (
        <span className="mb-1 flex h-10 w-10 items-center justify-center rounded-md bg-fg/5 text-faint">
          <Icon size={20} aria-hidden />
        </span>
      )}
      <p className="text-sm font-medium">{title}</p>
      {children && <p className="max-w-md text-xs text-faint">{children}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: ReactNode }[]; value: T; onChange: (id: T) => void }) {
  return (
    <div role="tablist" className="mb-5 flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={tab.id === value}
          onClick={() => onChange(tab.id)}
          className={cx(
            "-mb-px h-11 cursor-pointer border-b-2 px-3 text-sm whitespace-nowrap",
            tab.id === value ? "border-accent text-fg" : "border-transparent text-fg/60 hover:text-fg",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function Segmented<T extends string>({ options, value, onChange, label }: { options: { id: T; label: ReactNode }[]; value: T; onChange: (id: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-line p-0.5">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="radio"
          aria-checked={option.id === value}
          onClick={() => onChange(option.id)}
          className={cx("h-7 cursor-pointer rounded px-2.5 text-sm whitespace-nowrap", option.id === value ? "bg-fg/10 text-fg" : "text-muted hover:text-fg")}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** The native dialog: focus trap, Escape and the backdrop come with the platform. */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return (
    <dialog ref={ref} onClose={onClose} onMouseDown={(event) => event.target === ref.current && onClose()}>
      {open && (
        <div className="p-6">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg">{title}</h2>
              {description && <p className="mt-1 text-sm text-muted">{description}</p>}
            </div>
            <Button variant="ghost" size="icon" aria-label="Close" onClick={onClose}>
              <X size={16} aria-hidden />
            </Button>
          </div>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function Menu({ label, trigger, children }: { label: string; trigger: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => !ref.current?.contains(event.target as Node) && setOpen(false);
    const escape = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
  return (
    <div ref={ref} className="relative">
      <Button size="icon" aria-label={label} aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(!open)}>
        {trigger}
      </Button>
      {open && (
        <div role="menu" onClick={() => setOpen(false)} className="absolute right-0 z-30 mt-1.5 min-w-56 rounded-md border border-line bg-card p-1 shadow-2xl">
          {children}
        </div>
      )}
    </div>
  );
}

export const menuItem = "flex w-full cursor-pointer items-center gap-2 rounded px-2.5 py-2 text-left text-sm text-muted hover:bg-fg/5 hover:text-fg";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="sm"
      aria-label={label}
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
    >
      {copied ? <Check size={14} className="text-success" aria-hidden /> : <Copy size={14} aria-hidden />}
      {copied ? "Copied" : label}
    </Button>
  );
}

export function Code({ text, title }: { text: string; title?: string }) {
  return (
    <div className="overflow-hidden rounded-md border border-line bg-panel">
      <div className="flex items-center justify-between gap-3 border-b border-line py-1.5 pr-1.5 pl-3">
        <span className="truncate text-xs text-faint">{title}</span>
        <CopyButton text={text} />
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[13px] leading-6 whitespace-pre-wrap break-all">{text}</pre>
    </div>
  );
}

const escape = (text: string) => text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
export const slug = (text: string) => text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

/** Markdown written by people and agents is untrusted: raw HTML is shown as text,
 * images are never loaded, and a link only keeps a safe address. */
function renderer(link: (href: string) => string) {
  return new Marked({
    gfm: true,
    renderer: {
      html: ({ text }) => escape(text),
      image: ({ text }) => escape(text),
      heading({ tokens, depth }) {
        const inner = this.parser.parseInline(tokens);
        return `<h${depth} id="${slug(inner.replace(/<[^>]+>/g, ""))}">${inner}</h${depth}>`;
      },
      link({ href, tokens }) {
        const inner = this.parser.parseInline(tokens);
        const target = link(href);
        if (!/^(https?:\/\/|mailto:|#)/i.test(target)) return inner;
        const outside = !target.startsWith("#");
        return `<a href="${escape(target)}"${outside ? ' target="_blank" rel="noopener noreferrer"' : ""}>${inner}</a>`;
      },
    },
  });
}

const same = (href: string) => href;

export function Markdown({ text, link = same }: { text: string; link?: (href: string) => string }) {
  const html = useMemo(() => renderer(link).parse(text, { async: false }), [text, link]);
  return <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />;
}
