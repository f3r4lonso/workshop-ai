import { memo } from 'react';
import { NAV, themeKey } from '../constants.js';

/** Inicio: one tile per section that has a count; clicking a tile opens that section. */
function HomeTiles({ counts, activeTasks, onNavigate }) {
  return (
    <ul className="tiles" aria-label="Resumen por sección">
      {NAV.filter(({ name }) => counts.has(name)).map(({ name }) => {
        const isTasks = name === 'Tareas';
        return (
          <li key={name}>
            <button type="button" className={`tile theme-${themeKey(name)}`} onClick={() => onNavigate(name)}>
              <span className="tile-number">
                {isTasks ? activeTasks : counts.get(name)}
                {isTasks ? <span className="tile-of"> de {counts.get(name)}</span> : null}
              </span>
              <span className="tile-label">{isTasks ? 'Tareas activas' : name}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

export default memo(HomeTiles);
