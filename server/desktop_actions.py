"""Owner-only fixed desktop actions; personal text never enters the catalogue."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import threading

import resource_interaction as documents
import workshop_data

NOTE_PATH = 'infra/docs/notes/my-notes.txt'
_note_lock = threading.Lock()


def _checked(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root) or path.resolve() != path:
        raise documents.ResourceError('La ruta contiene un enlace o un destino no permitido.')
    if workshop_data.is_linked_path(str(path), str(root)) or workshop_data._is_link(str(root)):
        raise documents.ResourceError('No se permiten enlaces en este destino.')
    return path


def _ignored(snapshot, find_executable):
    root = Path(snapshot.workshop_root).absolute()
    infra = _checked(root, root / 'infra')
    git = find_executable('git', str(root))
    if not git or not infra.is_dir():
        raise documents.ResourceError('No se pudo verificar que tus notas sean privadas. Comprueba Git y la carpeta infra.')
    command = [git, '-c', f'safe.directory={infra.as_posix()}', '-C', str(infra)]
    options = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=5, shell=False)
    try:
        ignored = subprocess.run(command + ['check-ignore', '--no-index', '-q', '--',
                                           'docs/notes/my-notes.txt'], **options)
        tracked = subprocess.run(command + ['ls-files', '--error-unmatch', '--',
                                           'docs/notes/my-notes.txt'], **options)
    except (OSError, subprocess.SubprocessError):
        raise documents.ResourceError('No se pudo comprobar la privacidad de tus notas. No se ha creado el archivo.') from None
    if ignored.returncode != 0 or tracked.returncode != 1:
        raise documents.ResourceError('Tus notas deben estar ignoradas por Git y fuera de los archivos versionados. Revisa infra/.gitignore.')


def ensure_note(snapshot, find_executable):
    """Create exclusively, after an ignore/tracking check; existing bytes are never read here."""
    root = Path(snapshot.workshop_root).absolute()
    with _note_lock:
        path = _checked(root, root / NOTE_PATH)
        _ignored(snapshot, find_executable)
        path.parent.mkdir(parents=True, exist_ok=True)
        _checked(root, path)
        try:
            with path.open('xb'):
                pass
        except FileExistsError:
            if not path.is_file():
                raise documents.ResourceError('El destino de tus notas no es un archivo.') from None
        _checked(root, path)
        return path


def _launch(snapshot, name, target):
    if os.name != 'nt':
        raise documents.ResourceError('Este acceso directo requiere Windows.')
    root = Path(snapshot.workshop_root).absolute()
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    if not windows.is_absolute() or windows.resolve() != windows or windows.is_relative_to(root):
        raise documents.ResourceError('No se encuentra una instalación de Windows de confianza.')
    executable = windows / ('System32/notepad.exe' if name == 'notepad' else 'explorer.exe')
    if (not executable.is_file() or workshop_data.is_linked_path(str(executable), str(windows))
            or workshop_data._is_link(str(windows))):
        raise documents.ResourceError('No se encuentra la aplicación de Windows. Comprueba su instalación.')
    try:
        subprocess.Popen([str(executable), str(target)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         cwd=str(windows), shell=False)
    except OSError:
        raise documents.ResourceError('No se pudo solicitar la apertura. Comprueba los permisos de Windows.') from None


def handle(action, snapshot, body, find_executable):
    """All callers use authenticated exact-origin POST; browser paths are never accepted."""
    try:
        if any(key in body for key in ('path', 'id', 'target')):
            raise documents.ResourceError('Este acceso directo usa un destino fijo; no acepta rutas.')
        root = Path(snapshot.workshop_root).absolute()
        if action == 'open-workshop':
            if body:
                raise documents.ResourceError('El acceso a Workshop no admite argumentos.')
            _checked(root, root)
            if not root.is_dir():
                raise documents.ResourceError('No se encuentra la carpeta Workshop.')
            _launch(snapshot, 'explorer', root)
            return dict(ok=True, message='Se ha solicitado abrir Workshop en el Explorador.')
        note = ensure_note(snapshot, find_executable)
        if action == 'notes-open':
            if body:
                raise documents.ResourceError('El acceso al Bloc de notas no admite argumentos.')
            _launch(snapshot, 'notepad', note)
            return dict(ok=True, message='Se ha solicitado abrir el Bloc de notas')
        fixed = dict(body, path=NOTE_PATH)
        handlers = {
            'notes-document': documents.document,
            'notes-save': documents.save,
            'notes-versions': documents.versions,
            'notes-version': documents.read_version,
            'notes-restore': documents.restore,
        }
        handler = handlers.get(action)
        if handler is None:
            raise documents.ResourceError('Acción desconocida.')
        result = handler(snapshot, fixed, allow_private_note=True)
        result['private'] = True
        return result
    except (documents.ResourceError, OSError, ValueError, TypeError) as error:
        # ResourceError messages contain guidance, never note text or subprocess output.
        return dict(ok=False, message=str(error) if isinstance(error, documents.ResourceError)
                    else 'No se pudo abrir el acceso privado. Revisa los permisos y vuelve a intentarlo.')
