"""Markdown documents with a `key: value` header and `## ` sections (spec section 4).

Parsing keeps everything it does not own: free text, unknown sections and their order.
"""

import re

from .errors import VALIDATION, WaiError

TASK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
CLIENTS = ("claude", "codex")
STATUSES = ("draft", "ready", "in-progress", "blocked", "done")
TASK_REQUIRED_KEYS = ("id", "client", "status", "created", "revision")
TASK_REQUIRED_SECTIONS = ("Objective", "Acceptance criteria", "Next action")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
CRITERION_RE = re.compile(r"^\s*- \[[ xX]\]\s+\S", re.M)


class Doc:
    def __init__(self, header=None, preamble="", sections=None):
        self.header = dict(header or {})
        self.preamble = preamble
        self.sections = [list(s) for s in (sections or [])]

    # sections -----------------------------------------------------------
    def section(self, title):
        for name, body in self.sections:
            if name == title:
                return body
        return None

    def has(self, title):
        return self.section(title) is not None

    def set_section(self, title, content):
        body = content.strip("\n") + "\n\n"
        for item in self.sections:
            if item[0] == title:
                item[1] = body
                return
        self.sections.append([title, body])

    def text(self, title):
        """Section content without HTML comments and surrounding blank lines."""
        body = self.section(title) or ""
        return COMMENT_RE.sub("", body).strip()

    # serialization ------------------------------------------------------
    def dumps(self):
        out = ["---\n"]
        for key, value in self.header.items():
            out.append(f"{key}: {value}\n")
        out.append("---\n")
        out.append(self.preamble)
        for name, body in self.sections:
            out.append(f"## {name}\n{body}")
        text = "".join(out)
        return text.rstrip("\n") + "\n"


def parse(text, source="document"):
    text = text.replace("\r\n", "\n")
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise WaiError(f"{source}: missing header (first line must be '---')", VALIDATION)
    header = {}
    end = None
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            end = i
            break
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise WaiError(f"{source}: header line {i + 1} is not 'key: value': {line!r}", VALIDATION)
        header[key.strip()] = value.strip()
    if end is None:
        raise WaiError(f"{source}: header is not closed with '---'", VALIDATION)

    rest = "\n".join(lines[end + 1:])
    parts = re.split(r"(?m)^## (.*)\n?", rest)
    preamble = parts[0]
    sections = []
    for j in range(1, len(parts), 2):
        sections.append([parts[j].strip(), parts[j + 1]])
    return Doc(header, preamble, sections)


def validate_task_id(task_id, what="task id"):
    if not TASK_ID_RE.match(task_id or ""):
        raise WaiError(
            f"invalid {what} {task_id!r}: use lowercase letters, digits and '-', up to 64 characters "
            "(e.g. t2-empty-csv)"
        )


def task_problems(doc, minimal=False):
    """List of human-readable problems; empty when the task contract is valid.

    minimal=True checks only what is needed to start a session: objective, one criterion, client.
    """
    problems = []
    keys = ("client",) if minimal else TASK_REQUIRED_KEYS
    for key in keys:
        if not doc.header.get(key):
            problems.append(f'missing header key "{key}"')
    client = doc.header.get("client")
    if client and client not in CLIENTS:
        problems.append(f'client must be one of {", ".join(CLIENTS)} (found "{client}")')
    status = doc.header.get("status")
    if not minimal and status and status not in STATUSES:
        problems.append(f'status must be one of {", ".join(STATUSES)} (found "{status}")')
    revision = doc.header.get("revision")
    if not minimal and revision and not revision.isdigit():
        problems.append(f'revision must be a whole number (found "{revision}")')

    sections = ("Objective", "Acceptance criteria") if minimal else TASK_REQUIRED_SECTIONS
    for name in sections:
        if not doc.has(name):
            problems.append(f'missing section "{name}"')
    if doc.has("Objective") and not doc.text("Objective"):
        problems.append('section "Objective" is empty: write what the task must achieve')
    if doc.has("Acceptance criteria") and not CRITERION_RE.search(doc.text("Acceptance criteria")):
        problems.append('section "Acceptance criteria" needs at least one "- [ ]" item')
    return problems


def context_paths(doc):
    paths = []
    for line in doc.text("Context").splitlines():
        line = line.strip()
        if line.startswith("- "):
            paths.append(line[2:].strip().strip("`"))
    return paths


def set_context_paths(doc, paths):
    doc.set_section("Context", "\n".join(f"- {p}" for p in paths) if paths else "<!-- wai context add -->")
