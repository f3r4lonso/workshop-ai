"""Project state, task contracts and checkpoints (spec sections 3, 4.1, 4.2, 9)."""

import datetime
import difflib
import os
from pathlib import Path

from . import formats
from .errors import ENVIRONMENT, REFUSED, USAGE, VALIDATION, WaiError
from .fsutil import atomic_write, git_commit_label, is_inside, read_text

STATE_DIR = ".workshop-ai"
GITIGNORE = "# Workshop AI: generated or local-only files\ntasks/*/brief.md\nhandoffs/\n.snapshots/\n"

TASK_TEMPLATE_SECTIONS = (
    ("Objective", "<!-- What must be true when this task is done? -->"),
    ("Acceptance criteria", "<!-- One '- [ ] ...' line per checkable criterion. -->\n- [ ] "),
    ("Context", "<!-- wai context add -->"),
    ("Constraints", "<!-- Optional: limits, exclusions, approvals. -->"),
    ("Decisions", "<!-- - D-001 (date): decision. Reason: ... -->"),
    ("Open questions", "<!-- Optional. -->"),
    ("Next action", "<!-- The very next step. -->"),
    ("History", "<!-- written by wai checkpoint -->"),
)

PROJECT_TEMPLATE_SECTIONS = (
    ("Objective", "<!-- What this project is for. -->"),
    ("Status", "<!-- Where the project stands. -->"),
    ("Requirements and constraints", ""),
    ("Decisions", "<!-- Cross-task decisions: - D-P001 (date): decision. Reason: ... -->"),
    ("Artifacts", ""),
    ("Open issues", ""),
    ("Last verified state", "<!-- written by wai checkpoint -->"),
    ("Next steps", ""),
)


def now():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")


def default_infra():
    env = os.environ.get("WORKSHOP_AI_INFRA")
    return Path(env) if env else Path.home() / "workshop" / "infra"


