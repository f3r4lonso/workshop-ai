import assert from 'node:assert/strict';
import { test } from 'node:test';
import { replaceHeaderField, changedLines, hasCommandOrWebTools } from './editor-state.js';
test('scalar form edit preserves unknown fields, comments, body and CRLF', () => {
 const source='---\r\nname: old\r\nunknown: keep # exact\r\n---\r\nname: body\r\n';
 assert.equal(replaceHeaderField(source,'name','new "quoted"',['name']), '---\r\nname: "new \\"quoted\\""\r\nunknown: keep # exact\r\n---\r\nname: body\r\n'.replaceAll('\\\\"','\\"'));
});
test('ambiguous, missing or unapproved fields cannot use the scalar form', () => {
 assert.equal(replaceHeaderField('---\nname: a\nname: b\n---\n','name','c',['name']),null);
 assert.equal(replaceHeaderField('---\nunknown: a\n---\n','unknown','c',['name']),null);
 assert.equal(replaceHeaderField('name: body','name','c',['name']),null);
});
test('review isolates changed region and preserves additions/deletions', () => {
 assert.deepEqual(changedLines('a\nb\nc','a\nx\ny\nc'),{start:2,removed:['b'],added:['x','y']});
 assert.deepEqual(changedLines('a','a'),{start:2,removed:[],added:[]});
});
test('capability warning decodes quoted tools without executing content', () => {
 assert.equal(hasCommandOrWebTools('tools: "\\u0042ash, Read"'), true);
 assert.equal(hasCommandOrWebTools("tools: 'Read, WebFetch'"), true);
 assert.equal(hasCommandOrWebTools('tools: Read, Edit'), false);
});
