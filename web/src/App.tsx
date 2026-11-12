import { Activity as ActivityIcon, FolderTree, KeyRound, LogOut, Users } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ActivityPage, Members, Tokens } from "./Admin";
import { ApiError, type State, api } from "./api";
import { Brain } from "./Brain";
import { Button, Card, Field, Input, Notice } from "./ui";

function useRoute(): string {
  const read = () => decodeURI(location.hash.slice(1)) || "/brain/";
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => setRoute(read());
    addEventListener("hashchange", onChange);
    return () => removeEventListener("hashchange", onChange);
  }, []);
  return route;
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
    login: ["Sign in", "Use the email and password of your account."],
    accept: ["Accept your invitation", "Choose a password to finish creating your account."],
  }[mode];

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "accept") await api("POST", "/api/accept", { invite, password });
      else await api("POST", `/api/${mode}`, { email, password, ...(mode === "setup" ? { code } : {}) });
      if (mode === "accept") location.hash = "#/brain/";
      onDone();
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-4">
      <div>
        <p className="text-sm font-semibold tracking-tight text-zinc-500">Brainfold</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">{titles[0]}</h1>
        <p className="mt-1 text-sm text-zinc-500">{titles[1]}</p>
      </div>
      <form onSubmit={submit} className="space-y-4">
        {mode !== "accept" && (
          <Field label="Email">
            <Input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
        )}
        <Field label="Password" hint={mode === "login" ? undefined : "At least 10 characters."}>
          <Input
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "login" ? undefined : 10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>
        {mode === "setup" && state.code_required && (
          <Field label="Setup code" hint="Printed by the server when it started (docker compose logs brainfold).">
            <Input required value={code} onChange={(e) => setCode(e.target.value)} />
          </Field>
        )}
        {error && <Notice>{error}</Notice>}
        <Button type="submit" disabled={busy} className="w-full">
          {mode === "login" ? "Sign in" : "Create account"}
        </Button>
      </form>
    </main>
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

  if (failed) return <main className="p-8"><Notice>The server could not be reached.</Notice></main>;
  if (!state) return null;
  const invite = route.startsWith("/accept/") ? route.slice("/accept/".length) : null;
  if (!state.user || invite) return <Entrance state={state} invite={invite} onDone={refresh} />;

  const user = state.user;
  const admin = user.role === "admin";
  const pages = [
    { href: "/brain/", label: "Brain", icon: FolderTree, show: true, active: route.startsWith("/brain") || route.startsWith("/file") },
    { href: "/members", label: "Members", icon: Users, show: admin, active: route === "/members" },
    { href: "/tokens", label: "Tokens", icon: KeyRound, show: true, active: route === "/tokens" },
    { href: "/activity", label: "Activity", icon: ActivityIcon, show: admin, active: route === "/activity" },
  ].filter((page) => page.show);

  async function logout() {
    await api("POST", "/api/logout", {}).catch(() => undefined);
    refresh();
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col gap-1 border-zinc-200 p-4 md:w-56 md:border-r dark:border-zinc-800">
        <p className="mb-3 px-2 text-sm font-semibold tracking-tight">Brainfold</p>
        <nav className="flex gap-1 md:flex-col" aria-label="Sections">
          {pages.map(({ href, label, icon: Icon, active }) => (
            <a
              key={href}
              href={`#${href}`}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                active ? "bg-zinc-200 font-medium dark:bg-zinc-800" : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
              }`}
            >
              <Icon size={16} aria-hidden /> {label}
            </a>
          ))}
        </nav>
        <div className="mt-auto hidden space-y-2 pt-6 md:block">
          <p className="truncate px-2 text-xs text-zinc-500" title={user.email}>
            {user.email} · {user.role}
          </p>
          <Button variant="ghost" onClick={logout} className="w-full justify-start">
            <LogOut size={16} aria-hidden /> Sign out
          </Button>
        </div>
      </aside>
      <main className="min-w-0 flex-1 space-y-4 p-4 md:p-8">
        {route.startsWith("/brain") && <Brain admin={admin} kind="folder" path={route.slice("/brain".length) || "/"} />}
        {route.startsWith("/file") && <Brain admin={admin} kind="file" path={route.slice("/file".length)} />}
        {route === "/members" && admin && <Members self={user.email} />}
        {route === "/tokens" && <Tokens />}
        {route === "/activity" && admin && <ActivityPage />}
        <div className="md:hidden">
          <Card>
            <div className="flex items-center justify-between gap-3">
              <span className="truncate text-sm text-zinc-500">{user.email}</span>
              <Button variant="outline" onClick={logout}>Sign out</Button>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
}
