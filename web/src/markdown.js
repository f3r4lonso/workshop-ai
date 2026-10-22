const INLINE_PATTERN = /^(?:!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([\s\S]+?)\*\*|__([\s\S]+?)__|~~([^~]+)~~|`([^`]+)`|\*([^*\n]+)\*|_([^_\n]+)_)/;
const FENCE_PATTERN = /^\s*(`{3,}|~{3,})([a-zA-Z0-9_-]*)\s*$/;
const LIST_PATTERN = /^(\s*)([-*+]|\d+[.)])\s+(.+)$/;
const TABLE_RULE_PATTERN = /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/;
const BLOCK_TAG_PATTERN = /^(?:#{1,6}\s|>\s?|(?:[-*_]\s*){3,}$|`{3,}|~{3,}|(?:[-*+]|\d+[.)])\s+)/;

export function safeMarkdownHref(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:', 'mailto:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function parseInline(text) {
  const tokens = [];
  let remaining = text;
  while (remaining) {
    const match = remaining.match(INLINE_PATTERN);
    if (!match) {
      const nextMarker = remaining.slice(1).search(/[\[!*_~`]/);
      const length = nextMarker === -1 ? remaining.length : nextMarker + 1;
      tokens.push({ type: 'text', value: remaining.slice(0, length) });
      remaining = remaining.slice(length);
      continue;
    }

    if (match[1] !== undefined) {
      tokens.push({ type: 'image', value: match[1] });
    } else if (match[3] !== undefined) {
      tokens.push({ type: 'link', value: match[3], href: safeMarkdownHref(match[4]) });
    } else if (match[5] !== undefined || match[6] !== undefined) {
      tokens.push({ type: 'strong', children: parseInline(match[5] ?? match[6]) });
    } else if (match[7] !== undefined) {
      tokens.push({ type: 'del', children: parseInline(match[7]) });
    } else if (match[8] !== undefined) {
      tokens.push({ type: 'code', value: match[8] });
    } else {
      tokens.push({ type: 'em', children: parseInline(match[9] ?? match[10]) });
    }
    remaining = remaining.slice(match[0].length);
  }
  return tokens;
}

function splitTableRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/)
    .map((cell) => cell.trim().replace(/\\\|/g, '|'));
}

function startsBlock(lines, index) {
  return BLOCK_TAG_PATTERN.test(lines[index] || '')
    || (index + 1 < lines.length && lines[index].includes('|') && TABLE_RULE_PATTERN.test(lines[index + 1]));
}

export function parseMarkdown(source) {
  const lines = String(source ?? '').replace(/\r\n?/g, '\n').split('\n');
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index++;
      continue;
    }

    const fence = line.match(FENCE_PATTERN);
    if (fence) {
      const code = [];
      index++;
      while (index < lines.length && !new RegExp(`^\\s*${fence[1][0]}{${fence[1].length},}\\s*$`).test(lines[index])) {
        code.push(lines[index++]);
      }
      if (index < lines.length) index++;
      blocks.push({ type: 'code-block', language: fence[2], value: code.join('\n') });
      continue;
    }

    const heading = line.match(/^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/);
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, children: parseInline(heading[2]) });
      index++;
      continue;
    }

    if (/^\s{0,3}(?:(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,})$/.test(line)) {
      blocks.push({ type: 'rule' });
      index++;
      continue;
    }

    if (/^\s{0,3}>\s?/.test(line)) {
      const quote = [];
      while (index < lines.length && /^\s{0,3}>\s?/.test(lines[index])) {
        quote.push(lines[index++].replace(/^\s{0,3}>\s?/, ''));
      }
      blocks.push({ type: 'quote', children: parseMarkdown(quote.join('\n')) });
      continue;
    }

    if (index + 1 < lines.length && line.includes('|') && TABLE_RULE_PATTERN.test(lines[index + 1])) {
      const headers = splitTableRow(line).map(parseInline);
      index += 2;
      const rows = [];
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        rows.push(splitTableRow(lines[index++]).map(parseInline));
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }

    const list = line.match(LIST_PATTERN);
    if (list) {
      const ordered = /^\d/.test(list[2]);
      const indent = list[1].length;
      const items = [];
      while (index < lines.length) {
        const item = lines[index].match(LIST_PATTERN);
        if (!item || item[1].length !== indent || /^\d/.test(item[2]) !== ordered) break;
        items.push(parseInline(item[3]));
        index++;
      }
      blocks.push({ type: 'list', ordered, items });
      continue;
    }

    const paragraph = [line.trim()];
    index++;
    while (index < lines.length && lines[index].trim() && !startsBlock(lines, index)) {
      paragraph.push(lines[index++].trim());
    }
    blocks.push({ type: 'paragraph', children: parseInline(paragraph.join(' ')) });
  }

  return blocks;
}
