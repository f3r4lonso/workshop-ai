// Running wai (spec section 3.2). Invocation rule EXT-09: `<python> -E -s -m workshop_ai ...` with the working
// folder set to the product folder, never the project folder; argument arrays only, no shell.

import { execFile } from 'node:child_process';
import * as path from 'node:path';
import { Env, findOnPath, isFile } from './clients';

export const EXIT_MEANING: Record<number, string> = {
  1: 'usage error or not found',
  2: 'validation failed',
  3: 'refused',
  4: 'environment problem',
};

export interface WaiConfig {
  python: string;
  waiPath: string;
  infra: string;
}

export interface ExecResult {
  code: number;
  stdout: string;
  stderr: string;
}

export type Exec = (file: string, args: string[], cwd: string) => Promise<ExecResult>;

export class WaiFailure extends Error {
  constructor(message: string, readonly code?: number) {
    super(message);
  }
}

const TIMEOUT_MS = 60_000;

export const nodeExec: Exec = (file, args, cwd) =>
  new Promise((resolve, reject) => {
    try {
      execFile(file, args, { cwd, windowsHide: true, timeout: TIMEOUT_MS, maxBuffer: 4 * 1024 * 1024, encoding: 'utf8' },
        (error, stdout, stderr) => {
          if (error?.killed) {
            reject(new WaiFailure(`${path.basename(file)} was stopped after ${TIMEOUT_MS / 1000} s without finishing`));
          } else if (error && typeof error.code !== 'number') {
            reject(new WaiFailure(`could not run ${path.basename(file)}: ${error.code ?? error.message}`));
          } else {
            resolve({ code: error ? (error.code as number) : 0, stdout, stderr });
          }
        });
    } catch (error) {
      // e.g. EINVAL: Node refuses to run a .cmd/.bat file without a shell.
      reject(new WaiFailure(`could not run ${path.basename(file)}: ${(error as NodeJS.ErrnoException).code ?? error}`));
    }
  });

// The product folder: the setting, else the folder above the extension (vscode-extension/ lives in the product).
export function findWaiFolder(setting: string | undefined, extensionPath: string): string | undefined {
  const folder = path.resolve(setting || path.join(extensionPath, '..'));
  return isFile(path.join(folder, 'workshop_ai', '__main__.py')) ? folder : undefined;
}

// Python must be a real executable: a .cmd/.bat shim would need a shell (spec section 8.7).
export function findPython(setting: string | undefined, env: Env, platform = process.platform): string | undefined {
  if (setting) {
    const exeOnly = platform !== 'win32' || path.extname(setting).toLowerCase() === '.exe';
    return exeOnly && path.isAbsolute(setting) && isFile(setting) ? setting : undefined;
  }
  return platform === 'win32' ? findOnPath('python', env, platform, ['.exe']) : findOnPath('python3', env, platform);
}

export function waiArgs(cfg: WaiConfig, project: string, command: string[], options: string[] = [],
  positionals: string[] = []): string[] {
  const args = ['-E', '-s', '-m', 'workshop_ai', ...command, '--project', project, '--infra', cfg.infra, '--json',
    ...options];
  return positionals.length ? [...args, '--', ...positionals] : args;
}

export async function checkWai(cfg: WaiConfig, exec: Exec = nodeExec): Promise<string> {
  const result = await exec(cfg.python, ['-E', '-s', '-m', 'workshop_ai', '--version'], cfg.waiPath);
  const version = result.stdout.trim();
  if (result.code !== 0 || !version.startsWith('wai ')) {
    throw new WaiFailure(`wai did not start (exit ${result.code})`, result.code);
  }
  return version;
}

export function parseWaiOutput(result: ExecResult): Record<string, unknown> {
  let payload: unknown;
  try {
    payload = JSON.parse(result.stdout.trim());
  } catch {
    payload = undefined;
  }
  if (typeof payload !== 'object' || payload === null || (payload as { schema?: unknown }).schema !== 'wai.v1') {
    const first = result.stderr.trim().split(/\r?\n/).slice(0, 3).join(' ');
    throw new WaiFailure(`wai returned unexpected output (exit ${result.code})${first ? `: ${first}` : ''}`,
      result.code);
  }
  const body = payload as Record<string, unknown>;
  const error = body.error as { code?: unknown; message?: unknown } | undefined;
  if (error || result.code !== 0) {
    const code = typeof error?.code === 'number' ? error.code : result.code;
    const meaning = EXIT_MEANING[code] ?? 'failed';
    throw new WaiFailure(`wai: ${meaning} (exit ${code}): ${String(error?.message ?? '')}`.trim(), code);
  }
  return body;
}

export async function runWai(cfg: WaiConfig, project: string, command: string[], options: string[] = [],
  positionals: string[] = [], exec: Exec = nodeExec, log?: (line: string) => void): Promise<Record<string, unknown>> {
  const result = await exec(cfg.python, waiArgs(cfg, project, command, options, positionals), cfg.waiPath);
  // The log names the command and its exit code only, never task text or file contents (spec section 8.2).
  log?.(`wai ${command.join(' ')} -> exit ${result.code}`);
  return parseWaiOutput(result);
}