class Project:
    def __init__(self, root, infra):
        self.root = Path(root).resolve()
        self.infra = Path(infra)
        self.dir = self.root / STATE_DIR

    # paths ----------------------------------------------------------------
    @property
    def state_file(self):
        return self.dir / "project-state.md"

    def task_dir(self, task_id):
        formats.validate_task_id(task_id)
        return self.dir / "tasks" / task_id

    def task_file(self, task_id):
        return self.task_dir(task_id) / "task.md"

    def snapshot(self, rel):
        return self.dir / ".snapshots" / rel

    def rel(self, path):
        return Path(path).resolve().relative_to(self.dir).as_posix()

    # init -----------------------------------------------------------------
    def refuse_inside_infra(self):
        if self.infra.exists() and is_inside(self.root, self.infra):
            raise WaiError(
                "this folder is inside the shared infrastructure repository, which is public: project state "
                "never goes there. Run wai init in a project repository instead.",
                REFUSED,
            )

    def init(self, name=None):
        self.refuse_inside_infra()
        if self.state_file.exists():
            return False
        (self.dir / "tasks").mkdir(parents=True, exist_ok=True)
        atomic_write(self.dir / ".gitignore", GITIGNORE)
        doc = formats.Doc(
            {"project": name or self.root.name, "revision": "0", "updated": now()}, "\n",
            [[t, b + "\n\n"] for t, b in PROJECT_TEMPLATE_SECTIONS],
        )
        atomic_write(self.state_file, doc.dumps())
        self.save_snapshot(self.rel(self.state_file), read_text(self.state_file))
        return True

    def require_init(self):
        self.refuse_inside_infra()
        if not self.state_file.exists():
            raise WaiError(
                f"no Workshop AI project in {self.root}: run wai init here first (or pass --project)",
                ENVIRONMENT,
            )

    # tasks ----------------------------------------------------------------
    def task_ids(self):
        folder = self.dir / "tasks"
        return sorted(p.parent.name for p in folder.glob("*/task.md")) if folder.exists() else []

    def new_task(self, task_id, client):
        self.require_init()
        if client not in formats.CLIENTS:
            raise WaiError(f"unknown client {client!r}: use one of {', '.join(formats.CLIENTS)}")
        path = self.task_file(task_id)
        if path.exists():
            raise WaiError(f"task {task_id} already exists: {self.rel(path)}", REFUSED)
        header = {"id": task_id, "client": client, "status": "draft", "created": now(), "revision": "0"}
        doc = formats.Doc(header, "\n", [[t, b + "\n\n"] for t, b in TASK_TEMPLATE_SECTIONS])
        atomic_write(path, doc.dumps())
        return path

    def load_task(self, task_id):
        self.require_init()
        path = self.task_file(task_id)
        if not path.exists():
            raise WaiError(f"task {task_id} not found: create it with wai task new {task_id} --client claude")
        return formats.parse(read_text(path), f".workshop-ai/tasks/{task_id}/task.md")

    def save_task(self, task_id, doc):
        atomic_write(self.task_file(task_id), doc.dumps())

    def check_task(self, task_id, doc, minimal=False):
        problems = formats.task_problems(doc, minimal=minimal)
        if doc.header.get("id") and doc.header["id"] != task_id:
            problems.append(f'header id "{doc.header["id"]}" does not match the folder name "{task_id}"')
        if problems:
            lines = "\n  - ".join(problems)
            raise WaiError(
                f".workshop-ai/tasks/{task_id}/task.md is not valid:\n  - {lines}\n"
                "Fix the file, then run the command again.",
                VALIDATION,
            )

    # context --------------------------------------------------------------
    def resolve_context(self, raw):
        """Validate one context path; return it relative to the project root (posix form)."""
        from .scan import forbidden_reason
        candidate = (self.root / raw) if not Path(raw).is_absolute() else Path(raw)
        if not is_inside(candidate, self.root):
            raise WaiError(f"{raw}: outside the project folder; only project files can be context", REFUSED)
        resolved = candidate.resolve()
        if not resolved.is_file():
            raise WaiError(f"{raw}: not a file (folders are not accepted; add files one by one)")
        rel = resolved.relative_to(self.root).as_posix()
        reason = forbidden_reason(rel)
        if reason:
            raise WaiError(f"{rel}: {reason}", REFUSED)
        return rel

    # snapshots and diffs --------------------------------------------------
    def snapshot_text(self, rel):
        path = self.snapshot(rel)
        return read_text(path) if path.exists() else ""

    def save_snapshot(self, rel, text):
        atomic_write(self.snapshot(rel), text)

    def diff_since_checkpoint(self, path):
        rel = self.rel(path)
        old = self.snapshot_text(rel)
        new = read_text(path) if Path(path).exists() else ""
        if old == new:
            return ""
        return "".join(difflib.unified_diff(
            old.splitlines(True), new.splitlines(True),
            fromfile=f"{rel} (last checkpoint)", tofile=f"{rel} (now)",
        ))

    # checkpoint -----------------------------------------------------------
    def changed_protected_keys(self, task_id, doc):
        old_text = self.snapshot_text(self.rel(self.task_file(task_id)))
        if not old_text:
            return []
        old = formats.parse(old_text, "snapshot")
        keys = set(old.header) | set(doc.header)
        return sorted(k for k in keys if k not in ("status", "revision")
                      and old.header.get(k) != doc.header.get(k))

    def previous_verify(self, task_id):
        old_text = self.snapshot_text(self.rel(self.task_file(task_id)))
        return formats.parse(old_text, "snapshot").header.get("verify") if old_text else None

    def record_checkpoint(self, task_id, doc, verify_result):
        revision = int(doc.header.get("revision", "0")) + 1
        stamp = now()
        commit = git_commit_label(self.root)
        doc.header["revision"] = str(revision)
        history = doc.text("History")
        line = f"- rev {revision}, {stamp}, commit {commit}, verify: {verify_result}, confirmed by user"
        doc.set_section("History", (history + "\n" if history else "") + line)
        self.save_task(task_id, doc)
        self.save_snapshot(self.rel(self.task_file(task_id)), read_text(self.task_file(task_id)))

        state = formats.parse(read_text(self.state_file), ".workshop-ai/project-state.md")
        entries = [l for l in state.text("Last verified state").splitlines()
                   if l.strip().startswith("- ") and not l.strip().startswith(f"- {task_id}:")]
        entries.append(f"- {task_id}: rev {revision}, {doc.header.get('status')}, {stamp}, commit {commit}")
        state.set_section("Last verified state", "\n".join(sorted(entries)))
        state.header["revision"] = str(int(state.header.get("revision", "0") or 0) + 1)
        state.header["updated"] = stamp
        atomic_write(self.state_file, state.dumps())
        self.save_snapshot(self.rel(self.state_file), read_text(self.state_file))
        return revision, commit

    def checkpointed_clean(self, task_id):
        """True if the task file is unchanged since its last checkpoint."""
        rel = self.rel(self.task_file(task_id))
        snap = self.snapshot_text(rel)
        return bool(snap) and snap == read_text(self.task_file(task_id))
