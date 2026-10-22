"""Load the canonical adapter parser from the active Workshop, never a copy."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def parse_frontmatter(workshop_root: Path, text: str):
    path = Path(workshop_root) / "infra" / "scripts" / "resource_headers.py"
    # Loading code through a redirected ancestor would cross the workspace boundary.
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise ValueError("Shared header parser path is redirected")
        if candidate == Path(workshop_root):
            break
    name = "_workshop_canonical_resource_headers_" + str(abs(hash(str(path.resolve()))))
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ValueError("Shared header parser is unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(name, None)
            raise ValueError("Shared header parser is unavailable") from exc
    return module.parse_frontmatter(text)
