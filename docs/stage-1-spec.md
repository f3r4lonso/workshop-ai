# Workshop AI — Stage 1 specification

Status: approved at Gate B (2026-10-17); updated during the build (2026-10-18: worktrees per pilot run, ignored results folder, Codex read-only check, snapshots instead of an index file).
Note (2026-10-18): the VS Code extension that follows Stage 1 is specified in [vscode-extension-spec.md](vscode-extension-spec.md); this Stage 1 content is unchanged.
Implements the P0 set of the product vision v1.1 (infra `docs/workshop-ai-product-vision.md`, §10) under its decisions (§17). Requirement ids (FR-xx, NFR-xx) refer to the vision.

Labels: **Proposed** unless stated. "Infra" = the shared infrastructure repository (default
`%USERPROFILE%\workshop\infra`).

## 1. Scope

In: one user, one machine, Windows first (PowerShell), Claude Code as the executing client, Codex CLI as a manual
handoff target. Python 3 standard library only. No network access, no background process, no git writes, no
installs, no non-interactive client runs (vision §17.2).

Out: automated handoff, parallel runs, routing, UI, run log (FR-10), Stage 2+ features.

## 2. User journey

| Step | Command | Result | FR |
|---|---|---|---|
| 0. Set up a project once | `wai init` (in the project root) | `.workshop-ai/` with `project-state.md`, `tasks/`, `.gitignore` | FR-06 |
| 1. See what is available | `wai resources [clients\|agents\|skills\|tasks]` | lists read from the infra contracts | FR-01/04 (read only) |
| 2. Create a task and choose a client | `wai task new <task-id> --client claude` | task contract file with `status: draft`, opened in `$env:EDITOR` (else Notepad); `wai start` exits 2 until objective and at least one acceptance criterion are filled | FR-02, FR-03 |
| 3. Attach context | `wai context add <task-id> <path>...` / `wai context list <task-id>` | paths recorded in the contract; only paths inside the project | FR-07 |
| 4. Run it | `wai start <task-id>` | shows client, folder, flags, context → **approval A1** → starts an interactive Claude Code session with a short first message pointing at the task brief | FR-02, FR-08 |
| 5. Save verified state | `wai checkpoint <task-id>` | validates the contract, shows what changed since the last checkpoint, optionally runs the task's `verify` command (**approval A1**), asks the user to confirm (**A3**), records revision, time and project commit | FR-06, NFR-01 |
| 6. Resume later | `wai resume <task-id>` | same as `start`, but the brief tells the new session to rely only on the contract and project state | FR-06 |
| 7. Hand off manually | `wai handoff create <task-id> --to codex` → `wai handoff approve <pkg-id>` → `wai handoff show <pkg-id>` | package folder; secret check; **approval A2**; printed steps for the target client | FR-05, FR-08, FR-09 |
| — | `wai status` | one line per task: id, client, status, last checkpoint, next action | FR-14 (partial) |

Command name: `wai` = `python -m workshop_ai` (a `wai.cmd` one-liner in the repository root). Global options:
`--project <dir>` (default: current folder), `--infra <dir>` (else env `WORKSHOP_AI_INFRA`, else the default above),
`--debug` (show tracebacks).

## 3. Storage layout (vision §13, §17.4)

```text
<project>/.workshop-ai/
├── project-state.md          versioned in the project repo
├── tasks/<task-id>/
│   ├── task.md               task contract (versioned)
│   └── brief.md              generated on start/resume (ignored)
├── handoffs/<pkg-id>/        handoff packages (ignored by default)
├── .snapshots/               copies of task.md and project-state.md at their last checkpoint (ignored)
└── .gitignore                ignores brief.md, handoffs/, .snapshots/
```

Nothing is written to the infra repository. The tool refuses to `init` inside the infra repository or any folder
whose git root is the infra repository (exit 3).

## 4. Formats

All files are UTF-8 Markdown with a header block of `key: value` lines between `---` lines, then fixed `## `
sections. The tool rewrites only the header and the sections it owns; free text inside sections is preserved.
Unknown sections are kept.

### 4.1 Task contract — `tasks/<task-id>/task.md` (FR-03)

