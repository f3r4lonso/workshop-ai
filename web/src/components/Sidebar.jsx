import { memo } from 'react';
import { NAV } from '../constants.js';

/** Navy sidebar: brand, the seven sections (with counts where they list resources) and the workspace folder. */
function Sidebar({ counts, current, onNavigate, workshopRoot, loading }) {
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
