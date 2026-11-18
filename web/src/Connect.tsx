import { KeyRound, Plug, Plus, Trash2 } from "lucide-react";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { type Token, ago, api, message, when } from "./api";
import { Badge, Button, Code, Dialog, Empty, Field, Input, Notice, PageHeader, Section, Table, Tabs, Td, Tr } from "./ui";

type Harness = "claude" | "codex" | "cursor" | "other" | "files";

function Snippets({ token }: { token: string }) {
  const [harness, setHarness] = useState<Harness>("claude");
  const url = `${location.origin}/mcp`;
  const secret = token || "<your-token>";
  const step = (number: number, text: string) => (
    <p className="flex gap-2.5 text-muted">
      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-fg/10 text-xs text-fg">{number}</span>
      <span>{text}</span>
    </p>
  );
  return (
    <>
      <Tabs
        value={harness}
        onChange={setHarness}
        tabs={[
          { id: "claude", label: "Claude Code" },
          { id: "codex", label: "Codex" },
          { id: "cursor", label: "Cursor" },
          { id: "other", label: "Other MCP client" },
          { id: "files", label: "Files from a terminal" },
        ]}
      />
      <div className="space-y-3">
        {!token && <Notice tone="accent">Create a token above and these commands are filled in with it. A token is shown only once.</Notice>}
        {harness === "claude" && (
          <>
            {step(1, "Run this once in a terminal. It registers the brain for your user.")}
            <Code title="Terminal" text={`claude mcp add --transport http --scope user brainfold ${url} --header "Authorization: Bearer ${secret}"`} />
            {step(2, "Open Claude Code and run /mcp: brainfold should show as connected.")}
          </>
        )}
        {harness === "codex" && (
          <>
            {step(1, "Keep the token in an environment variable, for example in your shell profile.")}
            <Code title="~/.zshrc" text={`export BRAINFOLD_TOKEN="${secret}"`} />
            {step(2, "Add the server to the Codex configuration.")}
            <Code title="~/.codex/config.toml" text={`[mcp_servers.brainfold]\nurl = "${url}"\nbearer_token_env_var = "BRAINFOLD_TOKEN"`} />
            {step(3, "Start Codex from a terminal that has the variable set.")}
          </>
        )}
        {harness === "cursor" && (
          <>
            {step(1, "Add the server to the Cursor configuration, then restart Cursor.")}
            <Code title="~/.cursor/mcp.json" text={JSON.stringify({ mcpServers: { brainfold: { url, headers: { Authorization: `Bearer ${secret}` } } } }, null, 2)} />
          </>
        )}
        {harness === "other" && (
          <>
            {step(1, "Any client that speaks MCP over streamable HTTP works. Give it this address and header.")}
            <Code title="Server address" text={url} />
            <Code title="Header" text={`Authorization: Bearer ${secret}`} />
          </>
        )}
        {harness === "files" && (
          <>
            {step(1, "Manuals, spreadsheets and other files that are not text travel through the brainfold command, with the same token.")}
            <Code title="Terminal" text={`export BRAINFOLD_URL="${location.origin}"\nexport BRAINFOLD_TOKEN="${secret}"\n\nbrainfold put salaries.xlsx /hr/salaries.xlsx\nbrainfold get /hr/salaries.xlsx ./salaries.xlsx`} />
          </>
        )}
        {harness !== "files" && (
          <p className="pt-1 text-xs text-faint">
            Then ask your agent: “What is in the brain? Start from the root.” The connection was checked with Claude Code; the Codex and Cursor settings follow their documentation.
          </p>
        )}
      </div>
    </>
  );
}

export function Connect({ admin }: { admin: boolean }) {
  const [tokens, setTokens] = useState<Token[] | null>(null);
  const [creating, setCreating] = useState(false);
  const [label, setLabel] = useState("");
  const [manage, setManage] = useState(false);
  const [created, setCreated] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => api<{ tokens: Token[] }>("GET", "/api/tokens").then((result) => setTokens(result.tokens), (failure) => setError(message(failure))), []);
  useEffect(() => void load(), [load]);

  async function create(event: FormEvent) {
    event.preventDefault();
    try {
      setCreated((await api<{ token: string }>("POST", "/api/tokens", { name: label, manage })).token);
      setLabel("");
      setManage(false);
      setCreating(false);
      await load();
    } catch (failure) {
      setError(message(failure));
    }
  }
  const newToken = <Button variant="primary" onClick={() => setCreating(true)}><Plus size={15} aria-hidden /> Create token</Button>;

  return (
    <>
      <PageHeader icon={Plug} title="Connect a harness">
        Give Claude Code, Codex or any other MCP client access to the brain. The agent acts as you: it reads and writes exactly what you can.
      </PageHeader>
      <div className="space-y-5">
        {error && <Notice>{error}</Notice>}
        {created && (
          <Section title="Your new token" description="Copy it now: it is not shown again. The commands below already include it." action={<Button size="sm" variant="ghost" onClick={() => setCreated("")}>Dismiss</Button>}>
            <Code title="Token" text={created} />
          </Section>
        )}
        <Section title="Access tokens" docs="connect" description="One token per harness and machine, so you can revoke one without touching the others." action={newToken}>
          {tokens?.length === 0 ? (
            <Empty icon={KeyRound} title="No tokens yet" action={newToken}>Create a token, then paste the command of your harness below.</Empty>
          ) : (
            <Table head={["Name", "Created", "Last used", ""]}>
              {(tokens ?? []).map((token) => (
                <Tr key={token.id}>
                  <Td><span className="font-medium">{token.name}</span>{token.manage && <Badge>Manages access</Badge>}</Td>
                  <Td><span className="text-muted" title={when(token.created)}>{ago(token.created)}</span></Td>
                  <Td>{token.last_used ? <span className="text-muted" title={when(token.last_used)}>{ago(token.last_used)}</span> : <Badge>Never used</Badge>}</Td>
                  <Td className="w-px text-right">
                    <Button size="sm" variant="ghost" className="hover:text-danger" onClick={() => confirm(`Revoke "${token.name}"? The harness using it loses access at once.`) && void api("DELETE", `/api/tokens/${token.id}`).then(load)}>
                      <Trash2 size={13} aria-hidden /> Revoke
                    </Button>
                  </Td>
                </Tr>
              ))}
            </Table>
          )}
        </Section>
        <Section title="Set up your harness" docs="connect" description="Pick where your agent runs.">
          <Snippets token={created} />
        </Section>
      </div>
      <Dialog open={creating} onClose={() => setCreating(false)} title="Create token" description="Name it after the harness and machine that will use it.">
        <form onSubmit={create} className="space-y-4">
          <Field label="Name">
            <Input required autoFocus maxLength={80} placeholder="Claude Code on my laptop" value={label} onChange={(event) => setLabel(event.target.value)} />
          </Field>
          {admin && (
            <label className="flex items-start gap-2.5 text-sm">
              <input type="checkbox" className="mt-0.5" checked={manage} onChange={(event) => setManage(event.target.checked)} />
              <span>
                Can manage access and groups
                <span className="block text-xs text-muted">Your agent can change who reads and writes each folder and edit groups. Leave it off for everyday tokens.</span>
              </span>
            </label>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreating(false)}>Cancel</Button>
            <Button type="submit" variant="primary">Create token</Button>
          </div>
        </form>
      </Dialog>
    </>
  );
}