Required header keys: `id`, `client` (`claude` | `codex`), `status` (`draft` | `ready` | `in-progress` |
`blocked` | `done`), `created`, `revision`. Optional: `verify` (a local command), `owner`.
Required sections: `Objective`, `Acceptance criteria` (at least one `- [ ]` item), `Next action`.
Optional sections: `Context` (owned by `wai context`), `Constraints`, `Decisions`, `Open questions`,
`Artifacts`, `History` (owned by `wai checkpoint`).

```markdown
---
id: t2-empty-csv
client: claude
status: in-progress
created: 2026-10-20T10:02
revision: 2
verify: python -m unittest
---

## Objective
`csvsummary` must report "no data rows" instead of crashing on a CSV with only a header.

## Acceptance criteria
- [x] A regression test reproduces the crash before the fix.
- [ ] `python -m unittest` passes.

## Context
- csvsummary/stats.py
- tests/test_stats.py

## Constraints
- Do not change the output format for non-empty files.

## Decisions
- D-001 (2026-10-20, rev 2): exit code 0 with a message, not an error. Reason: an empty export is a normal case.

## Open questions
- none

## Next action
Implement the fix in `stats.summarize`; then run the tests.

## History
- rev 1, 2026-10-20T10:05, commit 3f2a1c0, verify: not run, confirmed by user
- rev 2, 2026-10-20T10:41, commit 3f2a1c0+dirty, verify: fail (1 test), confirmed by user
```

### 4.2 Project state — `project-state.md` (FR-06)

Header keys: `project`, `revision`, `updated`. Sections: `Objective`, `Status`, `Requirements and constraints`,
`Decisions` (project-level, `D-P001 …`), `Artifacts`, `Open issues`, `Last verified state` (owned by the tool:
latest checkpoint per task), `Next steps`.

```markdown
---
project: workshop-ai-sandbox
revision: 4
updated: 2026-10-20T10:41
---

## Objective
Small CSV summary CLI used to pilot Workshop AI.

## Status
Pilot in progress: T1 done, T2 in progress.

## Requirements and constraints
- Python standard library only.

## Decisions
- D-P001 (2026-10-20): every task records its decisions in its own task file; this file keeps only cross-task ones.

## Artifacts
- pilot/results.md

## Open issues
- none

## Last verified state
- t1-column-option: rev 3, done, 2026-10-20T09:50, commit 9b1e004
- t2-empty-csv: rev 2, in-progress, 2026-10-20T10:41, commit 3f2a1c0+dirty

## Next steps
- Finish T2, then run T3 across two sessions.
```

### 4.3 Handoff package — `handoffs/<pkg-id>/` (FR-05, FR-09)

`<pkg-id>` = `<task-id>-<n>`. Contents:

- `handoff.md`: the brief for the receiving client: objective, acceptance criteria, constraints, decisions, open
  questions, next action, and the list of context files — copied from the task contract at its last checkpoint.
  It must not contain transcript text.
- `context/`: copies of the selected context files, same relative paths.
- `manifest.json`:

```json
{
  "package": "t3-validation-1",
  "task": "t3-validation",
  "task_revision": 3,
  "from_client": "claude",
  "to_client": "codex",
  "created": "2026-10-21T16:10",
  "files": [
    {"path": "handoff.md", "sha256": "…", "bytes": 1840},
    {"path": "context/csvsummary/reader.py", "sha256": "…", "bytes": 2210}
  ],
  "scan": {"builtin": "pass", "gitleaks": "not installed", "user_paths": 0, "date": "2026-10-21T16:10"},
  "approval": {"status": "approved", "date": "2026-10-21T16:12"}
}
```

`approval.status` is `pending` until A2. `wai handoff approve` refuses a package whose files no longer match the
manifest hashes (changed after the scan) or whose scan failed.

## 5. Resource listing (vision FR-01, FR-04; infra `docs/ai-architecture.md` §9)

Read-only parsing of the infra contracts, nothing copied:

| List | Source | Shown |
|---|---|---|
| clients | `clients/<client-id>/README.md` folders | id, title line |
| agents | frontmatter of `agents/<area>/<name>.md` | area, name, description (first sentence), tools |
| skills | frontmatter of `skills/<name>/SKILL.md` | name, description (first sentence) |
| tasks | `tasks/*.md` except `README.md` | file, title, `Status:` line |

