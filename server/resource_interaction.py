"""Bounded canonical document editing and reuse of the local reader pipeline."""
from __future__ import annotations

import hashlib
import base64
import binascii
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading

import workshop_data
import document_versions

READER_ROOT = Path(__file__).resolve().parents[2] / 'ai-reading-assistant'
MAX_TEXT_BYTES = 1024 * 1024
MAX_FILE_BYTES = 20 * 1024 * 1024
_save_lock = threading.Lock()
_BLOCKED = {'.aws', '.ssh', '.agents', '__pycache__', 'dist', 'build', 'pilot-results',
            'secrets', 'credentials', 'config', 'configs'}


class ResourceError(Exception):
    pass


def safe_path(snapshot, body, *, allow_private_note=False):
    root = Path(snapshot.workshop_root).absolute()
    if body.get('id'):
        item = snapshot.by_id.get(body['id']) if isinstance(body['id'], str) else None
        if item is None:
            raise ResourceError('Recurso desconocido. Pulsa Actualizar.')
        path = Path(item.path).absolute()
    else:
        relative = body.get('path')
        if not isinstance(relative, str) or not relative or len(relative) > 1000:
            raise ResourceError('Indica una ruta relativa del Workshop.')
        parts = relative.replace('\\', '/').split('/')
        if any(p in ('', '.', '..') or ':' in p for p in parts) or relative.startswith(('/', '\\')):
            raise ResourceError('Ruta no permitida.')
        path = root.joinpath(*parts)
    try:
        relative = path.relative_to(root)
    except ValueError:
        raise ResourceError('El archivo debe estar dentro del Workshop.') from None
    private_note = relative.as_posix().lower() == 'infra/docs/notes/my-notes.txt'
    if private_note and not allow_private_note:
        raise ResourceError('Las notas personales requieren su acceso privado.')
    if (not relative.parts or any(p.startswith('.') or p.lower() in _BLOCKED for p in relative.parts)
            or (workshop_data.is_excluded_path(str(path)) and not (private_note and allow_private_note))
            or workshop_data.is_linked_path(str(path), str(root))):
        raise ResourceError('Archivo protegido, generado o enlazado: acceso no permitido.')
    if path.resolve() != path or not path.is_file():
        raise ResourceError('El archivo no existe o no es accesible.')
    return path, relative


def eligible(relative):
    parts = [p.lower() for p in relative.parts]
    if relative.suffix.lower() not in ('.md', '.txt'):
        return False
    if len(parts) == 1 and parts[0] in ('index.md', 'workshop-context.md'):
        return True
    if len(parts) >= 3 and parts[:2] == ['projects', 'music'] and relative.suffix.lower() == '.md':
        return True
    if parts[0] == 'infra' and len(parts) >= 3 and parts[1] in ('docs', 'tasks', 'agents', 'skills'):
        return True
    return (len(parts) >= 3 and parts[0] == 'applications'
            and (parts[2] == 'docs' or (len(parts) == 3 and parts[2] == 'readme.md')))


def read_bytes(path, limit):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    if len(raw) > limit:
        raise ResourceError(f'El archivo supera el límite de {limit // 1024} KB; no se ha truncado.')
    return raw


def version(raw):
    return hashlib.sha256(raw).hexdigest()


def _header(snapshot, text):
    try:
        import resource_headers
        parsed = resource_headers.parse_frontmatter(Path(snapshot.workshop_root), text)
        tools = re.split(r'[^A-Za-z0-9_-]+', parsed.fields.get('tools', ''))
        warnings = ['Estas herramientas pueden ejecutar comandos o acceder a Internet: ' + ', '.join(
            tool for tool in tools if tool in ('Bash', 'WebFetch', 'WebSearch'))] if any(
                tool in tools for tool in ('Bash', 'WebFetch', 'WebSearch')) else []
        return dict(safe=True, fields=parsed.fields, editable_fields=list(parsed.editable_fields), raw_header=parsed.raw_header, reason='', warnings=warnings)
    except (ValueError, ImportError, OSError):
        return dict(safe=False, fields={}, editable_fields=[], raw_header=_metadata(text), reason='Cabecera no compatible: usa el modo avanzado y conserva sus metadatos.')


def document(snapshot, body, *, allow_private_note=False):
    path, relative = safe_path(snapshot, body, allow_private_note=allow_private_note)
    if path.suffix.lower() not in ('.md', '.markdown', '.txt'):
        raise ResourceError('Solo se pueden editar documentos de texto compatibles.')
    raw = read_bytes(path, MAX_TEXT_BYTES)
    text = raw.decode('utf-8-sig')
    if '\x00' in text:
        raise ResourceError('El archivo parece binario.')
    editable = eligible(relative)
    return dict(ok=True, text=text, version=version(raw), base_sha256=version(raw), editable=editable,
                path=relative.as_posix(), header=_header(snapshot, text),
                reason='' if editable else 'Solo lectura: recurso fuera de las áreas editables.')


