import { memo } from 'react';
import { NAV } from '../constants.js';
import ClientLaunchers from './ClientLaunchers.jsx';

/** Navy sidebar: brand, the seven sections (with counts where they list resources) and the workspace folder. */
function Sidebar({ counts, current, onNavigate, workshopRoot, loading, onShortcut, onEditNotes,
  clients, clientsLoading, clientsError, launchState, onLaunch, draftItem, onResumeDraft }) {
  return (
    <div className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          W
        </span>
        <span className="brand-text">
          <span className="brand-name">Workshop AI</span>
          <span className="brand-tagline">Todo lo que tengo</span>
        </span>
      </div>

      <nav className="nav" aria-label="Secciones">
        <ul>
          {NAV.map(({ name }) => {
            const isCurrent = name === current;
            const count = counts.get(name);
            return (
              <li key={name}>
                <button
                  type="button"
                  className="nav-item"
                  aria-current={isCurrent ? 'page' : undefined}
                  onClick={() => onNavigate(name)}
                >
                  <span className="nav-label">{name}</span>
                  {count === undefined ? null : loading ? (
                    <span className="nav-count nav-count--loading" aria-hidden="true" />
                  ) : (
                    <span className="nav-count">
                      {count}
                      <span className="sr-only"> elementos</span>
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      {draftItem ? <div className="sidebar-draft">
        <span>Hay un borrador sin guardar</span>
        <button type="button" onClick={onResumeDraft}>Volver al borrador</button>
      </div> : null}

      <ClientLaunchers clients={clients} loading={clientsLoading} error={clientsError}
        launchState={launchState} onLaunch={onLaunch} />

      <div className="sidebar-shortcuts">
        <strong><svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M6 3h14v18H6zM3 7h6M3 12h6M3 17h6" /></svg> Mis notas</strong><p>Tu bloc de ideas</p>
        <button type="button" onClick={() => onShortcut('notes-open')}>Abrir en Bloc de notas</button>
        <button type="button" onClick={onEditNotes}>Editar aquí</button>
        <button type="button" onClick={() => onShortcut('open-workshop')}><svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 6h7l2 3h9v11H3z" /></svg> Abrir Workshop</button>
      </div>
      {workshopRoot ? (
        <div className="root-folder">
          <span className="root-folder-label">Carpeta workshop</span>
          <span className="root-folder-path">{workshopRoot}</span>
        </div>
      ) : null}
    </div>
  );
}

export default memo(Sidebar);