Missing or malformed entries are listed as warnings; the command still succeeds (exit 0) if at least one list was
read. Evidence labels per client are not parsed in Stage 1 (FR-01 is P1).

## 6. Starting a client (infra `docs/projects/README.md` step 4)

| Client | What `wai start`/`resume` does | Status |
|---|---|---|
| claude | runs `claude --add-dir "<infra>\clients" "<first message>"` in the project folder, attached to the user's terminal | `claude "<query>"` starts an interactive session with a first message (Documented, to be Observed in Phase 5) |
| codex | handoff target only: `wai handoff show` prints the steps (once per machine: `python <infra>\scripts\codex-adapter.py link-skills --user`; then start `codex` in the project folder and paste *"Read `.workshop-ai/handoffs/<pkg-id>/handoff.md` and continue the task."*); the tool never launches Codex | Not run unless Gate C is approved |

First message (identical for both): *"Read `.workshop-ai/tasks/<task-id>/brief.md` and follow it."*
The brief contains: the task contract; the context paths to read (and only those); the instruction to keep the
`Decisions`, `Open questions`, `Next action` and `status` up to date in `task.md` before stopping; the reminder that
`wai checkpoint` (run by the user) saves the verified state; and, for `resume`, the instruction to rely on the task
file and `project-state.md` only and to report any conflict with current files.

The tool checks that the client is on PATH (exit 4 otherwise) and never passes permission-widening flags.

## 7. Approval points (FR-08)

| Id | When | Shown before asking | Default |
|---|---|---|---|
| A1 | before starting a client, before running a `verify` command | client, folder, full command line, context list | No |
| A2 | before releasing a handoff package | manifest summary, file list with sizes, scan results | No |
| A3 | before saving a checkpoint, and before overwriting any state file changed outside the tool since the last checkpoint | unified diff since the last checkpoint | No |

Approval is an interactive `y/N` prompt. Every prompt requires **both stdin and stdout to be a terminal**; otherwise
the command refuses with exit 3 and "approval requires an interactive terminal". There is no flag that skips any
approval. This stops an AI session (whose shell tool has no terminal) or a pipe (`echo y | …`) from approving its own
actions. Tests replace the prompt function instead of using a flag.

A1 for a `verify` command shows the command and, if it changed since the last checkpoint, marks it
**CHANGED since rev n**. The brief tells the session not to edit header keys other than `status`; a change to any
other header key is shown at A3.

## 8. Redaction checks (FR-09)

Run by `wai handoff create` on every file of the package; any **block** stops the package (status `blocked`, exit 2):

1. **Location:** every context path must resolve inside the project root (no `..`, no links pointing out) — block.
2. **Forbidden names:** `.env*` (except `.env.example`), `auth.json`, `.credentials.json`, `credentials*.json`,
   `settings.local.json`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `.netrc`, `.npmrc`,
   `.pypirc` — block.
3. **Secret patterns (built-in):** private-key headers; `AKIA[0-9A-Z]{16}`; `sk-ant-…`; `sk-…` (OpenAI);
   `gh[pousr]_…`; `xox[baprs]-…`; generic assignments `(api[_-]?key|secret|token|password)\s*[:=]\s*\S{12,}` — block.
4. **Gitleaks:** if `gitleaks` is on PATH, `gitleaks dir <package> --config <infra>\.gitleaks.toml` — finding =
   block. If not installed, A2 additionally asks the user to type `reviewed` after reading the listed files, and the
   manifest records `"gitleaks": "not installed", "manual_review": true`.
5. **Personal paths:** case-insensitive `[a-z]:[\\/]users[\\/][^\\/]+`, `/Users/[^/]+`, `/home/[^/]+` — warn,
   shown at A2.

The built-in checks 2, 3 and 5 also run at every checkpoint on `task.md`, `brief.md` and `project-state.md`
(vision FR-09); a block there stops the checkpoint (exit 2).

**Ids and paths:** task and package ids must match `^[a-z0-9][a-z0-9-]{0,63}$` (exit 1 otherwise). `wai context add`
accepts files only, not folders; paths under `.git/`, `.ssh/` or `.workshop-ai/`, and `*.kdbx`, are refused.
6. **Size:** package over 256 KB — warn, shown at A2 (selected context should be small).

Matched values are never printed: only file, line and rule.

