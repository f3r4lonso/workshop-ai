// Spec checks that need the real wai, the manifest or the source tree (EXT-04, EXT-09, section 8.6).

import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import { test } from 'node:test';
import { findPython, findWaiFolder, runWai, WaiFailure } from '../wai';

const extensionRoot = path.resolve(__dirname, '..', '..');
const manifest = JSON.parse(fs.readFileSync(path.join(extensionRoot, 'package.json'), 'utf8'));

function tempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'wai-ext-'));
}

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? sourceFiles(path.join(dir, e.name)) : e.name.endsWith('.ts') ? [path.join(dir, e.name)] : []);
}

test('manifest: Restricted Mode off, no * activation, no runtime dependencies', () => {
  assert.equal(manifest.capabilities.untrustedWorkspaces.supported, false);
  assert.ok(!(manifest.activationEvents ?? []).includes('*'));
  assert.equal(manifest.dependencies, undefined);
  assert.deepEqual(Object.keys(manifest.devDependencies).sort(), ['@types/node', '@types/vscode', 'typescript']);
});

test('EXT-09: path settings are machine-scoped', () => {
  const props = manifest.contributes.configuration.properties;
  for (const key of ['workshopAi.waiPath', 'workshopAi.pythonPath', 'workshopAi.infraPath', 'workshopAi.clients']) {
    assert.equal(props[key].scope, 'machine', key);
  }
});

test('manifest strings all resolve in package.nls.json', () => {
  const nls = JSON.parse(fs.readFileSync(path.join(extensionRoot, 'package.nls.json'), 'utf8'));
  const keys = [...JSON.stringify(manifest).matchAll(/"%([^%"]+)%"/g)].map((m) => m[1]);
  assert.ok(keys.length > 10);
  for (const key of keys) {
    assert.ok(key in nls, key);
  }
});

test('EXT-04: the source never writes to a terminal', () => {
  const banned = ['send' + 'Text', 'shell' + 'Integration'];
  for (const file of sourceFiles(path.join(extensionRoot, 'src'))) {
    const text = fs.readFileSync(file, 'utf8');
    for (const word of banned) {
      assert.ok(!text.includes(word), `${word} in ${file}`);
    }
  }
});

const waiPath = findWaiFolder(undefined, extensionRoot);
const python = findPython(undefined, process.env);

test('EXT-09: a fake workshop_ai in the project and PYTHONPATH cannot replace wai; journey through real wai',
  { skip: !waiPath || !python ? 'wai or python not found' : false }, async () => {
    const tmp = tempDir();
    const project = path.join(tmp, 'project');
    const marker = path.join(tmp, 'marker.txt');
    fs.mkdirSync(path.join(project, 'workshop_ai'), { recursive: true });
    for (const name of ['__init__.py', '__main__.py']) {
      fs.writeFileSync(path.join(project, 'workshop_ai', name),
        `open(${JSON.stringify(marker)}, "w").write("fake wai ran")\n`);
    }
    fs.writeFileSync(path.join(project, 'notes.txt'), 'hello\n');
    const cfg = { python: python!, waiPath: waiPath!, infra: path.join(tmp, 'no-infra') };
    const saved = process.env.PYTHONPATH;
    process.env.PYTHONPATH = project;
    const logged: string[] = [];
    try {
      await assert.rejects(runWai(cfg, project, ['status']), (e: WaiFailure) => e.code === 4);
      assert.equal((await runWai(cfg, project, ['init'])).created, true);
      assert.deepEqual((await runWai(cfg, project, ['status'])).tasks, []);
      const created = await runWai(cfg, project, ['task', 'new'], ['--client', 'claude', '--no-edit'], ['t1'], undefined,
        (line) => logged.push(line));
      assert.equal(created.task_file, '.workshop-ai/tasks/t1/task.md');
      const context = await runWai(cfg, project, ['context', 'add'], [], ['t1', 'notes.txt']);
      assert.deepEqual(context.context, ['notes.txt']);
      await assert.rejects(runWai(cfg, project, ['context', 'add'], [], ['t1', '../outside.txt']),
        (e: WaiFailure) => e.code === 3);
      const status = await runWai(cfg, project, ['status']);
      assert.equal((status.tasks as { id: string }[])[0].id, 't1');
    } finally {
      if (saved === undefined) {
        delete process.env.PYTHONPATH;
      } else {
        process.env.PYTHONPATH = saved;
      }
    }
    assert.equal(fs.existsSync(marker), false, 'the fake workshop_ai ran');
    assert.deepEqual(logged, ['wai task new -> exit 0']);
  });
