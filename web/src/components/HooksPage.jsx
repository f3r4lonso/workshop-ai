const IDEAS = [
  {
    title: 'Aviso al terminar',
    detail: 'Recibe una notificación cuando una tarea larga termina o necesita tu atención.',
    fit: 'Útil en ejecuciones largas; no necesita acceder a tus archivos.',
  },
  {
    title: 'Recordatorio de entrega',
    detail: 'Al cerrar una sesión, recuerda registrar el resultado, las decisiones y lo que falta.',
    fit: 'Mantiene el seguimiento sin escribir notas por su cuenta.',
  },
  {
    title: 'Confirmación de comandos delicados',
    detail: 'Detecta un conjunto pequeño de acciones destructivas o externas y conserva la aprobación manual.',
    fit: 'No aprueba ni ejecuta comandos automáticamente.',
  },
];

const CLIENTS = [
  {
    name: 'Claude Code',
    state: 'Documentado por el proveedor',
    url: 'https://code.claude.com/docs/en/hooks-guide',
  },
  {
    name: 'Codex',
    state: 'Hooks propios; falta validar el evento y la superficie exactos',
    url: 'https://learn.chatgpt.com/docs/hooks',
  },
  {
    name: 'Gemini CLI',
    state: 'Hooks propios; configuración local del cliente',
    url: 'https://geminicli.com/docs/hooks/reference/',
  },
  {
    name: 'GitHub Copilot CLI',
    state: 'Sin integración de hooks en Workshop AI',
    url: 'https://docs.github.com/copilot',
  },
];

export default function HooksPage() {
  return (
    <section className="hooks-page" aria-labelledby="hooks-title">
      <header className="hooks-intro">
        <p>Automatizaciones de los clientes</p>
        <h2 id="hooks-title">Ideas para hooks seguros</h2>
        <p>
          Los hooks pertenecen a cada cliente y no son intercambiables. Workshop AI los documenta;
          no instala configuraciones ni ejecuta scripts.
        </p>
      </header>

      <section className="hooks-section" aria-labelledby="hooks-shortlist">
        <h3 id="hooks-shortlist">Buenas primeras opciones</h3>
        <ol className="hooks-list">
          {IDEAS.map((idea) => (
            <li key={idea.title}>
              <h4>{idea.title}</h4>
              <p>{idea.detail}</p>
              <p className="hooks-fit">{idea.fit}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="hooks-section" aria-labelledby="hooks-clients">
        <h3 id="hooks-clients">Documentación por cliente</h3>
        <ul className="hooks-clients">
          {CLIENTS.map((client) => (
            <li key={client.name}>
              <strong>{client.name}</strong>
              <span>{client.state}</span>
              <a href={client.url} target="_blank" rel="noreferrer">Abrir documentación oficial</a>
            </li>
          ))}
        </ul>
      </section>

      <aside className="hooks-warning">
        <h3>Antes de configurar uno</h3>
        <p>
          Revisa el script y sus permisos localmente. No compartas prompts, argumentos, rutas privadas
          ni secretos en registros. Mantén las aprobaciones manuales: un hook no es un sandbox.
        </p>
      </aside>
    </section>
  );
}
