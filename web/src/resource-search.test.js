import assert from 'node:assert/strict';
import test from 'node:test';
import { buildGitHubResourceSearchUrl } from './resource-search.js';

test('prepares an agent repository search on the fixed GitHub origin', () => {
  const url = new URL(buildGitHubResourceSearchUrl('Agentes', 'accessibility review'));
  assert.equal(url.origin, 'https://github.com');
  assert.equal(url.pathname, '/search');
  assert.equal(url.searchParams.get('type'), 'repositories');
  assert.equal(url.searchParams.get('q'), 'AI agent instructions prompt accessibility review in:readme');
});

test('encodes user text as search terms rather than URL parameters', () => {
  const url = new URL(buildGitHubResourceSearchUrl('Skills', 'tests & source'));
  assert.equal(url.searchParams.get('type'), 'repositories');
  assert.equal(url.searchParams.get('q'), 'AI skills SKILL.md instructions tests & source in:readme');
});

test('rejects empty, unsupported and oversized searches', () => {
  assert.throws(() => buildGitHubResourceSearchUrl('Agentes', '  '), TypeError);
  assert.throws(() => buildGitHubResourceSearchUrl('Tareas', 'query'), TypeError);
  assert.throws(() => buildGitHubResourceSearchUrl('Skills', 'x'.repeat(121)), TypeError);
});
