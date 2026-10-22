import assert from 'node:assert/strict';
import test from 'node:test';
import { parseInline, parseMarkdown, safeMarkdownHref } from './markdown.js';

test('formats common Markdown blocks and keeps their text', () => {
  const blocks = parseMarkdown('# Title\n\nA **bold** note and `code`.\n\n- first\n- second\n\n> quoted');
  assert.equal(blocks[0].type, 'heading');
  assert.equal(blocks[0].level, 1);
  assert.equal(blocks[1].type, 'paragraph');
  assert.deepEqual(blocks[1].children.map((token) => token.type), ['text', 'strong', 'text', 'code', 'text']);
  assert.equal(blocks[2].type, 'list');
  assert.equal(blocks[2].items.length, 2);
  assert.equal(blocks[3].type, 'quote');
});

test('renders fenced code and Markdown tables as structured blocks', () => {
  const blocks = parseMarkdown('```python\nprint("safe")\n```\n\n| Name | State |\n| --- | --- |\n| agent | ready |');
  assert.equal(blocks[0].type, 'code-block');
  assert.equal(blocks[0].language, 'python');
  assert.equal(blocks[0].value, 'print("safe")');
  assert.equal(blocks[1].type, 'table');
  assert.equal(blocks[1].headers.length, 2);
  assert.equal(blocks[1].rows[0][0][0].value, 'agent');
});

test('leaves raw HTML as text and blocks unsafe link schemes', () => {
  const tokens = parseInline('<script>alert(1)</script> [unsafe](javascript:alert(1))');
  assert.equal(tokens[0].type, 'text');
  assert.equal(tokens[1].type, 'link');
  assert.equal(tokens[1].href, null);
  assert.equal(safeMarkdownHref('https://example.com'), 'https://example.com/');
  assert.equal(safeMarkdownHref('data:text/html,unsafe'), null);
});

test('supports only explicitly allowed external link protocols', () => {
  assert.equal(safeMarkdownHref('http://example.com'), 'http://example.com/');
  assert.equal(safeMarkdownHref('mailto:help@example.com'), 'mailto:help@example.com');
  assert.equal(safeMarkdownHref('/relative/path'), null);
});
