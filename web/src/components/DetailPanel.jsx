import DocumentEditor from './DocumentEditor.jsx';

/** The editor receives retained drafts from App. Agent chains live in Conversar. */
export default function DetailPanel({ item, panelRef, onBackToList, draft, onDraft, onCreated, onDiscard, initialVersionId, onVersionOpened }) {
  return (
    <aside ref={panelRef} className="detail document-detail" aria-label="Editor de documentos">
      <button type="button" className="back-link" onClick={onBackToList}>
        <span aria-hidden="true">↑ </span>Volver a los recursos
      </button>
      <DocumentEditor key={item?.id || 'no-selection'} item={item} draft={draft} onDraft={onDraft} onCreated={onCreated} onDiscard={onDiscard}
        initialVersionId={initialVersionId} onVersionOpened={onVersionOpened} />
    </aside>
  );
}