def _metadata(text):
    match = re.match(r'\A\ufeff?---[^\S\n]*\n.*?\n---[^\S\n]*(?:\n|\Z)', text, re.S)
    return match.group(0) if match else None


def _validate_header(snapshot, old_text, text, body):
    old_header, new_header = _metadata(old_text), _metadata(text)
    if old_header == new_header:
        return
    try:
        import resource_headers
        previous = resource_headers.parse_frontmatter(Path(snapshot.workshop_root), old_text)
        current = resource_headers.parse_frontmatter(Path(snapshot.workshop_root), text)
    except (ValueError, ImportError, OSError):
        raise ResourceError('Conserva intacta la cabecera no compatible; solo puedes cambiar el cuerpo.') from None
    updates = {key: value for key, value in current.fields.items() if previous.fields.get(key) != value}
    if set(previous.fields) != set(current.fields) or any(key not in previous.editable_fields for key in updates):
        raise ResourceError('Conserva los campos desconocidos de la cabecera.')
    # Compare everything except safely editable scalar lines, including unknown fields/comments.
    known = set(previous.editable_fields) & set(current.editable_fields)
    def protected_header(parsed):
        return ''.join(line for line in parsed.raw_header.splitlines(keepends=True)
                       if not any(re.match(r'^' + re.escape(key) + r':', line) for key in known))
    if protected_header(previous) != protected_header(current):
        raise ResourceError('Conserva los campos desconocidos y el formato de la cabecera.')
    if any(key in updates for key in ('tools', 'model', 'disallowedTools')) and body.get('review_tools_model') is not True:
        raise ResourceError('Revisa y confirma por separado los cambios de herramientas y modelo.')
    if 'Agent' in re.split(r'[^A-Za-z0-9_-]+', current.fields.get('tools', '')):
        raise ResourceError('Agent no está permitido en las herramientas.')


def _conflict(old, text):
    current = old.decode('utf-8-sig')
    return dict(ok=False, code='conflict', message='El archivo cambió. Conserva tu borrador y revisa las diferencias.',
                current_text=current, current_sha256=version(old), submitted_text=text, text=current,
                version=version(old), base_sha256=version(old))


def _maintenance(snapshot, relative):
    parts = [p.lower() for p in relative.parts]
    if parts[:2] != ['infra', 'agents']:
        return []
    adapter = Path(snapshot.workshop_root) / 'infra/scripts/codex-adapter.py'
    if (not adapter.is_file() or workshop_data.is_linked_path(str(adapter), snapshot.workshop_root)
            or adapter.resolve() != adapter):
        return [dict(command='agents', ok=False, output='El adaptador no existe o está enlazado.')]
    commands = [['agents']]
    if len(parts) > 2 and parts[2] == 'personal-assistants':
        commands.append(['personal'])
    commands += [[args[0], '--check'] for args in list(commands)]
    results = []
    for args in commands:
        try:
            # Temporary output file bounds memory even if the adapter emits excessive output.
            with tempfile.TemporaryFile() as output:
                result = subprocess.run([sys.executable, str(adapter), *args], cwd=str(adapter.parent.parent),
                                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                        timeout=30, check=False)
                output.seek(0)
                summary = output.read(8193)
            code = result.returncode if isinstance(result.returncode, int) else 0
            results.append(dict(command=' '.join(args), ok=code == 0, returncode=code,
                                output=summary[:8192].decode('utf-8', errors='replace'), truncated=len(summary) > 8192))
        except (OSError, subprocess.SubprocessError):
            results.append(dict(command=' '.join(args), ok=False, output='No se pudo completar el mantenimiento.'))
    return results


