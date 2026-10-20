import ResourceInteraction from './ResourceInteraction.jsx';

/** The selected-resource panel is the reading assistant (Lector). Agent chains live in Conversar. */
export default function DetailPanel({ item, panelRef, onBackToList }) {
  return (
    <aside ref={panelRef} className="detail reader-detail" aria-label="Lector">
      {item ? <button type="button" className="back-link" onClick={onBackToList}>
        <span aria-hidden="true">↑ </span>Volver a los recursos
      </button> : null}
      <ResourceInteraction key={item?.id || 'no-selection'} item={item} />
    </aside>
  );
}
