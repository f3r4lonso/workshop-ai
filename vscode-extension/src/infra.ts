// Locating the shared infrastructure clone (spec J1 step 4). E1 reuses an existing clone only; it never clones.

import * as fs from 'node:fs';
import * as path from 'node:path';
import { Env, envGet } from './clients';

export interface InfraLookup {
  path: string;
  source: 'setting' | 'WORKSHOP_AI_INFRA' | 'default';
  problem?: string;
}

function exists(file: string, dir: boolean): boolean {
  try {
    const stat = fs.statSync(file);
    return dir ? stat.isDirectory() : true;
  } catch {
    return false;
  }
}

export function infraProblem(folder: string): string | undefined {
  if (!exists(folder, true)) {
    return 'folder not found';
  }
  if (!exists(path.join(folder, '.git'), false)) {
    return 'not a git repository';
  }
  const missing = ['clients', 'tasks'].filter((sub) => !exists(path.join(folder, sub), true));
  return missing.length ? `missing ${missing.join(' and ')} folder` : undefined;
}

export function locateInfra(setting: string | undefined, env: Env, home: string): InfraLookup {
  const fromEnv = envGet(env, 'WORKSHOP_AI_INFRA');
  const lookup: InfraLookup = setting
    ? { path: setting, source: 'setting' }
    : fromEnv
      ? { path: fromEnv, source: 'WORKSHOP_AI_INFRA' }
      : { path: path.join(home, 'workshop', 'infra'), source: 'default' };
  lookup.path = path.resolve(lookup.path);
  const problem = infraProblem(lookup.path);
  return problem ? { ...lookup, problem } : lookup;
}
