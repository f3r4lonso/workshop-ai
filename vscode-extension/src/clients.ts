// Client detection (spec section 4, EXT-01): a PATH lookup only. Nothing found here is ever run.

import * as fs from 'node:fs';
import * as path from 'node:path';

export const CLIENT_IDS = ['claude', 'codex'] as const;
export type ClientId = (typeof CLIENT_IDS)[number];
export const CLIENT_NAMES: Record<ClientId, string> = { claude: 'Claude Code', codex: 'Codex CLI' };

export type Env = Record<string, string | undefined>;

export interface ConfirmedClient {
  id: ClientId;
  path?: string;
}

export interface ClientState {
  id: ClientId;
  confirmed: boolean;
  path?: string;
  source: 'path override' | 'found on PATH' | 'not found';
}

export function isClientId(value: unknown): value is ClientId {
  return typeof value === 'string' && (CLIENT_IDS as readonly string[]).includes(value);
}

export function envGet(env: Env, key: string, platform = process.platform): string | undefined {
  if (platform !== 'win32') {
    return env[key];
  }
  const match = Object.keys(env).find((k) => k.toUpperCase() === key.toUpperCase());
  return match === undefined ? undefined : env[match];
}

export function isFile(file: string): boolean {
  try {
    return fs.statSync(file).isFile();
  } catch {
    return false;
  }
}

// First file named `name` (plus a PATHEXT extension on Windows) in the PATH folders, without running it.
// Relative PATH entries are skipped: they would resolve against whatever the current folder is (a project).
export function findOnPath(name: string, env: Env, platform = process.platform, extensions?: string[]): string | undefined {
  const isAbsolute = platform === 'win32' ? path.win32.isAbsolute : path.posix.isAbsolute;
  const dirs = (envGet(env, 'PATH', platform) ?? '').split(platform === 'win32' ? ';' : ':')
    .map((dir) => dir.replace(/^"(.*)"$/, '$1'))
    .filter((dir) => dir && isAbsolute(dir));
  const exts = extensions ?? (platform === 'win32'
    ? (envGet(env, 'PATHEXT', platform) ?? '.COM;.EXE;.BAT;.CMD').split(';').filter(Boolean)
    : ['']);
  for (const dir of dirs) {
    for (const ext of exts) {
      const candidate = path.join(dir, name + ext.toLowerCase());
      if (isFile(candidate)) {
        return candidate;
      }
    }
  }
  return undefined;
}

export function detectClients(env: Env, platform = process.platform): Partial<Record<ClientId, string>> {
  const found: Partial<Record<ClientId, string>> = {};
  for (const id of CLIENT_IDS) {
    const file = findOnPath(id, env, platform);
    if (file) {
      found[id] = file;
    }
  }
  return found;
}

// Keep only well-formed entries from the user setting; the first entry per client wins.
export function readConfirmed(setting: unknown): ConfirmedClient[] {
  const result: ConfirmedClient[] = [];
  for (const entry of Array.isArray(setting) ? setting : []) {
    const id = entry?.id;
    if (isClientId(id) && !result.some((c) => c.id === id)) {
      result.push(typeof entry.path === 'string' && entry.path ? { id, path: entry.path } : { id });
    }
  }
  return result;
}

export function clientStates(confirmed: ConfirmedClient[], detected: Partial<Record<ClientId, string>>): ClientState[] {
  return CLIENT_IDS.map((id) => {
    const entry = confirmed.find((c) => c.id === id);
    if (entry?.path) {
      return { id, confirmed: true, path: entry.path, source: isFile(entry.path) ? 'path override' : 'not found' };
    }
    const found = detected[id];
    return { id, confirmed: entry !== undefined, path: found, source: found ? 'found on PATH' : 'not found' };
  });
}