def save(snapshot, body, *, allow_private_note=False):
    text = body.get('text')
    if not isinstance(text, str) or '\x00' in text or (not text.strip() and not allow_private_note):
        raise ResourceError('El texto no puede estar vacío ni contener datos binarios.')
    if body.get('header_fields') is not None:
        try:
            import resource_headers
            text = resource_headers.parse_frontmatter(Path(snapshot.workshop_root), text).with_updates(body['header_fields'])
        except (ValueError, TypeError, ImportError):
            raise ResourceError('No se pudieron aplicar los datos de la ficha.') from None
    raw = text.encode('utf-8')
    if len(raw) > MAX_TEXT_BYTES:
        raise ResourceError('El texto supera el límite de edición de 1 MB.')
    base = body.get('base_sha256', body.get('version'))
    with _save_lock:
        path, relative = safe_path(snapshot, body, allow_private_note=allow_private_note)
        if not eligible(relative):
            raise ResourceError('Este recurso es de solo lectura.')
        old = read_bytes(path, MAX_TEXT_BYTES)
        if base != version(old):
            return _conflict(old, text)
        # Browser textareas use LF; retain an existing Windows document's line endings.
        if b'\r\n' in old and b'\n' not in old.replace(b'\r\n', b''):
            text = text.replace('\r\n', '\n').replace('\n', '\r\n')
            raw = text.encode('utf-8')
            if len(raw) > MAX_TEXT_BYTES:
                raise ResourceError('El texto supera el límite de edición de 1 MB.')
        parts = [p.lower() for p in relative.parts]
        if parts[:2] in (['infra', 'agents'], ['infra', 'skills']):
            _validate_header(snapshot, old.decode('utf-8-sig'), text, body)
        if old.startswith(b'\xef\xbb\xbf'):
            raw = b'\xef\xbb\xbf' + raw
            if len(raw) > MAX_TEXT_BYTES:
                raise ResourceError('El texto supera el límite de edición de 1 MB.')
        safe_path(snapshot, body, allow_private_note=allow_private_note)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='wb', prefix='.workshop-draft-', suffix='.tmp', dir=path.parent, delete=False) as target:
                temporary = Path(target.name)
                target.write(raw)
                target.flush()
                os.fsync(target.fileno())
            safe_path(snapshot, body, allow_private_note=allow_private_note)
            latest = read_bytes(path, MAX_TEXT_BYTES)
            if version(latest) != base:
                return _conflict(latest, text)
            document_versions.backup(snapshot.workshop_root, relative, old)
            safe_path(snapshot, body, allow_private_note=allow_private_note)
            latest = read_bytes(path, MAX_TEXT_BYTES)
            if version(latest) != base:
                return _conflict(latest, text)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        try:
            document_versions.prune(snapshot.workshop_root, relative)
        except (OSError, ValueError):
            pass  # Retention must never make an already successful save look failed.
        maintenance = _maintenance(snapshot, relative)
        failed = any(not result['ok'] for result in maintenance)
        return dict(ok=True, version=version(raw), base_sha256=version(raw), text=text, header=_header(snapshot, text),
                    message='Guardado.' + (' Revisa el mantenimiento de adaptadores.' if failed else ''),
                    maintenance=maintenance, maintenanceRequired=failed)


def versions(snapshot, body, *, allow_private_note=False):
    _, relative = safe_path(snapshot, body, allow_private_note=allow_private_note)
    return dict(ok=True, versions=document_versions.list_versions(snapshot.workshop_root, relative))


def read_version(snapshot, body, *, allow_private_note=False):
    _, relative = safe_path(snapshot, body, allow_private_note=allow_private_note)
    raw = document_versions.read_version(snapshot.workshop_root, relative, body.get('version_id'))
    return dict(ok=True, text=raw.decode('utf-8-sig'), version_id=body.get('version_id'), base_sha256=version(raw))


def restore(snapshot, body, *, allow_private_note=False):
    prior = read_version(snapshot, body, allow_private_note=allow_private_note)
    return save(snapshot, dict(body, text=prior['text']), allow_private_note=allow_private_note)


_TEMPLATES = {'document': ('Documento', 'document.md'), 'task': ('Tarea', 'task.md')}
_CREATE_DESTINATIONS = {
    'workshop-docs': ('infra/docs', 'Documentación del Workshop'),
    'workshop-tasks': ('infra/tasks/projects/workshop-ai', 'Tareas de Workshop AI'),
    'app-docs': ('applications/workshop-ai/docs', 'Documentación de Workshop AI'),
    'music-docs': ('projects/music', 'Documentación de proyectos musicales'),
}


def templates(snapshot):
    root = Path(snapshot.workshop_root).absolute()
    destinations = []
    for key, (relative, label) in _CREATE_DESTINATIONS.items():
        folder = root.joinpath(*relative.split('/'))
        if (folder.is_dir() and folder.resolve() == folder and
                not workshop_data.is_linked_path(str(folder), str(root)) and
                not workshop_data.is_excluded_path(str(folder))):
            destinations.append(dict(id=key, label=label, path=relative))
    return dict(ok=True, templates=[dict(id=key, template_id=key, name=value[0]) for key, value in _TEMPLATES.items()],
                destinations=destinations)


