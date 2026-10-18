"""File helpers: atomic writes, hashing, path containment, read-only git queries."""

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


def read_text(path):
    """Read a UTF-8 text file with newlines normalized to \\n."""
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def atomic_write(path, text):
    """Write text so that a failure leaves the previous file untouched."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".wai-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_inside(child, parent):
    """True if child resolves to parent or a path below it (links are resolved)."""
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def git_commit_label(folder):
    """Short commit id of folder's repository, '+dirty' if it has changes; 'no git' otherwise."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=folder,
            capture_output=True, text=True, timeout=20,
        )
        if head.returncode != 0:
            return "no commit"
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=folder,
            capture_output=True, text=True, timeout=20,
        )
        label = head.stdout.strip()
        return label + ("+dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "no git"
