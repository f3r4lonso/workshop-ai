"""Motores: the engine cards and the "Probar" check (v2 engines.md, architecture section 6).

The list comes from `workshop_ai/engines.json`, shared with the `wai` CLI. Nothing here reads credentials, sends
content to a provider or puts request data on a command line: "Probar" runs only `<program> --version`.
"""

from __future__ import annotations

import os
import re
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Callable

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
from workshop_ai import engines, procutil  # noqa: E402

CMD_SPECIAL = set(';&|^%"<>')
CHECK_TIMEOUT_S = 5
SESSION_UNKNOWN = 'desconocida'
_check_lock = threading.Lock()


# Loaded and validated once, at server start: a broken engines.json stops the server with a clear message instead of
# failing requests, and the cards always agree with the console allow-list built from the same data.
try:
    _ENGINES: list[dict[str, Any]] = engines.load()
    _LEVELS: list[str] = engines.level_names()
except (OSError, ValueError) as exc:
    raise SystemExit(f'No se puede leer la lista de motores {engines.REGISTRY_PATH}: {exc}') from None


def _registry() -> tuple[list[dict[str, Any]], list[str]]:
    return _ENGINES, _LEVELS


def console_clients() -> dict[str, tuple[str, str]]:
    """Fixed allow-list for console launches: id -> (display name, program)."""
    return {e['id']: (e['name'], e['command']) for e in _ENGINES if e['console']}


def _guide_items(snapshot: Any) -> dict[str, str]:
    by_path: dict[str, str] = {}
    for item_id, resource in getattr(snapshot, 'by_id', {}).items():
        rel = (getattr(resource, 'relative_path', '') or '').replace('\\', '/').casefold()
        if rel:
            by_path.setdefault(rel, item_id)
    return by_path


def _effective(engine: dict[str, Any], executable: str | None) -> tuple[int, str]:
    """Level the app can offer now, and why it is lower than the verified level (empty when equal)."""
    level = engine['level']
    if engine['command'] is None:
        return level, ''
    if executable is None:
        return 0, 'No instalado en este ordenador (o no está en el PATH).'
    if engine['id'] == 'claude' and level >= 2 and not executable.lower().endswith('.exe'):
        return 1, 'Conversar necesita el ejecutable nativo de Claude Code, no un envoltorio.'
    return level, ''


def payload(snapshot: Any, root: str, find_executable: Callable[[str, str], str | None]) -> dict[str, Any]:
    entries, names = _registry()
    guides = _guide_items(snapshot)
    cards = []
    for engine in entries:
        executable = find_executable(engine['command'], root) if engine['command'] else None
        level, reason = _effective(engine, executable)
        warning = ''
        if engine['id'] == 'claude' and os.environ.get('ANTHROPIC_API_KEY'):
            warning = ('La variable ANTHROPIC_API_KEY está definida: Claude Code usará esa clave de pago por uso '
                       'en lugar de tu suscripción.')
        cards.append({
            'id': engine['id'],
            'name': engine['name'],
            'kind': engine['kind'],
            'location': engine['location'],
            'level': level,
            'levelName': names[level],
            'verifiedLevel': engine['level'],
            'target': engine['target'],
            'targetName': names[engine['target']],
            'installed': None if engine['command'] is None else executable is not None,
            'session': SESSION_UNKNOWN,
            'console': bool(engine['console'] and executable),
            'canCheck': engine['command'] is not None,
            'url': engine['url'],
            'guideItemId': guides.get(engine['guide'].casefold()),
            'goodFor': engine['good_for'],
            'nextStep': engine['next_step'],
            'reason': reason,
            'warning': warning,
        })
    return {'levels': names, 'engines': cards}


def check(engine_id: Any, root: str, find_executable: Callable[[str, str], str | None]) -> dict[str, Any]:
    """Probar: is the program on PATH, and which version does it report? Never signs in, never sends content."""
    entry = next((e for e in _ENGINES if e['id'] == engine_id), None) if isinstance(engine_id, str) else None
    if entry is None:
        return {'ok': False, 'message': 'Motor desconocido.'}
    now = datetime.now(timezone.utc).isoformat()
    if entry['command'] is None:
        return {'ok': True, 'id': entry['id'], 'installed': None, 'version': None, 'checkedAt': now,
                'message': f"{entry['name']} se usa desde su web o su aplicación; no hay nada que probar aquí."}
    executable = find_executable(entry['command'], root)
    if executable is None:
        return {'ok': True, 'id': entry['id'], 'installed': False, 'version': None, 'checkedAt': now,
                'message': f"{entry['name']} no está instalado o no está en el PATH."}
    if CMD_SPECIAL & set(executable):
        return {'ok': False, 'id': entry['id'], 'installed': True, 'version': None, 'checkedAt': now,
                'message': 'La ruta del programa contiene caracteres especiales; no se ejecuta.'}
    if not _check_lock.acquire(blocking=False):
        return {'ok': False, 'id': entry['id'], 'message': 'Ya hay una prueba en curso; espera un momento.'}
    try:
        version = _version(executable)
    finally:
        _check_lock.release()
    if version is None:
        return {'ok': True, 'id': entry['id'], 'installed': True, 'version': None, 'checkedAt': now,
                'message': f"{entry['name']} está instalado, pero no respondió con su versión."}
    return {'ok': True, 'id': entry['id'], 'installed': True, 'version': version, 'checkedAt': now,
            'message': f"{entry['name']} responde: versión {version}. La sesión no se comprueba."}


def _version(executable: str) -> str | None:
    env = dict(os.environ)
    env['NoDefaultCurrentDirectoryInExePath'] = '1'
    result = procutil.run_bounded([executable, '--version'], timeout=CHECK_TIMEOUT_S, env=env)
    if result is None or result[0]:
        return None
    match = re.search(r'(?<!\d)(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?)', result[1])
    return match.group(1) if match else None
