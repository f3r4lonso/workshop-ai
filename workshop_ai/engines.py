"""Engine registry shared by the `wai` CLI and the app server (v2 architecture section 6).

`engines.json` is the single list of AI engines; levels follow infra `docs/workshop-ai-v2/engines.md`.
"""

import json
import re
from pathlib import Path

REGISTRY_PATH = Path(__file__).with_name("engines.json")
SCHEMA = "workshop-ai.engines.v1"
KINDS = ("cli", "local-runtime", "service", "web", "desktop", "mcp")
LOCATIONS = ("local", "nube")
WAI_IMPLEMENTED = ("claude", "codex")  # clients with start/handoff code in clients.py
COMMAND_RE = re.compile(r"[a-z0-9]+")
TEXT_KEYS = ("name", "guide", "good_for", "next_step")
REQUIRED = ("id", "name", "kind", "command", "url", "guide", "location", "level", "target", "console",
            "wai_client", "good_for", "next_step")


class RegistryError(ValueError):
    pass


def validate(data):
    """Return the engine list, or raise RegistryError describing the first problem."""
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise RegistryError(f"schema must be {SCHEMA}")
    levels = data.get("levels")
    if not isinstance(levels, list) or len(levels) != 5:
        raise RegistryError("levels must list the five level names")
    engines = data.get("engines")
    if not isinstance(engines, list) or not engines:
        raise RegistryError("engines must be a non-empty list")
    seen = set()
    for engine in engines:
        if not isinstance(engine, dict):
            raise RegistryError("each engine must be an object")
        missing = [key for key in REQUIRED if key not in engine]
        eid = engine.get("id")
        if missing:
            raise RegistryError(f"engine {eid!r} misses {', '.join(missing)}")
        if not isinstance(eid, str) or not eid or eid in seen:
            raise RegistryError(f"engine id {eid!r} is empty or repeated")
        seen.add(eid)
        if engine["kind"] not in KINDS or engine["location"] not in LOCATIONS:
            raise RegistryError(f"engine {eid!r} has an unknown kind or location")
        if any(not isinstance(engine[key], str) or not engine[key].strip() for key in TEXT_KEYS):
            raise RegistryError(f"engine {eid!r} needs non-empty text in {', '.join(TEXT_KEYS)}")
        if not isinstance(engine["console"], bool) or not isinstance(engine["wai_client"], bool):
            raise RegistryError(f"engine {eid!r} console and wai_client must be true or false")
        if engine["wai_client"] and eid not in WAI_IMPLEMENTED:
            raise RegistryError(f"engine {eid!r} cannot be a wai client: wai only implements {', '.join(WAI_IMPLEMENTED)}")
        level, target = engine["level"], engine["target"]
        if not (type(level) is int and type(target) is int and 0 <= level <= target <= 4):
            raise RegistryError(f"engine {eid!r} needs 0 <= level <= target <= 4")
        command = engine["command"]
        if command is not None and (not isinstance(command, str) or not COMMAND_RE.fullmatch(command)):
            raise RegistryError(f"engine {eid!r} command must be a bare program name")
        if (engine["console"] or engine["wai_client"]) and command is None:
            raise RegistryError(f"engine {eid!r} opens a console but has no command")
        if engine["console"] and level < 1:
            raise RegistryError(f"engine {eid!r} opens a console below level 1")
        url = engine["url"]
        if not isinstance(url, str) or not url.startswith("https://"):
            raise RegistryError(f"engine {eid!r} url must be https")
    return engines


def load(path=REGISTRY_PATH):
    with open(path, encoding="utf-8") as handle:
        return validate(json.load(handle))


def level_names(path=REGISTRY_PATH):
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    validate(data)
    if not all(isinstance(name, str) and name for name in data["levels"]):
        raise RegistryError("level names must be text")
    return list(data["levels"])


def wai_clients(path=REGISTRY_PATH):
    """Ids of the engines `wai` can start or hand a task to, in registry order."""
    return tuple(engine["id"] for engine in load(path) if engine["wai_client"])
