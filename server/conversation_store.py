"""Private, bounded conversation history stored outside project repositories."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import uuid

import workshop_data
import client_dispatch

MAX_BYTES = 1024 * 1024
MAX_MESSAGES = 100
MAX_MESSAGE_BYTES = 96 * 1024
MAX_CONVERSATIONS = 100
RETENTION_DAYS = 90
_ID = re.compile(r'^[a-f0-9]{32}$')
_AGENT_ID = re.compile(r'^[a-z0-9_-]{1,40}:[a-z0-9][a-z0-9_-]{0,119}$')
_lock = threading.RLock()


def _now():
    return datetime.now(timezone.utc)


def _time(value):
    try:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _folder(snapshot, create=False):
    root = Path(snapshot.workshop_root).absolute()
    if any(part.casefold() in {'onedrive', 'dropbox', 'google drive'} for part in root.parts):
        raise ValueError('El historial no se guarda dentro de una carpeta sincronizada.')
    private = root / '.workshop-ai'
    folder = private / 'conversations'
    for part in (root, private, folder):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('El historial privado está enlazado; no se ha usado.')
        if part.exists() and not part.is_dir():
            raise ValueError('La ruta del historial privado no es una carpeta.')
    if workshop_data.is_linked_path(str(root), str(root.anchor)) or folder.resolve() != folder:
        raise ValueError('La ruta del historial privado no es segura.')
    if create:
        folder.mkdir(parents=True, exist_ok=True)
        _folder(snapshot)
    return folder


def _record_path(folder, conversation_id):
    if not isinstance(conversation_id, str) or not _ID.fullmatch(conversation_id):
        raise ValueError('Identificador de conversación no válido.')
    path = folder / f'{conversation_id}.json'
    if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
        raise ValueError('El registro de conversación está enlazado.')
    return path


def _read(path):
    with path.open('rb') as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('La conversación supera el límite de lectura.')
    try:
        value = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError):
        raise ValueError('El registro de conversación no es válido.') from None
    if (not isinstance(value, dict) or value.get('version') != 1
            or not isinstance(value.get('id'), str) or not _ID.fullmatch(value['id'])
            or not isinstance(value.get('created_at'), str) or not isinstance(value.get('updated_at'), str)
            or not isinstance(value.get('messages'), list)
            or not 1 <= len(value['messages']) <= MAX_MESSAGES):
        raise ValueError('El registro de conversación no es compatible.')
    for message in value['messages']:
        if (not isinstance(message, dict) or message.get('role') not in ('user', 'assistant')
                or not isinstance(message.get('content'), str) or '\x00' in message['content']
                or not _valid_metadata(message)):
            raise ValueError('El registro de conversación no es compatible.')
    return value


def _valid_metadata(message):
    if set(message) - {'role', 'content', 'client', 'model', 'effort', 'agent'}:
        return False
    values = {key: message.get(key, '') for key in ('client', 'model', 'effort', 'agent')}
    if any(not isinstance(value, str) or len(value) > 160 for value in values.values()):
        return False
    return (
        values['client'] in ('', 'claude')
        and values['model'] in ('', *client_dispatch.MODELS)
        and values['effort'] in ('', 'low', 'medium', 'high')
        and (not values['agent'] or bool(_AGENT_ID.fullmatch(values['agent'])))
    )


def _scan(messages):
    import workshop_ai.scan as scan
    blocks, warnings = [], []
    for index, message in enumerate(messages):
        for field in ('content', 'client', 'model', 'effort', 'agent'):
            value = message.get(field, '')
            if not value:
                continue
            found, warned = scan.scan_text(value, f'mensaje-{index + 1}')
            blocks.extend(found)
            warnings.extend(warned)
    return blocks, warnings


def _summary(record, flagged=False):
    messages = record['messages']
    first = next((item['content'].strip() for item in messages if item['role'] == 'user'), '')
    title = ('Conversación marcada para revisión' if flagged else
             'Conversación nueva' if not first else ' '.join(first.split())[:90])
    return dict(id=record['id'], title=title, updated_at=record['updated_at'],
                message_count=len(messages), flagged=flagged)


def _prune(folder):
    cutoff = _now() - timedelta(days=RETENTION_DAYS)
    for path in folder.iterdir():
        if path.suffix != '.json' or not _ID.fullmatch(path.stem):
            continue
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()) or not path.is_file():
            raise ValueError('Hay un registro enlazado o no válido en el historial.')
        record = _read(path)
        updated = _time(record.get('updated_at'))
        if updated is None or updated < cutoff:
            path.unlink()


def _conversation_count(folder):
    total = 0
    for path in folder.iterdir():
        if path.suffix != '.json' or not _ID.fullmatch(path.stem):
            continue
        if _record_path(folder, path.stem).is_file():
            total += 1
    return total


def list_conversations(snapshot):
    with _lock:
        folder = _folder(snapshot)
        if not folder.exists():
            return dict(ok=True, conversations=[], retention_days=RETENTION_DAYS)
        _prune(folder)
        conversations = []
        for path in folder.iterdir():
            if path.suffix != '.json' or not _ID.fullmatch(path.stem):
                continue
            record = _read(_record_path(folder, path.stem))
            blocks, warnings = _scan(record['messages'])
            conversations.append(_summary(record, flagged=bool(blocks or warnings)))
        conversations.sort(key=lambda record: record['updated_at'], reverse=True)
        return dict(ok=True, conversations=conversations, retention_days=RETENTION_DAYS)


def searchable_conversations(snapshot, max_bytes):
    """Return only valid, unflagged history records for the local global-search operation."""
    with _lock:
        folder = _folder(snapshot)
        if not folder.exists():
            return [], 0, 0, False
        records, skipped = [], 0
        scanned_bytes, processed, partial = 0, 0, False
        for path in folder.iterdir():
            if path.suffix != '.json' or not _ID.fullmatch(path.stem):
                continue
            try:
                path = _record_path(folder, path.stem)
                if processed >= MAX_CONVERSATIONS:
                    partial = True
                    break
                size = path.stat().st_size
                if size > max_bytes - scanned_bytes:
                    partial = True
                    break
                record = _read(_record_path(folder, path.stem))
                scanned_bytes += size
                processed += 1
                if record['id'] != path.stem:
                    skipped += 1
                    continue
                updated = _time(record.get('updated_at'))
                if updated is None or updated < _now() - timedelta(days=RETENTION_DAYS):
                    continue
                blocks, warnings = _scan(record['messages'])
                if blocks or warnings:
                    skipped += 1
                    continue
            except (OSError, ValueError):
                skipped += 1
                continue
            records.append(record)
        return records, skipped, scanned_bytes, partial


def load_conversation(snapshot, body):
    with _lock:
        folder = _folder(snapshot)
        conversation_id = body.get('id') if isinstance(body, dict) else None
        if not isinstance(conversation_id, str) or not _ID.fullmatch(conversation_id):
            return dict(ok=False, message='Identificador de conversación no válido.')
        if folder.exists():
            _prune(folder)
        path = _record_path(folder, conversation_id)
        if not path.is_file():
            return dict(ok=False, message='No existe esa conversación.')
        record = _read(path)
        if record['id'] != path.stem:
            return dict(ok=False, flagged=True, message='El registro no coincide con su identificador. Puedes eliminarlo desde el historial.')
        blocks, warnings = _scan(record['messages'])
        if blocks or warnings:
            return dict(ok=False, flagged=True, message='El registro contiene texto sensible o rutas privadas; se oculta. Puedes eliminarlo desde el historial.')
        return dict(ok=True, conversation=record, retention_days=RETENTION_DAYS)


def save_conversation(snapshot, body):
    if not isinstance(body, dict) or not isinstance(body.get('messages'), list):
        return dict(ok=False, message='La conversación no tiene un formato válido.')
    messages = body['messages']
    if not messages or len(messages) > MAX_MESSAGES:
        return dict(ok=False, message='El historial debe tener entre 1 y 100 mensajes.')
    normalized, total = [], 0
    for message in messages:
        if not isinstance(message, dict) or set(message) - {'role', 'content', 'client', 'model', 'effort', 'agent'}:
            return dict(ok=False, message='Un mensaje contiene campos no permitidos.')
        role, content = message.get('role'), message.get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str) or '\x00' in content:
            return dict(ok=False, message='Un mensaje no es válido.')
        try:
            size = len(content.encode('utf-8'))
        except UnicodeEncodeError:
            return dict(ok=False, message='Un mensaje no es texto UTF-8 válido.')
        total += size
        if size > MAX_MESSAGE_BYTES or total > MAX_BYTES // 2:
            return dict(ok=False, message='La conversación supera el límite de almacenamiento.')
        normalized.append(dict(role=role, content=content,
            client=message.get('client', '') if isinstance(message.get('client', ''), str) else '',
            model=message.get('model', '') if isinstance(message.get('model', ''), str) else '',
            effort=message.get('effort', '') if isinstance(message.get('effort', ''), str) else '',
            agent=message.get('agent', '') if isinstance(message.get('agent', ''), str) else ''))
    blocks, warnings = _scan(normalized)
    if blocks or warnings:
        return dict(ok=False, flagged=True, message='No se guardó: revisa posibles credenciales o rutas personales. La respuesta permanece en pantalla.')
    now = _now().isoformat()
    conversation_id = body.get('id')
    is_new = conversation_id is None
    if is_new:
        conversation_id = uuid.uuid4().hex
    if not isinstance(conversation_id, str) or not _ID.fullmatch(conversation_id):
        return dict(ok=False, message='Identificador de conversación no válido.')
    record = dict(version=1, id=conversation_id, created_at=now, updated_at=now, messages=normalized)
    encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if len(encoded) > MAX_BYTES:
        return dict(ok=False, message='La conversación supera el límite de almacenamiento.')
    with _lock:
        folder = _folder(snapshot, create=True)
        _prune(folder)
        path = _record_path(folder, conversation_id)
        if is_new and path.exists():
            return dict(ok=False, message='No se pudo reservar el historial. Conserva la conversación en pantalla.')
        if is_new and _conversation_count(folder) >= MAX_CONVERSATIONS:
            return dict(ok=False, message='El historial alcanzó el límite de conversaciones. Elimina alguna antes de crear otra.')
        if not is_new:
            if not path.is_file():
                return dict(ok=False, message='La conversación ya no existe.')
            previous = _read(path)
            if previous.get('id') != conversation_id:
                return dict(ok=False, flagged=True, message='El registro no coincide con su identificador.')
            record['created_at'] = previous['created_at']
            encoded = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', prefix='.wai-chat-', suffix='.tmp',
                                             dir=folder, delete=False) as target:
                temporary = Path(target.name)
                target.write(encoded)
                target.flush()
                os.fsync(target.fileno())
            if is_new:
                os.link(temporary, path)
            else:
                os.replace(temporary, path)
                temporary = None
        except FileExistsError:
            return dict(ok=False, message='No se pudo reservar el historial. Conserva la conversación en pantalla.')
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        _prune(folder)
    return dict(ok=True, conversation=_summary(record), retention_days=RETENTION_DAYS)


def delete_conversation(snapshot, body):
    with _lock:
        folder = _folder(snapshot)
        conversation_id = body.get('id') if isinstance(body, dict) else None
        if not isinstance(conversation_id, str) or not _ID.fullmatch(conversation_id):
            return dict(ok=False, message='Identificador de conversación no válido.')
        path = _record_path(folder, conversation_id)
        if not path.is_file():
            return dict(ok=False, message='No existe esa conversación.')
        path.unlink()
        return dict(ok=True, message='Conversación eliminada.')
