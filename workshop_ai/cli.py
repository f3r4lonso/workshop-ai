"""`wai` command line (spec section 2)."""

import argparse
import os
import subprocess
import sys
import traceback
from pathlib import Path

from . import __version__, approval, clients, formats, handoff, resources, scan
from .errors import OK, REFUSED, VALIDATION, WaiError
from .fsutil import atomic_write, read_text
from .state import Project, default_infra


def out(text=""):
    print(text)


def project_from(args):
    return Project(args.project or os.getcwd(), args.infra or default_infra())


# init / resources / status ------------------------------------------------
def cmd_init(args):
    project = project_from(args)
    if project.init(args.name):
        out(f"Initialized Workshop AI in {project.dir.name}/ (project-state.md, tasks/, .gitignore).")
        out("Next: wai task new <task-id> --client claude")
    else:
        out("Already initialized; nothing changed.")
    return OK


def cmd_resources(args):
    kinds = [args.kind] if args.kind else list(resources.KINDS)
    listed = resources.list_resources(Path(args.infra or default_infra()), kinds)
    for kind in kinds:
        rows, warnings = listed[kind]
        out(f"{kind} ({len(rows)})")
        for row in rows:
            if kind == "clients":
                out(f"  {row['id']:<18} {row['title']}")
            elif kind == "agents":
                out(f"  {row['area']}/{row['name']:<30} {row['description']}")
            elif kind == "skills":
                out(f"  {row['name']:<30} {row['description']}")
            else:
                out(f"  {row['file']:<55} {row['status']}")
        for warning in warnings:
            out(f"  warning: {warning}")
    return OK


def cmd_status(args):
    project = project_from(args)
    project.require_init()
    ids = project.task_ids()
    if not ids:
        out("No tasks yet. Create one with wai task new <task-id> --client claude")
        return OK
    for task_id in ids:
        try:
            doc = project.load_task(task_id)
        except WaiError as exc:
            out(f"{task_id:<24} unreadable: {exc}")
            continue
        history = [l for l in doc.text("History").splitlines() if l.startswith("- rev")]
        last = history[-1][2:].split(", commit")[0] if history else "no checkpoint"
        nxt = " ".join(doc.text("Next action").split())[:60] or "-"
        out(f"{task_id:<24} {doc.header.get('client', '?'):<7} {doc.header.get('status', '?'):<12} {last:<24} next: {nxt}")
    return OK


# tasks and context ---------------------------------------------------------
def cmd_task_new(args):
    project = project_from(args)
    path = project.new_task(args.task_id, args.client)
    out(f"Created .workshop-ai/tasks/{args.task_id}/task.md (status: draft, client: {args.client}).")
    if not args.no_edit and sys.stdin.isatty() and sys.stdout.isatty():
        editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "vi")
        out(f"Opening it in {editor}: fill in Objective and Acceptance criteria, save, close.")
        subprocess.run(f'{editor} "{path}"', shell=True)
    else:
        out("Edit it now: fill in Objective and Acceptance criteria.")
    out(f"Next: wai context add {args.task_id} <file>...  then  wai start {args.task_id}")
    return OK


def cmd_context(args):
    project = project_from(args)
    doc = project.load_task(args.task_id)
    current = formats.context_paths(doc)
    if args.action == "add":
        if not args.paths:
            raise WaiError("give at least one file: wai context add <task-id> <file>...")
        for raw in args.paths:
            rel = project.resolve_context(raw)
            if rel not in current:
                current.append(rel)
        formats.set_context_paths(doc, current)
        project.save_task(args.task_id, doc)
    elif args.action == "remove":
        targets = {Path(p).as_posix() for p in args.paths}
        current = [p for p in current if p not in targets]
        formats.set_context_paths(doc, current)
        project.save_task(args.task_id, doc)
    out(f"Context for {args.task_id} ({len(current)} file(s)):")
    for p in current:
        out(f"  - {p}")
    return OK