## 9. Error behaviour (NFR-01)

- Writes are atomic (temporary file in the same folder, then replace). A failed write leaves the previous file.
- Every write is read-modify-write of the current file, so hand edits are kept. At each checkpoint the tool shows
  the diff of `task.md` and of `project-state.md` against their snapshots (`.snapshots/`) and asks (A3); it never
  discards hand edits silently. Without a snapshot (fresh clone) the whole file is shown as new.
- The tool never deletes user files. `handoff create` never overwrites an existing package; it takes the next `<n>`.
- Exit codes: `0` ok; `1` usage error or not found; `2` validation failed (format, scan block, hash mismatch);
  `3` refused (approval declined, conflict, forbidden location); `4` environment (client or infra not found,
  project not initialized).
- Every error message states what failed and the next action, e.g.
  `task.md: missing section "Acceptance criteria" — add at least one "- [ ]" item, then run wai checkpoint again.`
- No traceback unless `--debug`.

## 10. Tests (Phase 5 step 1)

`python -m unittest` in the tool repository, standard library only, using temporary folders and a fake infra tree:
format round-trips (unknown sections and free text preserved), validation messages, context path escapes,
forbidden names, each secret pattern (with synthetic test strings only), manifest hash mismatch, approval refusal
without a terminal, atomic write on simulated failure, hand-edit detection, refusal to init inside infra, resource
listing on a fake infra tree, exit codes.

## 11. Sandbox project and pilot

