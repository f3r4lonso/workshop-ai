// Display helpers for text that comes from task files or wai output (spec section 8.8: data, never trusted).

export const TASK_ID_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;

export function isTaskId(value: unknown): value is string {
  return typeof value === 'string' && TASK_ID_RE.test(value);
}

// C0/C1 controls (tab and newline become spaces too), and bidirectional mark, override and isolate characters.
const UNSAFE = /[\u0000-\u001f\u007f-\u009f؜‎‏‪-‮⁦-⁩]/g;

export function plainText(value: unknown, limit = 200): string {
  const text = String(value ?? '').replace(UNSAFE, ' ').replace(/\s+/g, ' ').trim();
  return text.length <= limit ? text : text.slice(0, limit - 1) + '…';
}