# start / resume -------------------------------------------------------------
def start_session(args, resume):
    project = project_from(args)
    doc = project.load_task(args.task_id)
    project.check_task(args.task_id, doc, minimal=True)
    context = [project.resolve_context(p) for p in formats.context_paths(doc)]
    client = doc.header["client"]
    message = clients.FIRST_MESSAGE.format(task_id=args.task_id)
    command = clients.start_command(client, project.infra, message)

    brief_path = project.task_dir(args.task_id) / "brief.md"
    brief = clients.build_brief(args.task_id, read_text(project.task_file(args.task_id)), context, resume)
    blocks, warnings = scan.scan_text(brief, "brief.md")
    if blocks:
        raise WaiError("the brief contains secret-like text, nothing started:\n  - " + "\n  - ".join(blocks)
                       + "\nRemove it from task.md or the context, then try again.", VALIDATION)
    atomic_write(brief_path, brief)

    out(f"{'Resume' if resume else 'Start'} task {args.task_id}")
    out(f"  client:  {client} (interactive session)")
    out(f"  folder:  {project.root}")
    out(f"  command: {subprocess.list2cmdline(command)}")
    out(f"  context: {', '.join(context) if context else '(none)'}")
    for w in warnings:
        out(f"  warning: {w}")
    if not approval.confirm("Start this session?"):
        out("Not started.")
        return REFUSED
    subprocess.run(command, cwd=project.root)
    out(f"Session ended. Save the verified state with: wai checkpoint {args.task_id}")
    return OK


def cmd_start(args):
    return start_session(args, resume=False)


def cmd_resume(args):
    return start_session(args, resume=True)


# checkpoint -------------------------------------------------------------------
def cmd_checkpoint(args):
    project = project_from(args)
    doc = project.load_task(args.task_id)
    project.check_task(args.task_id, doc)

    blocks, warnings = [], []
    task_path = project.task_file(args.task_id)
    for path in (task_path, task_path.parent / "brief.md", project.state_file):
        if path.exists():
            b, w = scan.scan_text(read_text(path), project.rel(path))
            blocks += b
            warnings += w
    if blocks:
        raise WaiError("secret-like text found, checkpoint not saved:\n  - " + "\n  - ".join(blocks)
                       + "\nRemove it, then run wai checkpoint again.", VALIDATION)

    verify_result = "not set"
    command = doc.header.get("verify")
    if command:
        previous = project.previous_verify(args.task_id)
        changed = previous is not None and previous != command
        out(f"Verify command{' (CHANGED since the last checkpoint, was: ' + previous + ')' if changed else ''}:")
        out(f"  {command}")
        if approval.confirm("Run it in the project folder?"):
            result = subprocess.run(command, shell=True, cwd=project.root)
            verify_result = "pass" if result.returncode == 0 else f"fail (exit {result.returncode})"
        else:
            verify_result = "not run"
        out(f"Verify: {verify_result}")

    changed_keys = project.changed_protected_keys(args.task_id, doc)
    task_diff = project.diff_since_checkpoint(task_path)
    state_diff = project.diff_since_checkpoint(project.state_file)
    out(task_diff or f"task.md: no change since the last checkpoint.")
    if state_diff:
        out("project-state.md was edited since the last checkpoint; these edits are kept:")
        out(state_diff)
    for key in changed_keys:
        out(f"WARNING: header key '{key}' changed since the last checkpoint (only 'status' should change).")
    for w in warnings:
        out(f"warning: {w}")
    if not approval.confirm("Save this as the verified state?"):
        out("Checkpoint not saved; files left as they are.")
        return REFUSED
    revision, commit = project.record_checkpoint(args.task_id, doc, verify_result)
    out(f"Checkpoint saved: {args.task_id} rev {revision}, commit {commit}, verify {verify_result}.")
    return OK


# handoff ---------------------------------------------------------------------
def print_manifest(manifest):
    out(f"Package {manifest['package']}: task {manifest['task']} rev {manifest['task_revision']}, "
        f"{manifest['from_client']} → {manifest['to_client']}")
    for f in manifest["files"]:
        out(f"  {f['bytes']:>8} B  {f['path']}")
    s = manifest["scan"]
    out(f"  scan: built-in {s['builtin']}, gitleaks {s['gitleaks']}")
    for b in s.get("blocks", []):
        out(f"  BLOCK: {b}")
    for w in s.get("warnings", []):
        out(f"  warning: {w}")
    out(f"  approval: {manifest['approval']['status']}")


def cmd_handoff_create(args):
    project = project_from(args)
    package, manifest = handoff.create(project, args.task_id, args.to)
    print_manifest(manifest)
    if manifest["approval"]["status"] == "blocked":
        out("Blocked: fix the findings (remove the file from the context or the text from task.md), "
            "checkpoint, and create a new package.")
        return VALIDATION
    out(f"Next: review .workshop-ai/handoffs/{package}/, then run wai handoff approve {package}")
    return OK


