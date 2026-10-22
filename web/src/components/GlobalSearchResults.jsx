import { formatDate } from '../constants.js';

const KIND_LABELS = {
  resource: 'Contenido actual',
  version: 'Versión anterior',
  conversation: 'Conversación',
};

export default function GlobalSearchResults({ query, state, onOpen }) {
  return (
    <section className="global-search-results" aria-labelledby="global-search-title">
      <div className="global-search-heading">
        <div>
          <h2 id="global-search-title">Coincidencias en el Workshop</h2>
          <p>Resultados en documentos, tareas, conversaciones guardadas y versiones.</p>
        </div>
        {state.status === 'loading' ? <span role="status">Buscando…</span> : null}
      </div>

      {state.status === 'error' ? <p className="chat-error" role="alert">{state.message}</p> : null}
      {state.status === 'ready' && !state.results.length
        ? <p className="global-search-empty">No hay coincidencias para «{query}».</p> : null}

      {state.results.length ? <ul className="global-search-list" aria-label="Resultados globales">
        {state.results.map((result) => {
          const key = `${result.kind}:${result.item_id || result.conversation_id}:${result.version_id || ''}`;
          const date = result.modified ? formatDate(result.modified) : '';
          return <li key={key}>
            <button type="button" className="global-search-result" onClick={() => onOpen(result)}>
              <span className="global-search-result-meta">
                <span className={`global-search-kind global-search-kind--${result.kind}`}>
                  {KIND_LABELS[result.kind] || 'Resultado'}
                </span>
                {result.section ? <span>{result.section}</span> : null}
                {date ? <time dateTime={result.modified}>{date}</time> : null}
              </span>
              <strong>{result.title}</strong>
              {result.path ? <span className="global-search-path">{result.path}</span> : null}
              <span className="global-search-excerpt">{result.excerpt}</span>
            </button>
          </li>;
        })}
      </ul> : null}

      {state.status === 'ready' && (state.partial || state.skipped) ? <p className="global-search-note">
        {state.partial ? 'La búsqueda alcanzó su límite de lectura; puede haber más resultados.' : ''}
        {state.partial && state.skipped ? ' ' : ''}
        {state.skipped ? `Se omitieron ${state.skipped} archivos protegidos o no disponibles.` : ''}
      </p> : null}
    </section>
  );
}
