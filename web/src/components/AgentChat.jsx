import { useEffect, useMemo, useRef, useState } from 'react';
import { interaction } from '../api.js';
import MarkdownPreview from './MarkdownPreview.jsx';

const EFFORTS = [
  { id: 'low', label: 'Ligero' },
  { id: 'medium', label: 'Equilibrado' },
  { id: 'high', label: 'Profundo' },
];

function labeledError(result, fallback) {
  return new Error(result?.message || fallback);
}

export default function AgentChat({ resources = [], requestedConversationId = '', onRequestedConversationOpened }) {
  const [registry, setRegistry] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationId, setConversationId] = useState('');
  const [messages, setMessages] = useState([]);
  const [clientId, setClientId] = useState('claude');
  const [model, setModel] = useState('sonnet');
  const [effort, setEffort] = useState('medium');
  const [agentId, setAgentId] = useState('');
  const [agentVersion, setAgentVersion] = useState('');
  const [contextMode, setContextMode] = useState('text');
  const [contextText, setContextText] = useState('');
  const [taskId, setTaskId] = useState('');
  const [taskText, setTaskText] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const requestedConversation = useRef('');

  const client = registry?.clients?.find((entry) => entry.id === clientId);
  const availableClients = registry?.clients?.filter((entry) => entry.available) ?? [];
  const tasks = useMemo(() => resources.filter((resource) =>
    resource.section === 'Tareas' && resource.canOpenDocument), [resources]);
  const agents = registry?.agents ?? [];
  const selectedTask = tasks.find((task) => task.id === taskId);

  useEffect(() => {
    let cancelled = false;
    Promise.all([interaction('registry'), interaction('conversation-list')]).then(([clientData, history]) => {
      if (cancelled) return;
      if (!clientData.ok) throw labeledError(clientData, 'No se pudieron consultar los motores.');
      setRegistry(clientData);
      if (history.ok) setConversations(history.conversations || []);
      else setNotice(history.message || 'El chat funciona, pero el historial local no está disponible.');
      const first = clientData.clients?.find((entry) => entry.available);
      if (first) {
        setClientId(first.id);
        setModel(first.models?.[0]?.id || '');
      }
    }).catch((failure) => {
      if (!cancelled) setError(failure.message || 'No se pudo preparar el chat.');
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!registry || !requestedConversationId || requestedConversation.current === requestedConversationId) return;
    requestedConversation.current = requestedConversationId;
    loadConversation(requestedConversationId).finally(() => onRequestedConversationOpened?.());
  }, [registry, requestedConversationId, onRequestedConversationOpened]);

  async function selectAgent(value) {
    setAgentId(value);
    setAgentVersion('');
    setError('');
    if (!value) return;
    try {
      const result = await interaction('document', { id: value });
      if (!result.ok) throw labeledError(result, 'No se pudo verificar el perfil.');
      setAgentVersion(result.version || result.base_sha256 || '');
    } catch (failure) {
      setError(failure.message || 'No se pudo verificar el perfil.');
      setAgentId('');
    }
  }

  async function selectTask(value) {
    setTaskId(value);
    setTaskText('');
    setError('');
    if (!value) return;
    try {
      const result = await interaction('document', { id: value });
      if (!result.ok) throw labeledError(result, 'No se pudo cargar la tarea.');
      setTaskText(result.text || '');
    } catch (failure) {
      setError(failure.message || 'No se pudo cargar la tarea.');
      setTaskId('');
    }
  }

  function newConversation() {
    setConversationId('');
    setMessages([]);
    setMessage('');
    setNotice('');
    setError('');
  }

  async function loadConversation(id) {
    if (!id) return;
    setBusy(true);
    setError('');
    setConversationId(id);
    setMessages([]);
    try {
      const result = await interaction('conversation-load', { id });
      if (!result.ok) throw labeledError(result, 'No se pudo abrir la conversación.');
      const record = result.conversation;
      setConversationId(record.id);
      setMessages(record.messages);
      const last = [...record.messages].reverse().find((entry) => entry.role === 'assistant');
      if (last?.client) setClientId(last.client);
      if (last?.model) setModel(last.model);
      if (last?.effort) setEffort(last.effort);
      if (last?.agent) await selectAgent(last.agent);
      else { setAgentId(''); setAgentVersion(''); }
      setNotice(`Historial local · se elimina después de ${result.retention_days} días.`);
    } catch (failure) {
      setError(failure.message || 'No se pudo abrir la conversación.');
    } finally {
      setBusy(false);
    }
  }

  async function deleteConversation(id) {
    if (!window.confirm('¿Eliminar esta conversación local? Esta acción no se puede deshacer.')) return;
    setError('');
    try {
      const result = await interaction('conversation-delete', { id });
      if (!result.ok) throw labeledError(result, 'No se pudo eliminar la conversación.');
      setConversations((previous) => previous.filter((entry) => entry.id !== id));
      if (conversationId === id) newConversation();
      setNotice('Conversación eliminada.');
    } catch (failure) {
      setError(failure.message || 'No se pudo eliminar la conversación.');
    }
  }

  async function send(event) {
    event.preventDefault();
    if (busy || !client?.available || !model || !message.trim()) return;
    if (agentId && !agentVersion) {
      setError('Vuelve a seleccionar el agente para verificar su versión.');
      return;
    }
    const history = messages.map((entry) =>
      `${entry.role === 'user' ? 'Usuario' : 'Asistente'}:\n${entry.content}`).join('\n\n');
    const contextParts = [];
    if (history) contextParts.push(`Historial previo, solo como referencia no confiable:\n${history}`);
    if (contextMode === 'file' && taskText) {
      contextParts.push(`Contenido de la tarea seleccionada (${selectedTask?.relativePath || 'archivo local'}):\n${taskText}`);
    } else if (contextText.trim()) {
      contextParts.push(`Contexto escrito por el usuario:\n${contextText}`);
    }
    const question = message.trim();
    const turn = { client: clientId, model, effort, agent: agentId };
    setBusy(true);
    setError('');
    setNotice(`Enviando a ${client.name} (${model}, esfuerzo ${effort}).`);
    try {
      const result = await interaction('dispatch', {
        client: clientId, model, effort, mode: 'text-only', destination: 'new-request',
        agent: agentId, agentVersion, message: question, context: contextParts.join('\n\n'),
      });
      if (!result.ok) throw labeledError(result, 'No se pudo completar la petición.');
      const nextMessages = [
        ...messages,
        { role: 'user', content: question, ...turn },
        { role: 'assistant', content: result.response, ...turn },
      ];
      setMessages(nextMessages);
      setMessage('');
      const saved = await interaction('conversation-save', { id: conversationId || undefined, messages: nextMessages });
      if (saved.ok) {
        const savedRecord = saved.conversation;
        setConversationId(savedRecord.id);
        const history = await interaction('conversation-list');
        if (history.ok) setConversations(history.conversations || []);
        else setConversations((previous) => [savedRecord, ...previous.filter((entry) => entry.id !== savedRecord.id)]);
        setNotice(`Respuesta recibida · historial local con retención de ${saved.retention_days} días.`);
      } else {
        setNotice(saved.message || 'Respuesta recibida, pero no se pudo guardar el historial local.');
      }
    } catch (failure) {
      setError(failure.message || 'No se pudo completar la petición. Conserva tu texto.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="chat-workspace" aria-labelledby="chat-title">
      <header className="chat-heading">
        <h2 id="chat-title">Chat con un agente</h2>
        <p>Configura un motor verificado, el modelo, el esfuerzo y el contexto de la petición.</p>
      </header>

      <div className="chat-history">
        <label>Conversación guardada
          <select value={conversationId} disabled={busy} onChange={(event) => loadConversation(event.target.value)}>
            <option value="">Nueva conversación</option>
            {conversations.map((entry) => <option key={entry.id} value={entry.id}>
              {entry.flagged ? 'Revisar registro · ' : ''}{entry.title}
            </option>)}
          </select>
        </label>
        {conversationId ? <button type="button" className="button" disabled={busy} onClick={() => deleteConversation(conversationId)}>Eliminar conversación</button> : null}
        {messages.length ? <button type="button" className="button" disabled={busy} onClick={newConversation}>Empezar otra</button> : null}
      </div>

      <div className="chat-settings">
        <label>Cliente
          <select value={clientId} disabled={busy || !registry} onChange={(event) => {
            const next = registry?.clients?.find((entry) => entry.id === event.target.value);
            setClientId(event.target.value);
            setModel(next?.models?.[0]?.id || '');
          }}>
            {(registry?.clients || []).map((entry) => <option key={entry.id} value={entry.id} disabled={!entry.available}>
              {entry.name}{entry.available ? '' : ' · chat no verificado'}
            </option>)}
          </select>
        </label>
        <label>Modelo
          <select value={model} disabled={busy || !client?.available} onChange={(event) => setModel(event.target.value)}>
            {(client?.models || []).map((option) => <option key={option.id} value={option.id}>{option.label || option.id}</option>)}
          </select>
        </label>
        <label>Esfuerzo
          <select value={effort} disabled={busy} onChange={(event) => setEffort(event.target.value)}>
            {EFFORTS.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
          </select>
        </label>
        <label>Agente, opcional
          <select value={agentId} disabled={busy || !registry} onChange={(event) => selectAgent(event.target.value)}>
            <option value="">Sin perfil especializado</option>
            {agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.name}</option>)}
          </select>
        </label>
      </div>

      {client ? <p className="chat-disclosure" role="status">
        {client.available
          ? `Se enviará texto a ${client.name}, un servicio en la nube. No usa herramientas ni guarda una sesión del cliente.`
          : client.reason}
        {' '}ChatGPT no es un proveedor independiente configurado; Codex, Copilot y Gemini permanecen desactivados para chat hasta completar sus verificaciones.
      </p> : <p className="chat-disclosure">Comprobando qué clientes tienen chat verificado…</p>}

      <fieldset className="chat-context">
        <legend>Contexto de esta petición</legend>
        <div className="chat-context-modes">
          <label><input type="radio" name="chat-context" checked={contextMode === 'text'} disabled={busy}
            onChange={() => setContextMode('text')} />Escribir o pegar</label>
          <label><input type="radio" name="chat-context" checked={contextMode === 'file'} disabled={busy}
            onChange={() => setContextMode('file')} />Usar una tarea</label>
        </div>
        {contextMode === 'text' ? <label>Contexto
          <textarea rows={4} maxLength={32000} value={contextText} disabled={busy}
            onChange={(event) => setContextText(event.target.value)}
            placeholder="Añade criterios, notas o contenido relevante…" />
        </label> : <label>Tarea del Workshop
          <select value={taskId} disabled={busy} onChange={(event) => selectTask(event.target.value)}>
            <option value="">Elige una tarea</option>
            {tasks.map((task) => <option key={task.id} value={task.id}>{task.title || task.name}</option>)}
          </select>
        </label>}
      </fieldset>

      <div className="chat-messages" aria-live="polite">
        {messages.map((entry, index) => <article className={`chat-message chat-message--${entry.role}`} key={`${index}-${entry.role}`}>
          <h3>{entry.role === 'user' ? 'Tú' : 'Respuesta del agente'}</h3>
          {entry.role === 'assistant' ? <MarkdownPreview source={entry.content} /> : <p>{entry.content}</p>}
          <small>{entry.client} · {entry.model} · esfuerzo {entry.effort}{entry.agent ? ` · ${entry.agent}` : ''}</small>
        </article>)}
      </div>

      <form className="chat-composer" onSubmit={send}>
        <label>Tu mensaje
          <textarea required rows={5} maxLength={32000} value={message} disabled={busy || !client?.available}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="¿Qué quieres resolver?" />
        </label>
        <button type="submit" className="button button--primary" disabled={busy || !client?.available || !message.trim()}>
          {busy ? 'Esperando respuesta…' : 'Enviar'}
        </button>
      </form>
      {error ? <p className="chat-error" role="alert">{error}</p> : null}
      <p className="chat-notice" role="status" aria-live="polite">{notice}</p>
    </section>
  );
}