def cmd_handoff_approve(args):
    project = project_from(args)
    folder, manifest = handoff.load(project, args.package)
    status = manifest.get("approval", {}).get("status")
    if status == "blocked":
        raise WaiError(f"package {args.package} is blocked by the scan and cannot be approved", VALIDATION)
    if status == "approved":
        out(f"Package {args.package} is already approved.")
        return OK
    handoff.require_intact(folder, manifest)
    print_manifest(manifest)
    out(f"Review the files in .workshop-ai/handoffs/{args.package}/ before approving.")
    manual = manifest["scan"]["gitleaks"] != "pass"
    if manual:
        out(f"gitleaks result: {manifest['scan']['gitleaks']}. A manual review is required: open every file "
            "listed above and check it holds no secrets, credentials or private data.")
        if not approval.confirm_typed("Have you reviewed every file?", "reviewed"):
            out("Not approved.")
            return REFUSED
    if not approval.confirm(f"Release this package to {manifest['to_client']}?"):
        out("Not approved.")
        return REFUSED
    manifest["approval"] = {"status": "approved", "date": handoff.now(), "manual_review": manual}
    handoff.write_manifest(folder, manifest)
    out(f"Approved. Next: wai handoff show {args.package}")
    return OK


def cmd_handoff_show(args):
    project = project_from(args)
    folder, manifest = handoff.load(project, args.package)
    handoff.require_approved(manifest)
    handoff.require_intact(folder, manifest)
    for line in clients.handoff_steps(manifest["to_client"], project.infra, project.root, args.package):
        out(line)
    return OK


# parser ----------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(prog="wai", description="Workshop AI, Stage 1: single-client tasks with "
                                     "saved state and manual handoff.")
    parser.add_argument("--version", action="version", version=f"wai {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", help="project folder (default: current folder)")
    common.add_argument("--infra", help="shared infrastructure folder (default: WORKSHOP_AI_INFRA or ~/workshop/infra)")
    common.add_argument("--debug", action="store_true", help="show tracebacks")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", parents=[common], help="set up .workshop-ai/ in a project")
    p.add_argument("--name", help="project name (default: folder name)")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("resources", parents=[common], help="list shared clients, agents, skills, tasks")
    p.add_argument("kind", nargs="?", choices=resources.KINDS)
    p.set_defaults(func=cmd_resources)

    p = sub.add_parser("status", parents=[common], help="one line per task")
    p.set_defaults(func=cmd_status)

    task = sub.add_parser("task", help="task contracts").add_subparsers(dest="task_command", required=True)
    p = task.add_parser("new", parents=[common], help="create a task and choose its client")
    p.add_argument("task_id")
    p.add_argument("--client", required=True, choices=formats.CLIENTS)
    p.add_argument("--no-edit", action="store_true", help="do not open an editor")
    p.set_defaults(func=cmd_task_new)

    p = sub.add_parser("context", parents=[common], help="select the files a task may use")
    p.add_argument("action", choices=("add", "remove", "list"))
    p.add_argument("task_id")
    p.add_argument("paths", nargs="*")
    p.set_defaults(func=cmd_context)

    for name, func, text in (("start", cmd_start, "start an interactive session for a task"),
                             ("resume", cmd_resume, "resume a task in a new session from its saved state"),
                             ("checkpoint", cmd_checkpoint, "save the verified state of a task")):
        p = sub.add_parser(name, parents=[common], help=text)
        p.add_argument("task_id")
        p.set_defaults(func=func)

    ho = sub.add_parser("handoff", help="manual handoff packages").add_subparsers(dest="handoff_command",
                                                                                 required=True)
    p = ho.add_parser("create", parents=[common], help="build a package from the last checkpoint")
    p.add_argument("task_id")
    p.add_argument("--to", required=True, choices=formats.CLIENTS)
    p.set_defaults(func=cmd_handoff_create)
    for name, func, text in (("approve", cmd_handoff_approve, "review and release a package"),
                             ("show", cmd_handoff_show, "print the steps for the receiving client")):
        p = ho.add_parser(name, parents=[common], help=text)
        p.add_argument("package")
        p.set_defaults(func=func)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except WaiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except KeyboardInterrupt:
        print("interrupted; files left as they were", file=sys.stderr)
        return REFUSED
    except Exception as exc:  # unexpected: keep state, explain, offer --debug
        if getattr(args, "debug", False):
            traceback.print_exc()
        else:
            print(f"error: unexpected {type(exc).__name__}: {exc} (run again with --debug for details)",
                  file=sys.stderr)
        return 1
