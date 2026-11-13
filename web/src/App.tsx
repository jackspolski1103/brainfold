import { BookOpen, CircleHelp, FolderTree, LayoutGrid, LogOut, type LucideIcon, Menu as MenuIcon, Moon, PanelLeft, Plug, ScrollText, ShieldCheck, Sparkles, Sun, UserPlus, UserRound, Users } from "lucide-react";
import { type FormEvent, type ReactNode, useCallback, useEffect, useState } from "react";
import { AccessPage } from "./Access";
import { ApiError, SIGNED_OUT, type State, type User, api } from "./api";
import { Brain } from "./Brain";
import { Connect } from "./Connect";
import { Docs } from "./Docs";
import { Members } from "./Members";
import { Account, ActivityPage, Overview, Skills } from "./Pages";
import { Badge, Button, Field, Input, Menu, Notice, cx, menuItem } from "./ui";

function useRoute(): string {
  const read = () => decodeURI(location.hash.slice(1)) || "/";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    addEventListener("hashchange", onChange);
    return () => removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

const Logo = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7" strokeLinejoin="round" aria-hidden>
    <path d="M3.5 6.5 12 3l8.5 3.5v11L12 21l-8.5-3.5z" />
    <path d="M3.5 6.5 12 10l8.5-3.5M12 10v11" />
  </svg>
);

function ThemeToggle() {
  const [light, setLight] = useState(document.documentElement.classList.contains("light"));
  const toggle = () => {
    document.documentElement.classList.toggle("light", !light);
    try {
      localStorage.setItem("theme", light ? "dark" : "light");
    } catch {
      // The choice then lasts until the page is closed.
    }
    setLight(!light);
  };
  return (
    <Button size="icon" aria-label={`Switch to ${light ? "dark" : "light"} theme`} onClick={toggle}>
      {light ? <Moon size={16} aria-hidden /> : <Sun size={16} aria-hidden />}
    </Button>
  );
}

function TopBar({ title, badge, onMenu, children }: { title: string; badge: string; onMenu?: () => void; children: ReactNode }) {
  return (
    <header className="flex h-12 shrink-0 items-center border-b border-shell">
      <div className="flex h-full items-center gap-2.5 px-4 md:w-[255px] md:border-r md:border-shell">
        {onMenu && (
          <Button size="icon" variant="ghost" aria-label="Open navigation" className="md:hidden" onClick={onMenu}>
            <MenuIcon size={17} aria-hidden />
          </Button>
        )}
        <a href="#/" className="flex items-center gap-2.5 text-sm font-medium">
          <Logo /> Brainfold
        </a>
        <span className="hidden sm:inline"><Badge tone="accent">{badge}</Badge></span>
      </div>
      <p className="hidden truncate px-4 text-sm md:block">{title}</p>
      <div className="ml-auto flex items-center gap-1.5 px-2">{children}</div>
    </header>
  );
}

function Entrance({ state, invite, onDone }: { state: State; invite: string | null; onDone: () => void }) {
  const mode = invite ? "accept" : state.setup_needed ? "setup" : "login";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const titles = {
    setup: ["Create the first account", "This account administers the brain and invites everyone else."],
    login: ["Welcome back", "Sign in to your team's brain."],
    accept: ["Choose your password", "One step left to finish creating your account."],
  }[mode];

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "accept") await api("POST", "/api/accept", { invite, password });
      else await api("POST", `/api/${mode}`, { email, password, ...(mode === "setup" ? { code } : {}) });
      if (mode === "accept") location.hash = "#/";
      onDone();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-full flex-col items-center justify-center px-4 py-10">
      <div className="mb-6 flex items-center gap-2.5 text-lg font-medium">
        <Logo size={26} /> Brainfold
      </div>
      <div className="w-full max-w-sm rounded-lg border border-line bg-card p-6">
        <h1 className="text-xl">{titles[0]}</h1>
        <p className="mt-1 mb-5 text-sm text-muted">{titles[1]}</p>
        <form onSubmit={submit} className="space-y-4">
          {mode !== "accept" && (
            <Field label="Email">
              <Input type="email" autoComplete="username" required autoFocus value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
          )}
          <Field label="Password" hint={mode === "login" ? undefined : "At least 10 characters."}>
            <Input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              required
              minLength={mode === "login" ? undefined : 10}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          {mode === "setup" && state.code_required && (
            <Field label="Setup code" hint="Printed in the server logs when it started: “Setup code for the first account”.">
              <Input required autoComplete="off" value={code} onChange={(event) => setCode(event.target.value)} />
            </Field>
          )}
          {error && <Notice>{error}</Notice>}
          <Button type="submit" variant="primary" disabled={busy} className="w-full">
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>
      </div>
      <p className="mt-5 flex items-center gap-4 text-sm text-muted">
        <a href="#/docs" className="hover:text-fg">Documentation</a>
        {mode === "login" && <span className="text-faint">Forgot your password? Ask an administrator for a reset link.</span>}
        {mode === "accept" && <a href="#/" className="hover:text-fg">Already have an account? Sign in</a>}
      </p>
    </main>
  );
}

