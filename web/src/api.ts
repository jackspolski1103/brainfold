export type User = { email: string; role: "admin" | "member" };
export type State = { setup_needed: boolean; code_required: boolean; user: User | null };
export type Entry = {
  path: string;
  kind: "directory" | "file";
  description?: string;
  size?: number;
  read?: string[] | null;
  write?: string[] | null;
};
export type Listing = {
  path: string;
  description: string;
  start_here: string[];
  can_write: boolean;
  entries: Entry[];
  truncated: boolean;
  read?: string[] | null;
  write?: string[] | null;
  guide?: string[];
  home?: string;
};
export type FileView = {
  path: string;
  kind: "text" | "binary";
  size: number;
  version: string;
  content?: string;
  truncated?: boolean;
  fetch?: string;
};
export type Member = { email: string; role: string; pending: boolean; groups: string[] };
export type Token = { id: number; name: string; created: number; last_used: number | null; manage: boolean };
export type Activity = {
  at: number;
  actor: string;
  action: string;
  path: string;
  ok: boolean;
  versioned: boolean | null;
};

export type Skill = { name: string; description: string; path: string | null };
export type Hit = { path: string; line: number; text: string };
export type Health = { git: boolean; database: boolean; unversioned_writes: number; mirror: string };

export const SIGNED_OUT = "brainfold:signed-out";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return answer<T>(response);
}

async function answer<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  // The session ended elsewhere (removed, signed out, expired): the app shows the sign-in.
  if (data?.error?.code === "unauthenticated") dispatchEvent(new Event(SIGNED_OUT));
  if (!response.ok) {
    const error = data?.error ?? { code: "request_failed", message: `The server answered ${response.status}.` };
    throw new ApiError(error.code, error.message);
  }
  return data as T;
}

/** Where the browser fetches a file of any type; the server always answers "save to disk". */
export const fileUrl = (path: string) => `/api/files?path=${encodeURIComponent(path)}`;

/** Store a file of any type. Replacing one needs the version it has now. */
export async function upload(path: string, file: File, version?: string): Promise<void> {
  const headers = { "Content-Type": "application/octet-stream", ...(version ? { "If-Match": `"${version}"` } : {}) };
  await answer(await fetch(fileUrl(path), { method: "PUT", credentials: "same-origin", headers, body: file }));
}

export const when = (seconds: number | null) =>
  seconds ? new Date(seconds * 1000).toLocaleString() : "never";

export const message = (failure: unknown) => (failure instanceof ApiError ? failure.message : "Something went wrong.");
export const baseName = (path: string) => path.split("/").filter(Boolean).pop() ?? "/";
export const parent = (path: string) => `/${path.split("/").filter(Boolean).slice(0, -1).join("/")}`;
export const tree = (path: string) => api<Listing>("GET", `/api/tree?path=${encodeURIComponent(path || "/")}`);

export function ago(seconds: number | null): string {
  if (!seconds) return "never";
  const passed = Date.now() / 1000 - seconds;
  if (passed < 60) return "just now";
  if (passed < 3600) return `${Math.floor(passed / 60)} min ago`;
  if (passed < 86400) return `${Math.floor(passed / 3600)} h ago`;
  if (passed < 86400 * 30) return `${Math.floor(passed / 86400)} d ago`;
  return new Date(seconds * 1000).toLocaleDateString();
}

export const bytes = (size: number) =>
  size < 1024 ? `${size} B` : size < 1048576 ? `${(size / 1024).toFixed(1)} KB` : `${(size / 1048576).toFixed(1)} MB`;
