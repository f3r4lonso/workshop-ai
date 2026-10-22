import { useState } from 'react';
import { interaction } from '../api.js';

const AREAS = [
  ['ai', 'AI'],
  ['backend', 'Backend'],
  ['creative', 'Creatividad'],
  ['devops', 'DevOps'],
  ['frontend', 'Frontend'],
  ['game-development', 'Desarrollo de juegos'],
  ['quality', 'Calidad'],
  ['trading', 'Trading'],
  ['ui', 'Interfaz (UI)'],
  ['ux', 'Experiencia (UX)'],
];
const SKILL_AREAS = ['AI workflow', 'Backend', 'Frontend', 'Game development', 'Quality', 'Trading', 'UI/UX'];
const INITIAL = {
  kind: 'skill',
  name: '',
  title: '',
  area: 'UI/UX',
  access: 'read-only',
  description: '',
  when_to_use: '',
  instructions: '',
};

export default function ResourceAuthoring({ onRegistered }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(INITIAL);
  const [preview, setPreview] = useState(null);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setPreview(null);
    setApproved(false);
    setError('');
    setNotice('');
  }

  async function prepare(event) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await interaction('resource-registration-preview', form);
      if (!result.ok) throw new Error(result.message || 'No se pudo preparar la vista previa.');
      setPreview(result);
      setApproved(false);
      setNotice('Vista previa lista. Revisa cada archivo antes de guardar.');
    } catch (failure) {
      setError(failure.message || 'No se pudo preparar la vista previa.');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!preview?.preview_id || !approved || busy) return;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await interaction('resource-registration-save', { preview_id: preview.preview_id });
      if (!result.ok) throw new Error(result.message || 'No se pudo registrar el recurso.');
      setNotice(result.message || 'Recurso registrado.');
      setPreview(null);
      setApproved(false);
      setForm(INITIAL);
      await onRegistered?.();
    } catch (failure) {
      setError(failure.message || 'No se pudo registrar el recurso.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="resource-tool resource-authoring" aria-labelledby="resource-author-title">
      <div className="resource-tool-heading">
        <div>
          <h2 id="resource-author-title">Crear un agente o una skill</h2>
          <p>Completa una guía original, revisa los archivos que se modificarán y confirma el registro.</p>
        </div>
        <button type="button" className="button" aria-expanded={open} aria-controls="resource-author-form"
          onClick={() => { setOpen((value) => !value); setError(''); }}>
          {open ? 'Cerrar asistente' : 'Abrir asistente'}
        </button>
      </div>

      {open ? <div id="resource-author-form" className="authoring-workspace">
        <div className="authoring-safety" role="note">
          El registro se guarda en <code>infra/</code>, un repositorio público. {form.kind === 'agent'
            ? 'La vista previa incluye el adaptador Codex y el manifiesto del plugin Claude; para Copilot, Gemini y copias de usuario/proyecto, consulta infra/docs/manuals/shared-resource-installation.md.'
            : 'La vista previa incluye la skill canónica y un enlace compartido en infra/clients/.agents/skills; para copias de usuario/proyecto, consulta infra/docs/manuals/shared-resource-installation.md.'}
          {' '}La búsqueda de recursos externos solo prepara enlaces; no descarga ni instala código. Los agentes solo admiten permisos
          de lectura o edición de archivos; no terminal ni web.
        </div>
        <form className="authoring-form" onSubmit={prepare}>
          <div className="authoring-grid">
            <label>Tipo de recurso
              <select value={form.kind} disabled={busy} onChange={(event) => {
                const kind = event.target.value;
                update('kind', kind);
                setForm((current) => ({ ...current, kind, area: kind === 'skill' ? 'UI/UX' : 'ai' }));
              }}>
                <option value="skill">Skill: método o lista de comprobación</option>
                <option value="agent">Agente: rol especializado</option>
              </select>
            </label>
            <label>Nombre técnico
              <input required pattern="[a-z0-9]+(?:-[a-z0-9]+)*" maxLength={64} autoComplete="off"
                value={form.name} disabled={busy} onChange={(event) => update('name', event.target.value)}
                placeholder="ejemplo: revision-de-pruebas" />
              <small>Minúsculas, números y guiones; se usa como identificador único.</small>
            </label>
            <label>Nombre visible
              <input required maxLength={100} value={form.title} disabled={busy}
                onChange={(event) => update('title', event.target.value)} placeholder="Revisión de pruebas" />
            </label>
            <label>{form.kind === 'agent' ? 'Área' : 'Categoría'}
              {form.kind === 'agent' ? <select value={form.area} disabled={busy}
                onChange={(event) => update('area', event.target.value)}>
                {AREAS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
              </select> : <select value={form.area} disabled={busy}
                onChange={(event) => update('area', event.target.value)}>
                {SKILL_AREAS.map((area) => <option key={area}>{area}</option>)}
              </select>}
            </label>
            {form.kind === 'agent' ? <label>Permisos del agente
              <select value={form.access} disabled={busy} onChange={(event) => update('access', event.target.value)}>
                <option value="read-only">Solo lectura: Read, Grep, Glob</option>
                <option value="file-editing">Editar archivos: Read, Write, Edit, Grep, Glob</option>
              </select>
              <small>No se permiten Bash, PowerShell, web, delegación ni ejecución automática.</small>
            </label> : null}
            <label className="authoring-full">Descripción corta
              <input required maxLength={180} value={form.description} disabled={busy}
                onChange={(event) => update('description', event.target.value)}
                placeholder="Qué aporta este recurso y cuándo ayuda" />
            </label>
            <label className="authoring-full">Cuándo usarlo
              <textarea required rows={3} maxLength={500} value={form.when_to_use} disabled={busy}
                onChange={(event) => update('when_to_use', event.target.value)}
                placeholder="Describe las tareas o situaciones adecuadas." />
            </label>
            <label className="authoring-full">Instrucciones principales
              <textarea required rows={8} maxLength={24000} value={form.instructions} disabled={busy}
                onChange={(event) => update('instructions', event.target.value)}
                placeholder="Define un flujo claro, límites y el resultado esperado." />
              <small>{form.instructions.length}/24.000 caracteres. No incluyas credenciales, datos personales ni rutas privadas.</small>
            </label>
          </div>
          <div className="authoring-actions">
            <button type="submit" className="button button--primary" disabled={busy}>
              {busy ? 'Preparando…' : 'Preparar vista previa'}
            </button>
          </div>
        </form>

        {preview ? <section className="registration-review" aria-labelledby="registration-review-title">
          <h3 id="registration-review-title">Revisa los archivos del registro</h3>
          <p>{preview.warning}</p>
          <p>{preview.generated}</p>
          <div className="registration-files">
            {preview.files.map((file) => <details className="registration-file" key={file.path}>
              <summary>{file.path}</summary>
              <pre>{file.diff || 'Sin cambios de texto.'}</pre>
            </details>)}
          </div>
          <label className="registration-confirm">
            <input type="checkbox" checked={approved} disabled={busy}
              onChange={(event) => setApproved(event.target.checked)} />
            He revisado el contenido y confirmo que quiero registrarlo en el repositorio público.
          </label>
          <button type="button" className="button button--primary" disabled={!approved || busy} onClick={save}>
            {busy ? 'Guardando…' : 'Guardar y registrar'}
          </button>
        </section> : null}
        {error ? <p className="chat-error" role="alert">{error}</p> : null}
        <p className="chat-notice" role="status" aria-live="polite">{notice}</p>
      </div> : null}
    </section>
  );
}