type Page = { href: string; label: string; icon: LucideIcon; match: (route: string) => boolean };

function Panel({ user, route, onSignOut }: { user: User; route: string; onSignOut: () => void }) {
  const admin = user.role === "admin";
  const [collapsed, setCollapsed] = useState(false);
  const [drawer, setDrawer] = useState(false);
  useEffect(() => setDrawer(false), [route]);
  const is = (prefix: string) => (path: string) => path === prefix || path.startsWith(`${prefix}/`);
  const groups: { name: string; pages: Page[] }[] = [
    {
      name: "General",
      pages: [
        { href: "/", label: "Overview", icon: LayoutGrid, match: (path) => path === "/" },
        { href: "/brain/", label: "Brain", icon: FolderTree, match: (path) => is("/brain")(path) || is("/file")(path) },
        { href: "/skills", label: "Skills", icon: Sparkles, match: is("/skills") },
        { href: "/connect", label: "Connect a harness", icon: Plug, match: is("/connect") },
      ],
    },
    ...(admin
      ? [
          {
            name: "Administration",
            pages: [
              { href: "/access", label: "Access", icon: ShieldCheck, match: is("/access") },
              { href: "/members", label: "Members", icon: Users, match: is("/members") },
              { href: "/activity", label: "Activity", icon: ScrollText, match: is("/activity") },
            ],
          },
        ]
      : []),
  ];
  const path = route.split("?")[0];
  const active = groups.flatMap((group) => group.pages).find((page) => page.match(path));
  const adminOnly = ["/access", "/members", "/activity"].some((prefix) => is(prefix)(path)) && !admin;

  return (
    <div className="flex h-full flex-col">
      <TopBar title={active?.label ?? (is("/account")(path) ? "Account" : "")} badge={admin ? "Admin" : "Member"} onMenu={() => setDrawer(!drawer)}>
        {admin && (
          <a href="#/members?invite" className="mr-1 hidden h-8 items-center gap-2 rounded-md border border-line px-2.5 text-sm hover:bg-fg/5 sm:inline-flex">
            <UserPlus size={14} aria-hidden /> Invite users
          </a>
        )}
        <a href="#/docs" aria-label="Documentation" title="Documentation" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-line hover:bg-fg/5">
          <CircleHelp size={16} aria-hidden />
        </a>
        <ThemeToggle />
        <Menu label="Account menu" trigger={<UserRound size={16} aria-hidden />}>
          <div className="border-b border-line px-2.5 py-2">
            <p className="truncate text-sm">{user.email}</p>
            <p className="text-xs text-faint">{admin ? "Administrator" : "Member"}</p>
          </div>
          <a role="menuitem" href="#/account" className={menuItem}><UserRound size={14} aria-hidden /> Account and password</a>
          <a role="menuitem" href="#/connect" className={menuItem}><Plug size={14} aria-hidden /> Harness tokens</a>
          <button type="button" role="menuitem" onClick={onSignOut} className={menuItem}><LogOut size={14} aria-hidden /> Sign out</button>
        </Menu>
      </TopBar>
      <div className="relative flex min-h-0 flex-1">
        <aside className={cx("shrink-0 flex-col border-r border-shell bg-bg md:flex", collapsed ? "md:w-14" : "md:w-[255px]", drawer ? "absolute inset-y-0 left-0 z-20 flex w-[255px]" : "hidden")}>
          <nav aria-label="Sections" className="flex-1 overflow-y-auto py-4">
            {groups.map((group) => (
              <div key={group.name} className="mb-4">
                <p className={cx("flex h-7 items-center px-4 text-xs font-medium tracking-wide text-faint", collapsed && "md:invisible")}>{group.name}</p>
                {group.pages.map(({ href, label, icon: Icon, match }) => (
                  <a
                    key={href}
                    href={`#${href}`}
                    title={collapsed ? label : undefined}
                    aria-current={match(path) ? "page" : undefined}
                    className={cx(
                      "flex h-10 items-center gap-2.5 border-l-2 px-4 text-sm whitespace-nowrap",
                      match(path) ? "border-accent bg-fg/5 font-medium text-fg" : "border-transparent text-muted hover:bg-fg/[0.03] hover:text-fg",
                    )}
                  >
                    <Icon size={16} className={cx("shrink-0", match(path) && "text-accent")} aria-hidden />
                    <span className={cx(collapsed && "md:hidden")}>{label}</span>
                  </a>
                ))}
              </div>
            ))}
          </nav>
          <a href="#/docs" title="Documentation" className="flex h-10 items-center gap-2.5 border-t border-shell px-4 text-sm whitespace-nowrap text-muted hover:text-fg">
            <BookOpen size={16} className="shrink-0" aria-hidden />
            <span className={cx(collapsed && "md:hidden")}>Documentation</span>
          </a>
          <button type="button" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} onClick={() => setCollapsed(!collapsed)} className="hidden h-12 cursor-pointer items-center justify-center border-t border-shell text-muted hover:text-fg md:flex">
            <PanelLeft size={16} aria-hidden />
          </button>
        </aside>
        <main className="min-w-0 flex-1 overflow-y-auto">
          <div className="px-5 py-8 md:px-12 md:py-10">
            {adminOnly && <Notice>Only administrators can open this page.</Notice>}
            {path === "/" && <Overview user={user} />}
            {is("/brain")(path) && <Brain admin={admin} kind="folder" path={path.slice("/brain".length) || "/"} />}
            {is("/file")(path) && <Brain admin={admin} kind="file" path={path.slice("/file".length)} />}
            {is("/skills")(path) && <Skills />}
            {is("/connect")(path) && <Connect />}
            {is("/account")(path) && <Account user={user} />}
            {admin && is("/access")(path) && <AccessPage />}
            {admin && is("/members")(path) && <Members self={user.email} tab={path === "/members/groups" ? "groups" : "users"} />}
            {admin && is("/activity")(path) && <ActivityPage />}
          </div>
        </main>
      </div>
    </div>
  );
}

