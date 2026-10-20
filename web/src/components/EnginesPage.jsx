import { useCallback, useEffect, useState } from 'react';
import { checkEngine, getEngines } from '../api.js';
import { AlertIcon } from './Icons.jsx';

const INSTALLED_TEXT = { true: 'Instalado', false: 'No instalado', null: 'No se instala: se usa desde su web o app' };

function LevelMeter({ level, target, levels }) {
  return (
    <ol className="level-meter" aria-label={`Nivel ${level} de 4: ${levels[level]}. Objetivo en v2: ${levels[target]}.`}>
      {levels.map((name, index) => (
        <li key={name} aria-hidden="true"
          className={`level-step${index <= level ? ' level-step--on' : ''}${index === target ? ' level-step--target' : ''}`}
          title={`${index} · ${name}${index === target ? ' (objetivo)' : ''}`} />
      ))}
    </ol>
  );
}

function EngineCard({ engine, levels, check, launch, onCheck, onLaunch, onOpenGuide }) {
  const busy = check?.phase === 'busy';
  const launching = launch?.phase === 'busy';
  const resultId = `engine-result-${engine.id}`;
  return (
    <li className="engine-card">
      <div className="engine-head">
        <h2 className="engine-name">{engine.name}</h2>
        <span className={`pill pill--${engine.location === 'local' ? 'aplicaciones' : 'otros'}`}>
          {engine.location === 'local' ? 'En este ordenador' : 'En la nube'}
        </span>
      </div>
      <p className="engine-level">
        <strong>Nivel {engine.level} · {engine.levelName}</strong>
        <LevelMeter level={engine.level} target={engine.target} levels={levels} />
      </p>
      <p className="engine-good">{engine.goodFor}</p>
      <dl className="engine-facts">
        <div><dt>Estado</dt><dd>{INSTALLED_TEXT[String(engine.installed)]}</dd></div>
        <div><dt>Sesión</dt><dd>{engine.session}</dd></div>
        <div><dt>Objetivo en v2</dt><dd>{engine.targetName}</dd></div>
      </dl>
      {engine.reason ? <p className="engine-reason">{engine.reason}</p> : null}
      {engine.warning ? (
        <p className="engine-warning" role="note"><AlertIcon size={16} /> {engine.warning}</p>
      ) : null}
      <p className="engine-next">
        <span className="engine-next-label">{engine.level < engine.target ? 'Para subir de nivel' : 'Regla'}</span>
        {engine.nextStep}
      </p>
      <div className="engine-actions">
        {engine.canCheck ? (
          <button type="button" className="button" aria-busy={busy ? 'true' : undefined}
            aria-describedby={check?.message ? resultId : undefined} disabled={busy} onClick={() => onCheck(engine)}>
            {busy ? 'Probando…' : 'Probar'}
          </button>
        ) : null}
        {engine.console ? (
          <button type="button" className="button button--primary" disabled={launching} onClick={() => onLaunch(engine)}>
            {launching ? 'Abriendo…' : 'Abrir consola'}
          </button>
        ) : null}
        {engine.guideItemId ? (
          <button type="button" className="button" onClick={() => onOpenGuide(engine)}>Ver guía</button>
        ) : null}
        <a className="button" href={engine.url} target="_blank" rel="noreferrer noopener">
          Web oficial<span className="sr-only"> (se abre en una pestaña nueva)</span>
        </a>
      </div>
      <p id={resultId} className={`engine-result${check?.ok === false ? ' engine-result--error' : ''}`}
        role="status" aria-live="polite">
        {check?.message ?? ''}
      </p>
    </li>
  );
}

/** Motores: one card per engine from GET /api/engines (registry workshop_ai/engines.json). */
export default function EnginesPage({ onLaunch, onOpenGuide, launchState }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [checks, setChecks] = useState({});
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getEngines().then(
      (json) => !cancelled && setData(json),
      (failure) => !cancelled && setError(failure.message),
    );
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const handleCheck = useCallback(async (engine) => {
    setChecks((previous) => ({ ...previous, [engine.id]: { phase: 'busy', message: 'Probando…' } }));
    try {
      const result = await checkEngine(engine.id);
      setChecks((previous) => ({ ...previous, [engine.id]: { phase: 'done', ok: result.ok, message: result.message } }));
      if (result.ok && typeof result.installed === 'boolean' && result.installed !== engine.installed) {
        setAttempt((value) => value + 1);
      }
    } catch (failure) {
      setChecks((previous) => ({ ...previous, [engine.id]: { phase: 'done', ok: false, message: failure.message } }));
    }
  }, []);

  if (error) {
    return (
      <div className="load-error" role="alert">
        <AlertIcon size={28} />
        <p>{error}</p>
        <button type="button" className="button" onClick={() => { setError(''); setAttempt((value) => value + 1); }}>
          Reintentar
        </button>
      </div>
    );
  }
  if (!data) return <p className="page-intro" aria-busy="true">Cargando motores…</p>;
  const ready = data.engines.filter((engine) => engine.level >= 1).length;
  return (
    <>
      <p className="page-intro">
        {data.engines.length} motores · {ready} se pueden abrir o usar desde aquí. Niveles: {data.levels.map(
          (name, index) => `${index} ${name}`).join(' · ')}. «Probar» solo mira la versión instalada: no envía nada a
        ningún proveedor ni comprueba tu sesión.
      </p>
      <ul className="engine-grid" aria-label="Motores de IA">
        {data.engines.map((engine) => (
          <EngineCard key={engine.id} engine={engine} levels={data.levels} check={checks[engine.id]}
            launch={launchState[engine.id]} onCheck={handleCheck} onLaunch={onLaunch} onOpenGuide={onOpenGuide} />
        ))}
      </ul>
    </>
  );
}
