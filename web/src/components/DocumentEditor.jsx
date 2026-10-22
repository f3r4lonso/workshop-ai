import { useEffect, useEffectEvent, useRef, useState } from 'react';
import { interaction } from '../api.js';
import { replaceHeaderField, changedLines, hasCommandOrWebTools } from '../editor-state.js';
import MarkdownPreview from './MarkdownPreview.jsx';

const hashOf = result => result.base_sha256 || result.version || result.sha256;
async function call(action, body) {
  const result = await interaction(action, body);
  if (!result.ok) { const error = new Error(result.message || result.reason || 'Operación rechazada.'); error.result = result; throw error; }
  return result;
}
function Comparison({ before, after }) {
  const diff = changedLines(before, after);
  return <><p>Cambios desde la línea {diff.start}: {diff.removed.length} líneas anteriores, {diff.added.length} líneas propuestas.</p><pre className="editor-diff" aria-label="Diferencias del texto">{[...diff.removed.map(line => `− ${line}`), ...diff.added.map(line => `+ ${line}`)].join('\n') || 'Sin diferencias'}</pre><div className="editor-comparison"><section><h4>Archivo actual</h4><pre>{before || '(vacío)'}</pre></section><section><h4>Texto propuesto</h4><pre>{after || '(vacío)'}</pre></section></div></>;
}
function CapabilityReview({ before, after }) {
  function lines(text) {
    const header = text.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1] || '';
    return header.split('\n').filter(line => /^(tools|model|disallowedTools):/.test(line)).join('\n');
  }
  const previous = lines(before), proposed = lines(after);
  if (!previous && !proposed) return null;
  return <section className="editor-capabilities"><h4>Herramientas y modelo · revisión específica</h4><Comparison before={previous} after={proposed} />
    {hasCommandOrWebTools(proposed) ? <p className="editor-error">Estas herramientas permiten ejecutar comandos o acceder a la web. Revisa si el recurso necesita esos permisos.</p> : null}</section>;
}
export default function DocumentEditor({ item, draft, onDraft, onCreated, onDiscard, initialVersionId = '', onVersionOpened }) {
  const [tab, setTab] = useState('edit');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [versions, setVersions] = useState([]);
  const [version, setVersion] = useState(null);
  const [templates, setTemplates] = useState(null);
  const [templateId, setTemplateId] = useState('');
  const [createPath, setCreatePath] = useState('');
  const [destinations, setDestinations] = useState([]);
  const [destination, setDestination] = useState('');
  const [newFileName, setNewFileName] = useState('');
  const [toolsReviewed, setToolsReviewed] = useState(false);
  const [previewMode, setPreviewMode] = useState('formatted');
  const alive = useRef(true);
  const inFlight = useRef(false);
  const loadGeneration = useRef(0);
  const id = item?.id;
  const action = name => item?.privateNotes ? `notes-${name}` : name;
  const payload = extra => ({ ...(item?.privateNotes ? {} : item?.documentPath ? { path: item.documentPath } : { id }), ...extra });
  const update = next => onDraft(id, next);
  const canEdit = draft && draft.meta.editable !== false && draft.meta.can_edit !== false;
  const locked = busy || draft?.saving;
  useEffect(() => { alive.current = true; return () => { alive.current = false; loadGeneration.current++; }; }, []);
  function accept(result, status = 'Sin cambios') {
    onDraft(id, { text: result.text ?? '', original: result.text ?? '', base_sha256: hashOf(result), meta: result, dirty: false, status, scroll: 0 });
  }
  async function load(force = false) {
    if (!id || item?.isNew || (!force && draft) || !item.canOpenDocument) return;
    const generation = ++loadGeneration.current;
    setBusy(true); setError('');
    try { const result = await call(action('document'), payload()); if (alive.current && generation === loadGeneration.current) accept(result); }
    catch (failure) { if (alive.current && generation === loadGeneration.current) setError(failure.message); }
    finally { if (alive.current && generation === loadGeneration.current) setBusy(false); }
  }
  useEffect(() => { load(); }, [id]);
  function edit(text) {
    update(previous => ({ ...previous, text, dirty: text !== previous.original, status: text === previous.original ? 'Sin cambios' : 'Cambios sin guardar', reviewed: false, header_fields: null, advanced: true }));
    setToolsReviewed(false);
  }
  function editField(field, value) {
    if (!draft.meta.header.editable_fields?.includes(field)) return;
    const text = replaceHeaderField(draft.text, field, value, draft.meta.header.editable_fields);
    if (text === null) { setError('Este campo requiere edición avanzada en el documento.'); return; }
    update(previous => ({ ...previous, text, dirty: text !== previous.original, reviewed: false,
      header_fields: { ...previous.header_fields, [field]: value }, status: 'Cambios sin guardar' }));
    setToolsReviewed(false);
  }
  function review() {
    if (!draft?.dirty || locked || !canEdit) return;
    update(previous => ({ ...previous, reviewed: true })); setTab('review');
  }
  async function save() {
    if (inFlight.current || !draft?.dirty || !canEdit || draft.conflict) return;
    if (!draft.reviewed || tab !== 'review') { review(); return; }
    if (item?.isNew) {
      await openSaveAs();
      return;
    }
    if (draft.meta.header?.raw_header && !toolsReviewed) { setError('Confirma la revisión de herramientas y modelo.'); return; }
    inFlight.current = true; update(previous => ({ ...previous, saving: true, status: 'Guardando…' })); setError('');
    try {
      const result = await call(action('save'), payload({ text: draft.text, base_sha256: draft.base_sha256, review_tools_model: toolsReviewed }));
      onDraft(id, previous => ({ ...previous, original: result.text ?? draft.text, text: result.text ?? draft.text,
        base_sha256: hashOf(result), meta: { ...previous.meta, ...result }, dirty: false, reviewed: false, saving: false, advanced: false, header_fields: null, status: 'Guardado', conflict: null, regeneration: result.maintenance || result.regeneration }));
      if (alive.current) { setTab('edit'); setToolsReviewed(false); }
    } catch (failure) {
      const conflict = failure.result?.conflict || failure.result?.code === 'conflict';
      onDraft(id, previous => ({ ...previous, saving: false, status: 'Cambios sin guardar', conflict: conflict ? failure.result : null }));
      if (alive.current) { setError(failure.message); if (conflict) setTab('review'); }
    } finally { inFlight.current = false; }
  }
  const shortcut = useEffectEvent(event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') { event.preventDefault(); save(); } });
  useEffect(() => { const handler = event => shortcut(event); window.addEventListener('keydown', handler); return () => window.removeEventListener('keydown', handler); }, []);
  async function versionsView(selectedVersionId = '') {
    const generation = ++loadGeneration.current;
    setTab('versions'); setVersion(null); setToolsReviewed(false); setBusy(true); setError('');
    try {
      const result = await call(action('versions'), payload());
      if (!alive.current || generation !== loadGeneration.current) return;
      setVersions(result.versions || []);
      if (selectedVersionId) {
        const previous = await call(action('version'), payload({ version_id: selectedVersionId }));
        if (alive.current && generation === loadGeneration.current) {
          setToolsReviewed(false); setVersion({ ...previous, version_id: selectedVersionId });
        }
      }
    } catch (failure) {
      if (alive.current && generation === loadGeneration.current) setError(failure.message);
    } finally {
      if (alive.current && generation === loadGeneration.current) setBusy(false);
    }
  }
  async function readVersion(versionId) {
    const generation = ++loadGeneration.current;
    setBusy(true); setError('');
    try {
      const result = await call(action('version'), payload({ version_id: versionId }));
      if (alive.current && generation === loadGeneration.current) {
        setToolsReviewed(false); setVersion({ ...result, version_id: versionId });
      }
    } catch (failure) {
      if (alive.current && generation === loadGeneration.current) setError(failure.message);
    } finally {
      if (alive.current && generation === loadGeneration.current) setBusy(false);
    }
  }
  async function restore() {
    if (inFlight.current || draft.dirty || !version || !window.confirm('¿Restaurar esta versión? El archivo actual quedará en el historial.')) return;
    inFlight.current = true; update(previous => ({ ...previous, saving: true, status: 'Restaurando…' })); setError('');
    try { const result = await call(action('restore'), payload({ version_id: version.version_id, base_sha256: draft.base_sha256, review_tools_model: toolsReviewed }));
      accept({ ...draft.meta, ...result }, 'Guardado'); if (alive.current) { setVersion(null); setTab('edit'); }
    } catch (failure) { onDraft(id, previous => ({ ...previous, saving: false, status: 'Sin cambios' })); if (alive.current) setError(failure.message); }
    finally { inFlight.current = false; }
  }
  useEffect(() => {
    if (!initialVersionId || !id || item?.isNew || !draft) return undefined;
    let cancelled = false;
    versionsView(initialVersionId).finally(() => {
      if (!cancelled) onVersionOpened?.();
    });
    return () => { cancelled = true; loadGeneration.current++; };
  }, [id, initialVersionId, Boolean(draft), onVersionOpened]);
  async function openCreate() {
    setError(''); try { const result = await call('templates', {}); if (alive.current) setTemplates(result.templates || []); }
    catch (failure) { if (alive.current) setError(failure.message); }
  }
  async function openSaveAs() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const result = await call('templates', {});
      if (!result.destinations?.length) throw new Error('No hay carpetas seguras disponibles para guardar.');
      if (alive.current) {
        setDestinations(result.destinations);
        setDestination(result.destinations[0].id);
        setTab('save-as');
      }
    } catch (failure) {
      if (alive.current) setError(failure.message);
    } finally {
      if (alive.current) setBusy(false);
    }
  }
  async function create(event) {
    event.preventDefault(); if (locked) return; setBusy(true); setError('');
    try { const result = await call('create', { template_id: templateId, path: createPath });
      if (alive.current) { setTemplates(null); onCreated({ id: result.id || result.path, documentPath: result.path, title: createPath.split('/').at(-1), relativePath: result.path || createPath, canOpenDocument: true }); }
    } catch (failure) { if (alive.current) setError(failure.message); } finally { if (alive.current) setBusy(false); }
  }
  async function saveAs(event) {
    event.preventDefault(); if (inFlight.current || locked || !item?.isNew || !draft?.reviewed) return;
    inFlight.current = true;
    setBusy(true); setError('');
    try {
      const result = await call('create', { destination, name: newFileName, text: draft.text });
      if (alive.current) {
        setDestinations([]);
        onCreated?.({ id: result.path, documentPath: result.path, title: result.path.split('/').at(-1),
          relativePath: result.path, canOpenDocument: true }, id);
      }
    } catch (failure) {
      if (alive.current) setError(failure.message);
    } finally {
      if (alive.current) setBusy(false);
      inFlight.current = false;
    }
  }
  return <section className="document-editor" aria-labelledby="editor-title" aria-busy={locked}>
    <header className="editor-heading"><span className="editor-eyebrow">TU MESA DE TRABAJO</span><h2 id="editor-title">{item?.title || item?.name || 'Selecciona un documento para editarlo'}</h2>
      <p className="editor-path">{item?.relativePath}</p>
      {!item?.privateNotes && !item?.isNew ? <button type="button" className="button" disabled={locked || draft?.dirty} onClick={openCreate}>Crear desde plantilla</button> : null}
      {item?.isNew ? <><p>Escribe primero. Elegirás la carpeta y el nombre al guardar.</p>
        <button type="button" className="button" disabled={locked} onClick={() => {
          if (window.confirm('¿Descartar este borrador? El texto no guardado se perderá.')) onDiscard?.(id);
        }}>Descartar borrador</button></> : null}
      {item?.privateNotes ? <p>Nota privada local · No se incluye en el contexto de los agentes.</p> : null}
    </header>
    {error ? <p className="editor-error" role="alert">{error} {!draft && id ? <button type="button" className="button" onClick={() => load()}>Reintentar</button> : null}</p> : null}
    {templates ? <form className="editor-create" onSubmit={create}><h3>Crear un documento</h3>
      <label>Plantilla<select required value={templateId} onChange={event => setTemplateId(event.target.value)}><option value="">Elige una plantilla</option>{templates.map(template => <option key={template.id} value={template.id}>{template.name || template.label || template.id}</option>)}</select></label>
      <label>Ruta relativa al Workshop<input required value={createPath} onChange={event => setCreatePath(event.target.value)} placeholder="infra/…/mi-documento.md" /></label>
      <button className="button button--primary" disabled={locked}>Crear</button><button type="button" className="button" onClick={() => setTemplates(null)}>Cancelar</button></form> : null}
    {!id ? <p className="editor-empty">Abre un recurso de la lista para editarlo, revisar los cambios y recuperar versiones anteriores.</p> : null}
    {id && !item.canOpenDocument ? <p>Solo lectura · Este recurso no tiene un documento compatible.</p> : null}
    {draft ? <>
      {!canEdit ? <p>Solo lectura · {draft.meta.reason || 'Este archivo está fuera de las rutas autorizadas para editar.'}</p> : null}
      {tab !== 'save-as' ? <div className="editor-tabs" role="group" aria-label="Vista del documento"><button type="button" aria-pressed={tab === 'edit'} onClick={() => setTab('edit')}>Editar</button><button type="button" aria-pressed={tab === 'preview'} onClick={() => setTab('preview')}>Vista previa</button>{!item?.isNew ? <button type="button" aria-pressed={tab === 'versions'} disabled={locked} onClick={versionsView}>Versiones</button> : null}</div> : null}
      {tab === 'edit' ? <>
        {draft.meta.header?.raw_header ? <details className="editor-header-info"><summary>Datos de la ficha</summary>
          {draft.meta.header.safe ? <>{(draft.meta.header.editable_fields || []).map(field => <label key={field}>{({ name: 'Nombre', description: 'Descripción', tools: 'Herramientas', model: 'Modelo', color: 'Color', skills: 'Skills', disallowedTools: 'Herramientas bloqueadas' })[field] || field}<input disabled={!canEdit || locked || draft.advanced} value={draft.header_fields?.[field] ?? draft.meta.header.fields?.[field] ?? ''} onChange={event => editField(field, event.target.value)} /></label>)}{draft.advanced ? <p>El documento tiene cambios en edición avanzada; guarda antes de volver al formulario.</p> : null}<p>Los campos desconocidos se conservan. La edición avanzada está disponible en el documento completo.</p></> : <p>Edición avanzada: {draft.meta.header.reason || 'La ficha no se puede convertir a un formulario con seguridad.'}</p>}
          {(draft.meta.header.warnings || []).map(warning => <p className="editor-error" key={warning}>{warning}</p>)}
        </details> : null}
        <label className="editor-content-label">Contenido del documento<textarea spellCheck={false} readOnly={!canEdit || locked} value={draft.text} onChange={event => edit(event.target.value)} onScroll={event => update(previous => ({ ...previous, scroll: event.target.scrollTop }))} onFocus={event => { if (draft.scroll && !event.target.scrollTop) event.target.scrollTop = draft.scroll; }} /></label>
      </> : null}
      {tab === 'preview' ? <section className="editor-preview" aria-label="Vista previa del documento">
        {(item?.isNew || /\.(md|markdown)$/i.test(item?.relativePath || '')) ? <>
          <div className="preview-mode" role="group" aria-label="Formato de vista previa">
            <button type="button" aria-pressed={previewMode === 'formatted'} onClick={() => setPreviewMode('formatted')}>Con formato</button>
            <button type="button" aria-pressed={previewMode === 'plain'} onClick={() => setPreviewMode('plain')}>Texto plano</button>
          </div>
          {previewMode === 'formatted' ? <MarkdownPreview source={draft.text} /> :
            <pre className="editor-preview-plain">{draft.text || '(Documento vacío)'}</pre>}
        </> : <pre className="editor-preview-plain">{draft.text || '(Documento vacío)'}</pre>}
      </section> : null}
      {tab === 'review' ? <section className="editor-review"><h3>Revisar cambios antes de guardar</h3><Comparison before={draft.conflict?.current_text ?? draft.conflict?.current?.text ?? draft.original} after={draft.text} /><CapabilityReview before={draft.original} after={draft.text} />{draft.meta.header?.raw_header ? <label className="editor-check"><input type="checkbox" checked={toolsReviewed} onChange={event => setToolsReviewed(event.target.checked)} />He revisado los cambios de herramientas y modelo.</label> : null}</section> : null}
      {tab === 'save-as' ? <section className="editor-save-as">
        <h3>Guardar el borrador</h3>
        <p>El archivo se creará ahora; el texto no se guarda hasta confirmar esta acción.</p>
        <Comparison before="" after={draft.text} />
        <form className="editor-create" onSubmit={saveAs}>
          <label>Carpeta de destino
            <select required value={destination} onChange={event => setDestination(event.target.value)}>
              {destinations.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
            </select>
          </label>
          <label>Nombre del archivo, sin extensión
            <span className="editor-filename"><input required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" maxLength={90}
              value={newFileName} onChange={event => setNewFileName(event.target.value)}
              placeholder="mi-nuevo-documento" autoComplete="off" /><span aria-hidden="true">.md</span></span>
          </label>
          <button className="button button--primary" disabled={locked || !destination || !newFileName || !draft.reviewed}>Crear archivo</button>
          <button type="button" className="button" disabled={locked} onClick={() => setTab('review')}>Volver a revisar</button>
        </form>
      </section> : null}
      {draft.conflict ? <section className="editor-error" role="alert"><p>El archivo cambió fuera de este borrador. Tu texto se conserva. Compara antes de recargar.</p><button className="button" onClick={() => setTab('review')}>Ver diferencias</button><button className="button" disabled={locked} onClick={() => { if (window.confirm('¿Recargar el archivo y descartar este borrador?')) load(true); }}>Recargar archivo</button></section> : null}
      {tab === 'versions' ? <section><h3>Versiones guardadas</h3><p>Solo se registran guardados y restauraciones desde la aplicación.</p>{!versions.length && !busy ? <p>Todavía no hay versiones anteriores.</p> : null}<ul>{versions.map(entry => <li key={entry.version_id || entry.id}><button type="button" className="button" disabled={locked} onClick={() => readVersion(entry.version_id || entry.id)}>{entry.created_at || entry.created || entry.version_id || entry.id}</button></li>)}</ul>{version ? <><Comparison before={draft.original} after={version.text} /><CapabilityReview before={draft.original} after={version.text} />{draft.meta.header?.raw_header ? <label className="editor-check"><input type="checkbox" checked={toolsReviewed} onChange={event => setToolsReviewed(event.target.checked)} />He revisado las herramientas y el modelo de esta versión.</label> : null}<button type="button" className="button" disabled={locked || draft.dirty || !canEdit || (!!draft.meta.header?.raw_header && !toolsReviewed)} onClick={restore}>Restaurar esta versión</button>{draft.dirty ? <p>Guarda el borrador antes de restaurar.</p> : null}</> : null}</section> : null}
      {draft.regeneration ? <details><summary>Resultado de sincronización</summary><pre>{JSON.stringify(draft.regeneration, null, 2)}</pre></details> : null}
      {tab !== 'save-as' ? <footer className="editor-savebar"><span role="status" aria-live="polite">{draft.status || 'Sin cambios'}</span><button type="button" className="button" disabled={!draft.dirty || locked || !canEdit} onClick={review}>Revisar cambios</button><button type="button" className="button button--primary" disabled={!draft.dirty || locked || !canEdit || !!draft.conflict} onClick={save}>{draft.saving ? 'Guardando…' : item?.isNew ? tab === 'review' && draft.reviewed ? 'Elegir nombre y carpeta' : 'Revisar borrador' : tab === 'review' && draft.reviewed ? 'Confirmar y guardar' : 'Guardar'}</button></footer> : null}
    </> : busy ? <p role="status">Cargando documento…</p> : null}
  </section>;
}