export function App() {
  const route = useRoute();
  const [state, setState] = useState<State | null>(null);
  const [failed, setFailed] = useState(false);
  const refresh = useCallback(() => {
    api<State>("GET", "/api/state").then(setState, () => setFailed(true));
  }, []);
  useEffect(refresh, [refresh]);
  useEffect(() => {
    addEventListener(SIGNED_OUT, refresh);
    return () => removeEventListener(SIGNED_OUT, refresh);
  }, [refresh]);

  if (route === "/docs" || route.startsWith("/docs/")) {
    return (
      <div className="flex h-full flex-col">
        <TopBar title="Documentation" badge="Docs">
          <ThemeToggle />
          <a href="#/" className="inline-flex h-8 items-center rounded-md border border-accent/25 bg-accent/10 px-2.5 text-sm hover:bg-accent/20">
            {state?.user ? "Open the panel" : "Sign in"}
          </a>
        </TopBar>
        <Docs page={route.slice("/docs/".length)} />
      </div>
    );
  }
  if (failed) return <main className="p-8"><Notice>The server could not be reached.</Notice></main>;
  if (!state) return null;
  const invite = route.startsWith("/accept/") ? route.slice("/accept/".length) : null;
  if (!state.user || invite) return <Entrance state={state} invite={invite} onDone={refresh} />;

  async function signOut() {
    await api("POST", "/api/logout", {}).catch(() => undefined);
    location.hash = "#/";
    refresh();
  }
  return <Panel user={state.user} route={route} onSignOut={signOut} />;
}
