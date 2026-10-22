const SEARCH_TOPICS = {
  Agentes: 'AI agent instructions prompt',
  Skills: 'AI skills SKILL.md instructions',
};

export function buildGitHubResourceSearchUrl(kind, terms) {
  if (!Object.hasOwn(SEARCH_TOPICS, kind) || typeof terms !== 'string' || !terms.trim() || terms.length > 120) {
    throw new TypeError('Indica si buscas agentes o skills y escribe hasta 120 caracteres.');
  }
  const url = new URL('https://github.com/search');
  url.searchParams.set('q', `${SEARCH_TOPICS[kind]} ${terms.trim()} in:readme`);
  url.searchParams.set('type', 'repositories');
  return url.href;
}
