import { ClientIcon } from './Icons.jsx';

const PRIORITY = [
  ['claude', 'Claude'],
  ['codex', 'Codex'],
  ['copilot', 'Copilot'],
  ['gemini', 'Gemini'],
];

export default function ClientLaunchers({ clients, loading, error, launchState, onLaunch }) {
  const byId = new Map((clients || []).map((client) => [client.id, client]));
  return (
    <section className="clients" aria-labelledby="client-launcher-title">
      <h2 id="client-launcher-title" className="clients-title">Abrir consola</h2>
      <p className="clients-note">Elige dónde continuar tu trabajo.</p>
      {error ? <p className="client-error-text" role="alert">{error}</p> : null}
      <ul className="clients-list">
        {PRIORITY.map(([id, label]) => {
          const client = byId.get(id);
          const state = launchState?.[id];
          const busy = state?.phase === 'busy';
          const installed = client?.installed === true;
          const name = client?.name || label;
          return (
            <li key={id}>
              <button type="button" className="client-button" disabled={loading || !client || !installed || busy}
                aria-label={`Abrir consola de ${name}`}
                title={client && !installed && !loading ? `${name}: no instalado` : undefined}
                onClick={() => onLaunch({ ...client, console: true })}>
                <ClientIcon id={id} name={name} />
                <span className="client-text">
                  <span className="client-name">{label}</span>
                  <span className="client-state">
                    {loading ? 'Comprobando…' : busy ? 'Abriendo…' : !client ? 'No comprobado' : installed ? 'Disponible' : 'No instalado'}
                  </span>
                </span>
              </button>
              {state?.phase === 'error' ? <p className="client-error-text" role="status">{state.message}</p> : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
