import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

const join = (...names: (string | false | undefined)[]) => names.filter(Boolean).join(" ");

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "outline" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-zinc-900 text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300",
    outline: "border border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800",
    ghost: "hover:bg-zinc-100 dark:hover:bg-zinc-800",
    danger: "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950",
  }[variant];
  return (
    <button
      {...props}
      className={join(
        "inline-flex h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500",
        "disabled:pointer-events-none disabled:opacity-50",
        styles,
        className,
      )}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={join(
        "h-9 w-full rounded-md border border-zinc-300 bg-white px-3 text-sm outline-none",
        "placeholder:text-zinc-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20",
        "dark:border-zinc-700 dark:bg-zinc-900",
        className,
      )}
    />
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-sm font-medium">{label}</span>
      {children}
      {hint && <span className="block text-xs text-zinc-500">{hint}</span>}
    </label>
  );
}

export function Card({ title, action, children }: { title?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
      {(title || action) && (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b border-zinc-200 px-4 py-2 dark:border-zinc-800">
          <h2 className="text-sm font-semibold">{title}</h2>
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "green" | "red" | "amber"; children: ReactNode }) {
  const tones = {
    neutral: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
    green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    red: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
    amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  }[tone];
  return <span className={join("inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium", tones)}>{children}</span>;
}

export function Notice({ tone = "red", children }: { tone?: "red" | "blue"; children: ReactNode }) {
  const tones = {
    red: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
    blue: "border-blue-200 bg-blue-50 text-blue-900 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-100",
  }[tone];
  return (
    <p role={tone === "red" ? "alert" : "status"} className={join("rounded-md border px-3 py-2 text-sm", tones)}>
      {children}
    </p>
  );
}

export function Table({ head, children, empty }: { head: string[]; children: ReactNode; empty?: boolean }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-zinc-500">
          <tr>
            {head.map((title) => (
              <th key={title} className="px-3 py-2 font-medium">
                {title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">{children}</tbody>
      </table>
      {empty && <p className="px-3 py-6 text-center text-sm text-zinc-500">Nothing here yet.</p>}
    </div>
  );
}

export const Td = ({ children, mono }: { children: ReactNode; mono?: boolean }) => (
  <td className={join("px-3 py-2 align-middle", mono && "font-mono text-xs")}>{children}</td>
);

export function Copyable({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2">
      <code className="min-w-0 flex-1 break-all rounded-md bg-zinc-100 px-3 py-2 font-mono text-xs dark:bg-zinc-800">
        {text}
      </code>
      <Button variant="outline" onClick={() => navigator.clipboard.writeText(text)}>
        Copy
      </Button>
    </div>
  );
}