Repository `%USERPROFILE%\workshop\applications\workshop-ai-sandbox\` (separate git repo, private, not pushed):
`csvsummary`, a small Python standard-library CLI that prints count, mean and median per numeric column of a CSV,
with a few unit tests and a sample file. It ships with one seeded defect (a header-only CSV crashes). Tag
`pilot-base` marks the starting commit.

### 11.1 Pilot tasks (acceptance criteria fixed before any run)

| Task | Kind | Acceptance criteria |
|---|---|---|
| T1 `t1-column-option` | small feature | (a) `--column <name>` prints stats for that column only; (b) an unknown column gives a clear message and exit code 2; (c) new tests cover (a) and (b); (d) `python -m unittest` passes; (e) README documents the option; (f) no files changed outside `csvsummary/`, `tests/`, `README.md` |
| T2 `t2-empty-csv` | bug fix | (a) a regression test fails on `pilot-base` and passes after the fix; (b) a header-only CSV prints "no data rows" with exit code 0; (c) output for non-empty files unchanged (existing tests untouched and passing) |
| T3 `t3-validation` | two sessions plus handoff | session 1 only designs: it records at least two decisions (error message format, behaviour on a malformed row) and stops. Session 2 starts fresh from the **handoff package**, in Claude Code (same client as the baseline, so the two T3 runs compare the tool, not the client). (a) session 2, given only `handoffs/<pkg-id>/handoff.md`, states the recorded decisions and next step correctly before coding; (b) the implementation follows them; (c) tests for a malformed row pass and `python -m unittest` passes; (d) the package was scanned clean and approved, and contains only `handoff.md`, `manifest.json` and the selected files under `context/` |

### 11.2 Design

Each task runs twice from `pilot-base`, each run in its own git worktree
(`git worktree add --detach ..\workshop-ai-sandbox-runs\<run> pilot-base`: a separate folder, no extra commits, kept
until checked): **baseline** (plain `claude --add-dir …` session, the
user pastes the objective and criteria) and **with tool** (`wai` journey). Order alternates to spread learning
effects: T1 baseline first, T2 tool first, T3 baseline first. In the T3 baseline, session 2 receives whatever the
user chooses to paste from session 1. A run is **done** when every acceptance criterion is ticked or the user stops
it. Recorded per run in `pilot-results/results.md` in the main sandbox folder (gitignored, so it is not affected by
the worktrees; whether to commit it is decided at Gate D): criteria pass/fail per item,
wall-clock start and accepted-result times, user interventions (messages typed after the first one), and the
`/context` and `/cost` output at the end of each session (N/A where not shown). Limitations stated up front: n = 3
tasks × 2, one user, not blinded, same person knows both variants.

**Codex check (Gate C approved):** after the T2 "with tool" run, Codex CLI is started read-only
(`codex --sandbox read-only`) in that run's folder and given only the approved T2 handoff package. Pass = it states
the recorded decisions and next step correctly. It is a continuity check, not a pilot run.

### 11.3 Phase 5 user script (summary; full text in `pilot/user-script.md` in the sandbox)

PowerShell, in a normal terminal (not inside an AI session):

0. Once per terminal: `Set-Alias wai "$env:USERPROFILE\workshop\applications\workshop-ai\wai.cmd"`.
1. `cd "$env:USERPROFILE\workshop\applications\workshop-ai-sandbox"` →
   `git worktree add --detach ..\workshop-ai-sandbox-runs\t2-tool pilot-base` →
   `cd ..\workshop-ai-sandbox-runs\t2-tool`.
2. `wai init` → `wai resources agents` (check the list appears).
3. `wai task new t2-empty-csv --client claude` → in the editor, paste objective and criteria from `pilot/tasks.md`
   → save and close.
4. `wai context add t2-empty-csv csvsummary/stats.py tests/test_stats.py`.
5. Write the start time in a note. `wai start t2-empty-csv` → `y` → work in the session until every criterion is
   ticked → write the accepted-result time and the number of messages you typed after the first → in the session run
   `/context` and `/cost` and copy both outputs into the note → `/exit`.
6. `wai checkpoint t2-empty-csv` → `y` for the verify command → review the diff → `y`.
7. Resume test: `wai resume t2-empty-csv` → `y` → ask "What decisions are recorded for this task?" → copy the
   answer into the note → `/exit`.
8. `wai handoff create t2-empty-csv --to codex` → `wai handoff approve t2-empty-csv-1` (type `reviewed` if asked)
   → `wai handoff show t2-empty-csv-1`.
9. Paste the note into the T2 "with tool" row of `..\..\workshop-ai-sandbox\pilot-results\results.md`.
10. Tell the agent you are done; the agent checks the files (Phase 5 verification).

The baseline runs and T1/T3 follow the same pattern; the full script lists every command.

## 12. Files to create (Gate B list)

Tool repository `%USERPROFILE%\workshop\applications\workshop-ai\` (`git init`, uncommitted):
`.gitignore`, `README.md`, `AGENTS.md`, `CLAUDE.md` (`@AGENTS.md` + Claude notes), `wai.cmd`,
`docs/stage-1-spec.md` (this file), `workshop_ai/{__init__,__main__,cli,errors,approval,formats,state,resources,clients,handoff,scan,fsutil}.py`,
`tests/helpers.py`, `tests/test_{formats,state,resources,handoff,scan,cli}.py` (client start is tested in
`test_cli.py`).

Both project repositories are local and private; neither gets a remote in this task.

**Gate B note (commit exception):** the pilot needs one fixed starting point. Requested at Gate B: one local commit
of the sandbox's initial files plus the tag `pilot-base`, in the sandbox only, never pushed. If declined, the
starting point is a zip copy of the sandbox folder outside all repositories, restored before each run, and the pilot
branches are replaced by restores.

Sandbox repository `%USERPROFILE%\workshop\applications\workshop-ai-sandbox\` (`git init`; commit exception above):
`.gitignore`, `README.md`, `AGENTS.md`, `CLAUDE.md`, `csvsummary/{__init__,__main__,stats}.py`,
`tests/test_stats.py`, `data/sample.csv`, `pilot/{tasks,user-script}.md`; plus the ignored
`pilot-results/results.md` (template, not committed).

Infrastructure repository (uncommitted):
- new `docs/projects/workshop-ai/README.md` (entry page, covers the sandbox too) and a row in
  `docs/projects/README.md`;
- `tasks/README.md` §2: `workshop/tasks/<file>.md` → `tasks/<file>.md`;
- `docs/ai-infrastructure-handover.md`: dated note on the `workshop/infra` paths (record not rewritten);
- `docs/ai-architecture.md` §10: replace "old copy … left untouched" with "no longer exists (checked
  2026-10-17)"; Codex row: "Codex CLI 0.163.0 found on PATH (Observed 2026-10-17, installed by the maintainer
  outside this task); discovery checks Not run (Gate C)";
- `clients/codex-cli/README.md` status line: same Codex fact.
- Phase 6: `docs/workshop-ai-stage-1-handover.md`; this task's `Status:` line and catalogue row.
