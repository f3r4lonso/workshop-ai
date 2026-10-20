import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { test } from 'node:test';
import { clientStates, detectClients, findOnPath, readConfirmed } from '../clients';
import { locateInfra } from '../infra';
import { isTaskId, plainText } from '../text';
import { findPython, parseWaiOutput, waiArgs, WaiFailure } from '../wai';

function tempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'wai-ext-'));
}

test('task ids follow the wai rule', () => {
  for (const ok of ['t1', 'a', 't2-empty-csv', 'x'.repeat(64)]) {
    assert.ok(isTaskId(ok), ok);
  }
  for (const bad of ['', '-t', 'T1', 't 1', '../x', 'x'.repeat(65), 7, undefined]) {
    assert.ok(!isTaskId(bad), String(bad));
  }
});

test('plainText removes control and bidirectional override characters', () => {
  assert.equal(plainText('a‮b\u0007c\nd⁦e'), 'a b c d e');
  assert.equal(plainText('x'.repeat(10), 5), 'xxxx…');
  assert.equal(plainText(undefined), '');
});

test('EXT-01: detection finds clients on PATH and never runs them', () => {
  const dir = tempDir();
  const marker = path.join(dir, 'marker.txt');
  fs.writeFileSync(path.join(dir, 'claude.cmd'), `@echo ran> "${marker}"\r\n`);
  fs.writeFileSync(path.join(dir, 'claude'), `#!/bin/sh\necho ran > "${marker}"\n`, { mode: 0o755 });
  const env = { PATH: dir, PATHEXT: '.EXE;.CMD' };
  const found = detectClients(env);
  assert.ok(found.claude?.startsWith(dir));
  assert.equal(found.codex, undefined);
  assert.equal(fs.existsSync(marker), false);
});

test('findOnPath honours PATHEXT order and folder order on Windows', () => {
  const first = tempDir();
  const second = tempDir();
  fs.writeFileSync(path.join(first, 'tool.cmd'), '');
  fs.writeFileSync(path.join(second, 'tool.exe'), '');
  const env = { Path: `${first};"${second}"`, PATHEXT: '.EXE;.CMD' };
  assert.equal(findOnPath('tool', env, 'win32'), path.join(first, 'tool.cmd'));
  assert.equal(findOnPath('tool', env, 'win32', ['.exe']), path.join(second, 'tool.exe'));
  assert.equal(findOnPath('missing', env, 'win32'), undefined);
});

test('findOnPath skips relative PATH entries', () => {
  const dir = tempDir();
  fs.writeFileSync(path.join(dir, 'tool.exe'), '');
  const cwd = process.cwd();
  process.chdir(dir);
  try {
    assert.equal(findOnPath('tool', { PATH: '.;bin', PATHEXT: '.EXE' }, 'win32'), undefined);
  } finally {
    process.chdir(cwd);
  }
});

test('pythonPath setting must be an absolute .exe on Windows', () => {
  const dir = tempDir();
  for (const name of ['python.exe', 'python.cmd']) {
    fs.writeFileSync(path.join(dir, name), '');
  }
  assert.equal(findPython(path.join(dir, 'python.exe'), {}, 'win32'), path.join(dir, 'python.exe'));
  assert.equal(findPython(path.join(dir, 'python.cmd'), {}, 'win32'), undefined);
  assert.equal(findPython('python.exe', {}, 'win32'), undefined);
  assert.equal(findPython(undefined, { PATH: dir, PATHEXT: '.CMD;.EXE' }, 'win32'), path.join(dir, 'python.exe'));
});

test('confirmed clients: malformed entries are ignored, overrides are checked', () => {
  const dir = tempDir();
  const exe = path.join(dir, 'codex.exe');
  fs.writeFileSync(exe, '');
  const confirmed = readConfirmed([{ id: 'claude' }, { id: 'claude', path: 'x' }, { id: 'evil' }, 'codex',
    { id: 'codex', path: exe }]);
  assert.deepEqual(confirmed, [{ id: 'claude' }, { id: 'codex', path: exe }]);
  assert.deepEqual(readConfirmed(undefined), []);
  const states = clientStates(confirmed, {});
  assert.deepEqual(states, [
    { id: 'claude', confirmed: true, path: undefined, source: 'not found' },
    { id: 'codex', confirmed: true, path: exe, source: 'path override' },
  ]);
});

test('infra lookup: setting, then WORKSHOP_AI_INFRA, then the default; problems are named', () => {
  const home = tempDir();
  const good = path.join(home, 'workshop', 'infra');
  for (const sub of ['.git', 'clients', 'tasks']) {
    fs.mkdirSync(path.join(good, sub), { recursive: true });
  }
  const other = tempDir();
  assert.deepEqual(locateInfra(undefined, {}, home), { path: good, source: 'default' });
  assert.equal(locateInfra(undefined, { WORKSHOP_AI_INFRA: other }, home).problem, 'not a git repository');
  assert.equal(locateInfra(good, { WORKSHOP_AI_INFRA: other }, home).problem, undefined);
  fs.mkdirSync(path.join(other, '.git'));
  assert.equal(locateInfra(other, {}, home).problem, 'missing clients and tasks folder');
  assert.equal(locateInfra(path.join(other, 'nope'), {}, home).problem, 'folder not found');
});

test('wai arguments: isolated module run, project and infra explicit, positionals after --', () => {
  const cfg = { python: 'python.exe', waiPath: 'P', infra: 'I' };
  assert.deepEqual(waiArgs(cfg, 'R', ['status']),
    ['-E', '-s', '-m', 'workshop_ai', 'status', '--project', 'R', '--infra', 'I', '--json']);
  assert.deepEqual(waiArgs(cfg, 'R', ['task', 'new'], ['--client', 'claude'], ['-t1']).slice(4),
    ['task', 'new', '--project', 'R', '--infra', 'I', '--json', '--client', 'claude', '--', '-t1']);
});

test('wai output: success, JSON error, invalid output', () => {
  assert.deepEqual(parseWaiOutput({ code: 0, stdout: '{"schema": "wai.v1", "tasks": []}\n', stderr: '' }),
    { schema: 'wai.v1', tasks: [] });
  assert.throws(
    () => parseWaiOutput({ code: 4, stdout: '{"schema":"wai.v1","error":{"code":4,"message":"run wai init"}}', stderr: '' }),
    (e: WaiFailure) => e.code === 4 && e.message === 'wai: environment problem (exit 4): run wai init');
  assert.throws(() => parseWaiOutput({ code: 2, stdout: 'usage: wai', stderr: 'wai: error: bad\nmore' }),
    (e: WaiFailure) => e.code === 2 && e.message.includes('unexpected output (exit 2): wai: error: bad more'));
  assert.throws(() => parseWaiOutput({ code: 0, stdout: '{"tasks": []}', stderr: '' }), WaiFailure);
});
