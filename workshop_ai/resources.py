"""Read-only listing of the shared infrastructure contracts (infra docs/ai-architecture.md section 9).

Nothing is copied: each entry points at its canonical file.
"""

import re
from pathlib import Path

from .errors import ENVIRONMENT, WaiError
from .fsutil import read_text

KINDS = ("clients", "agents", "skills", "tasks")


def first_sentence(text, limit=110):
    text = " ".join(text.split())
    match = re.match(r"(.+?[.!?])(\s|$)", text)
    sentence = match.group(1) if match else text
    return sentence if len(sentence) <= limit else sentence[: limit - 1] + "…"


def frontmatter(path):
    """Simple YAML-subset frontmatter: top-level 'key: value' lines between '---' lines."""
    text = read_text(path)
    if not text.startswith("---\n"):
        raise ValueError("no frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("frontmatter not closed")
    fields = {}
    for line in text[4:end].splitlines():
        if line[:1].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def list_clients(infra):
    rows, warnings = [], []
    for readme in sorted((infra / "clients").glob("*/README.md")):
        title = next((l[2:].strip() for l in read_text(readme).splitlines() if l.startswith("# ")), "")
        rows.append({"id": readme.parent.name, "title": title, "path": readme})
    return rows, warnings


def list_agents(infra):
    rows, warnings = [], []
    for path in sorted((infra / "agents").glob("*/*.md")):
        try:
            fm = frontmatter(path)
        except (ValueError, OSError) as exc:
            if path.parent.name != "personal-assistants":
                warnings.append(f"{path.relative_to(infra)}: {exc}")
            continue
        rows.append({
            "area": path.parent.name, "name": fm.get("name", path.stem),
            "description": first_sentence(fm.get("description", "")),
            "tools": fm.get("tools", "(all)"), "path": path,
        })
    return rows, warnings


def list_skills(infra):
    rows, warnings = [], []
    for path in sorted((infra / "skills").glob("*/SKILL.md")):
        try:
            fm = frontmatter(path)
        except (ValueError, OSError) as exc:
            warnings.append(f"{path.relative_to(infra)}: {exc}")
            continue
        rows.append({
            "name": fm.get("name", path.parent.name),
            "description": first_sentence(fm.get("description", "")), "path": path,
        })
    return rows, warnings


def list_tasks(infra):
    rows, warnings = [], []
    for path in sorted((infra / "tasks").glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        lines = read_text(path).splitlines()
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
        status = next((l[len("Status:"):].strip() for l in lines if l.startswith("Status:")), None)
        if status is None:
            warnings.append(f"tasks/{path.name}: no 'Status:' line")
            status = "unknown"
        rows.append({"file": path.name, "title": title, "status": status, "path": path})
    return rows, warnings


LISTERS = {"clients": list_clients, "agents": list_agents, "skills": list_skills, "tasks": list_tasks}


def check_infra(infra):
    infra = Path(infra)
    if not (infra / "AGENTS.md").is_file() or not (infra / "clients").is_dir():
        raise WaiError(
            f"shared infrastructure not found at {infra}: pass --infra <folder> or set WORKSHOP_AI_INFRA",
            ENVIRONMENT,
        )
    return infra


def list_resources(infra, kinds=KINDS):
    infra = check_infra(infra)
    return {kind: LISTERS[kind](infra) for kind in kinds}