def create(snapshot, body):
    root = Path(snapshot.workshop_root).absolute()
    template_id = body.get('template_id', body.get('template'))
    if 'destination' in body:
        if template_id is not None:
            raise ResourceError('Elige una plantilla o guarda el borrador, no ambas opciones.')
        destination = body.get('destination')
        target = _CREATE_DESTINATIONS.get(destination) if isinstance(destination, str) else None
        name = body.get('name')
        text = body.get('text')
        if not target or not isinstance(name, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or len(name) > 90:
            raise ResourceError('Elige una carpeta disponible y un nombre en minúsculas con guiones.')
        if not isinstance(text, str) or '\x00' in text:
            raise ResourceError('El contenido del borrador no es válido.')
        try:
            raw = text.encode('utf-8')
        except UnicodeEncodeError:
            raise ResourceError('El contenido debe ser texto UTF-8 válido.') from None
        if len(raw) > MAX_TEXT_BYTES:
            raise ResourceError('El documento supera el límite de 1 MB.')
        relative = Path(*target[0].split('/'), f'{name}.md')
    else:
        if template_id not in _TEMPLATES:
            raise ResourceError('Selecciona una plantilla disponible.')
        relative = body.get('path')
        if not isinstance(relative, str) or not relative or len(relative) > 1000:
            raise ResourceError('Indica una ruta nueva válida.')
        parts = relative.split('/')
        if any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*(?:\.md)?', part) for part in parts) or not relative.endswith('.md'):
            raise ResourceError('Usa nombres en minúsculas y kebab-case con extensión .md.')
        relative = Path(*parts)
        template = root / 'infra/docs/manuals/templates' / _TEMPLATES[template_id][1]
        safe_path(snapshot, {'path': template.relative_to(root).as_posix()})
        raw = read_bytes(template, MAX_TEXT_BYTES)
    if not eligible(relative) or relative.parts[:2] in (('infra', 'agents'), ('infra', 'skills')):
        raise ResourceError('Crea documentos en una carpeta de documentación permitida.')
    path = root / relative
    # Only existing, safe folders may be selected; no implicit arbitrary directory creation.
    if not path.parent.is_dir() or workshop_data.is_linked_path(str(path), str(root)) or path.resolve() != path:
        raise ResourceError('La carpeta no existe o está enlazada.')
    if workshop_data.is_excluded_path(str(path)) or any(p.startswith('.') or p.lower() in _BLOCKED for p in relative.parts):
        raise ResourceError('Ruta protegida.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix='.wai-create-', suffix='.tmp',
                                         dir=path.parent, delete=False) as target:
            temporary = Path(target.name)
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        with _save_lock:
            if path.exists():
                raise ResourceError('Ya existe un archivo con ese nombre.')
            if (workshop_data.is_linked_path(str(path), str(root)) or path.resolve() != path
                    or path.parent.resolve() != path.parent):
                raise ResourceError('Ruta enlazada no permitida.')
            try:
                os.link(temporary, path)
            except FileExistsError:
                raise ResourceError('Ya existe un archivo con ese nombre.') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return document(snapshot, {'path': relative.as_posix()})


def reader_modules():
    if not (READER_ROOT / 'reading_assistant' / 'extract.py').is_file():
        raise ResourceError('No se encuentra ai-reading-assistant en applications.')
    if str(READER_ROOT) not in sys.path:
        sys.path.insert(0, str(READER_ROOT))
    from reading_assistant import clean, extract, language, translate
    return clean, extract, language, translate


def read_document(snapshot, body):
    clean, extract, language, _ = reader_modules()
    path, relative = safe_path(snapshot, body)
    if path.suffix.lower() not in extract.SUPPORTED_EXTENSIONS:
        raise ResourceError(extract.MSG_PDF if path.suffix.lower() == '.pdf' else extract.MSG_UNSUPPORTED)
    text = clean.clean_text(extract.extract_text(path.name, read_bytes(path, MAX_FILE_BYTES)))
    if not text.strip():
        raise ResourceError('No hay texto legible en el documento.')
    return dict(ok=True, original=text, language=language.detect_language(text), path=str(relative))


def prepare_text(body):
    """Clean and identify explicitly pasted text without persisting or logging it."""
    clean, _, language, _ = reader_modules()
    text = body.get('text')
    if not isinstance(text, str) or not text.strip() or '\x00' in text:
        raise ResourceError('Pega texto legible para preparar la lectura.')
    if len(text.encode('utf-8')) > MAX_TEXT_BYTES:
        raise ResourceError('El texto pegado supera el límite de 1 MB.')
    prepared = clean.clean_text(text)
    if not prepared.strip():
        raise ResourceError('No queda texto legible después de limpiarlo.')
    return dict(ok=True, original=prepared, language=language.detect_language(prepared), path='Texto pegado')


def read_upload(body):
    """Extract a user-selected supported file in memory, with the reader's 20 MB bound."""
    clean, extract, language, _ = reader_modules()
    name, encoded = body.get('name'), body.get('data')
    if not isinstance(name, str) or not name or len(name) > 255 or '/' in name or '\\' in name:
        raise ResourceError('Nombre de archivo no válido.')
    suffix = Path(name).suffix.lower()
    if suffix not in extract.SUPPORTED_EXTENSIONS:
        raise ResourceError(extract.MSG_PDF if suffix == '.pdf' else extract.MSG_UNSUPPORTED)
    if not isinstance(encoded, str) or len(encoded) > ((MAX_FILE_BYTES + 2) // 3) * 4:
        raise ResourceError('El archivo supera el límite de 20 MB.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ResourceError('No se pudo leer el archivo seleccionado.') from None
    if not raw or len(raw) > MAX_FILE_BYTES:
        raise ResourceError('El archivo está vacío o supera el límite de 20 MB.')
    text = clean.clean_text(extract.extract_text(name, raw))
    if not text.strip():
        raise ResourceError('No hay texto legible en el documento.')
    return dict(ok=True, original=text, language=language.detect_language(text), path=name)


def translate_text(body):
    _, _, language, translate = reader_modules()
    text = body.get('text')
    if not isinstance(text, str) or not text.strip():
        raise ResourceError('No hay texto para traducir.')
    skipped = language.detect_language(text)['is_spanish']
    return dict(ok=True, text=text if skipped else translate.translate_to_spanish(text), skipped=skipped)


def handle(action, snapshot, body, find_executable):
    try:
        if action == 'global-search':
            import global_search
            return global_search.search(snapshot, body)
        if action in ('resource-registration-preview', 'resource-registration-save'):
            import resource_registration
            return resource_registration.handle(action, snapshot, body)
        if action == 'document':
            return document(snapshot, body)
        if action == 'save':
            return save(snapshot, body)
        if action == 'versions':
            return versions(snapshot, body)
        if action == 'version':
            return read_version(snapshot, body)
        if action == 'restore':
            return restore(snapshot, body)
        if action == 'templates':
            return templates(snapshot)
        if action == 'create':
            return create(snapshot, body)
        if action == 'read':
            return read_document(snapshot, body)
        if action == 'prepare-text':
            return prepare_text(body)
        if action == 'upload':
            return read_upload(body)
        if action == 'translate':
            return translate_text(body)
        if action == 'reader-status':
            return dict(ok=True, **reader_modules()[3].availability())
        if action in ('conversation-list', 'conversation-load', 'conversation-save', 'conversation-delete'):
            import conversation_store
            if action == 'conversation-list':
                return conversation_store.list_conversations(snapshot)
            if action == 'conversation-load':
                return conversation_store.load_conversation(snapshot, body)
            if action == 'conversation-save':
                return conversation_store.save_conversation(snapshot, body)
            return conversation_store.delete_conversation(snapshot, body)
        if action in ('registry', 'dispatch'):
            import client_dispatch
            if action == 'registry':
                return dict(ok=True, **client_dispatch.registry(snapshot, find_executable))
            if body.get('agent'):
                item = snapshot.by_id.get(body['agent']) if isinstance(body['agent'], str) else None
                if item is None or getattr(item, 'section', None) not in ('Agentes', 'Asistentes'):
                    raise ResourceError('Selecciona un perfil de agente válido.')
            profile = document(snapshot, {'id': body['agent']}) if body.get('agent') else None
            if profile and body.get('agentVersion') != profile['version']:
                return dict(ok=False, status='rejected', message='El perfil del agente cambió. Vuelve a cargarlo y revisarlo antes de enviar.')
            role = profile['text'] if profile else ''
            return client_dispatch.dispatch(body, snapshot, find_executable, role_text=role)
        raise ResourceError('Acción desconocida.')
    except (ResourceError, OSError, UnicodeError, ValueError, TypeError) as error:
        return dict(ok=False, message=str(error) if isinstance(error, ResourceError) else 'No se pudo procesar el recurso. Revisa permisos y formato.')
    except Exception as error:
        # Reader errors carry user-facing Spanish messages. Never expose other exception details.
        from reading_assistant.errors import UserFacingError
        return dict(ok=False, message=str(error) if isinstance(error, UserFacingError) else 'No se pudo completar la operación.')
