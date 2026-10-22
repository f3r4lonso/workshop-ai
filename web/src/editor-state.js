export function replaceHeaderField(text, field, value, allowedFields) {
  if (!allowedFields.includes(field) || !/^[A-Za-z][A-Za-z0-9]*$/.test(field)) return null;
  const lines = text.split(/(?<=\n)/);
  if (!/^---\r?\n$/.test(lines[0] || '')) return null;
  const end = lines.findIndex((line, index) => index > 0 && /^---(?:\r?\n)?$/.test(line));
  if (end < 0) return null;
  const indexes = lines.map((line, index) => index > 0 && index < end && line.startsWith(`${field}:`) ? index : -1).filter(index => index >= 0);
  if (indexes.length !== 1) return null;
  const index = indexes[0];
  const ending = lines[index].endsWith('\r\n') ? '\r\n' : lines[index].endsWith('\n') ? '\n' : '';
  lines[index] = `${field}: ${JSON.stringify(value)}${ending}`;
  return lines.join('');
}

export function changedLines(before, after) {
  const oldLines = before.split('\n');
  const newLines = after.split('\n');
  let start = 0;
  while (start < oldLines.length && start < newLines.length && oldLines[start] === newLines[start]) start++;
  let oldEnd = oldLines.length, newEnd = newLines.length;
  while (oldEnd > start && newEnd > start && oldLines[oldEnd - 1] === newLines[newEnd - 1]) { oldEnd--; newEnd--; }
  return { start: start + 1, removed: oldLines.slice(start, oldEnd), added: newLines.slice(start, newEnd) };
}

export function hasCommandOrWebTools(headerLines) {
  return headerLines.split('\n').some(line => {
    const match = line.match(/^tools:\s*(.*)$/);
    if (!match) return false;
    let value = match[1].trim();
    if (value.startsWith('"')) {
      try { value = JSON.parse(value); } catch { /* Keep malformed raw text visible. */ }
    } else if (value.startsWith("'") && value.endsWith("'")) {
      value = value.slice(1, -1).replaceAll("''", "'");
    }
    return /\b(Bash|PowerShell|WebFetch|WebSearch|shell)\b/i.test(String(value));
  });
}
