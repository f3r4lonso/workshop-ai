"""Private, document-scoped recovery bytes; never accepts caller-selected filenames."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import hashlib
import os
from pathlib import Path
import re
import uuid

import workshop_data

_ID = re.compile(r'^[0-9]{20}-[a-f0-9]{32}$')
MAX_BYTES = 1024 * 1024


def _folder(root, relative, create=False):
    root = Path(root).absolute()
    folder = root / '.workshop-ai' / 'versions' / hashlib.sha256(str(relative).replace('\\', '/').encode()).hexdigest()
    # Check every ancestor, including the workspace itself, before mkdir/open.
    for part in (root, root / '.workshop-ai', root / '.workshop-ai/versions', folder):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('El almacén de versiones está enlazado; no se ha guardado.')
        if part.exists() and not part.is_dir():
            raise ValueError('El almacén de versiones no es una carpeta.')
    if workshop_data.is_linked_path(str(root), str(root.anchor)) or folder.resolve() != folder:
        raise ValueError('El almacén de versiones no es seguro.')
    if create:
        folder.mkdir(parents=True, exist_ok=True)
        _folder(root, relative)
    return folder


def _entries(root, relative):
    folder = _folder(root, relative)
    if not folder.exists():
        return []
    entries = []
    for path in folder.iterdir():
        if path.suffix == '.bak' and _ID.fullmatch(path.stem):
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()) or not path.is_file():
                raise ValueError('Versión enlazada o no válida.')
            entries.append(path)
    return sorted(entries, reverse=True)


def list_versions(root, relative):
    return [dict(id=p.stem, version_id=p.stem, created_at=datetime.strptime(p.stem[:20], '%Y%m%d%H%M%S%f').replace(tzinfo=timezone.utc).isoformat(), size=p.stat().st_size)
            for p in _entries(root, relative)]


def read_version(root, relative, version_id):
    if not isinstance(version_id, str) or not _ID.fullmatch(version_id):
        raise ValueError('Identificador de versión no válido.')
    folder = _folder(root, relative)
    path = folder / (version_id + '.bak')
    if path not in _entries(root, relative):
        raise ValueError('No existe esa versión para este documento.')
    with path.open('rb') as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('La versión supera el límite de edición.')
    return raw


def backup(root, relative, raw):
    folder = _folder(root, relative, create=True)
    version_id = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f') + '-' + uuid.uuid4().hex
    path = folder / (version_id + '.bak')
    with path.open('xb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    return version_id


def prune(root, relative):
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    for index, path in enumerate(_entries(root, relative)):
        created = datetime.strptime(path.stem[:20], '%Y%m%d%H%M%S%f').replace(tzinfo=timezone.utc)
        if index >= 50 and created < cutoff:
            path.unlink()
