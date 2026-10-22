import { useState } from 'react';
import { buildGitHubResourceSearchUrl } from '../resource-search.js';

export default function ResourceDiscovery() {
  const [kind, setKind] = useState('Skills');
  const [terms, setTerms] = useState('');
  const [url, setUrl] = useState('');

  function prepare(event) {
    event.preventDefault();
    if (!terms.trim()) {
      setUrl('');
      return;
    }
    setUrl(buildGitHubResourceSearchUrl(kind, terms));
  }

  return (
    <section className="resource-tool resource-discovery" aria-labelledby="resource-search-title">
      <div className="resource-tool-heading">
        <div>
          <h2 id="resource-search-title">Buscar agentes y skills en Internet</h2>
          <p>Prepara una búsqueda de repositorios públicos. Workshop no descarga ni instala resultados.</p>
        </div>
        <span className="resource-tool-tag">Búsqueda manual</span>
      </div>
      <form className="discovery-form" onSubmit={prepare}>
        <label htmlFor="resource-search-kind">Qué quieres buscar</label>
        <select id="resource-search-kind" value={kind} onChange={(event) => {
          setKind(event.target.value);
          setUrl('');
        }}>
          <option>Skills</option>
          <option>Agentes</option>
        </select>
        <label htmlFor="resource-search-terms">Describe lo que necesitas</label>
        <div className="discovery-controls">
          <input id="resource-search-terms" type="search" maxLength={120} value={terms}
            onChange={(event) => { setTerms(event.target.value); setUrl(''); }}
            placeholder={kind === 'Agentes' ? 'p. ej., auditoría de accesibilidad' : 'p. ej., pruebas de React'} />
          <button type="submit" className="button button--primary" disabled={!terms.trim()}>
            Preparar búsqueda
          </button>
        </div>
      </form>
      {url ? <div className="discovery-result" role="status">
        <p>La búsqueda está lista. Se abrirá GitHub en una pestaña nueva; no se enviaron tus datos desde Workshop.</p>
        <a className="button" href={url} target="_blank" rel="noopener noreferrer">
          Ver resultados de {kind} en GitHub<span className="sr-only"> (se abre en una pestaña nueva)</span>
        </a>
      </div> : null}
      <p className="discovery-caution">Antes de reutilizar un resultado, revisa autoría, licencia, actividad, dependencias y permisos.</p>
    </section>
  );
}
