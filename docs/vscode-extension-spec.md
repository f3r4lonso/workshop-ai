# Workshop AI — VS Code extension specification

> **v2 note (2026-10-20):** paused and out of scope for the proposed Workshop AI v2 (`infra/docs/workshop-ai-v2/`, decision D-V2-03). Kept as a record; the `--json` output in `wai` stays because the v2 app uses it.

Status: proposed (2026-10-18). Written under infra `tasks/projects/workshop-ai/workshop-ai-vscode-extension-specification.md` (Gate A
passed 2026-10-18); security-reviewed and approved at its Gate B (2026-10-18; D7 decided, §8.9). Nothing here is
built.

Requirement ids (FR-xx, NFR-xx, §n) refer to the product vision v1.2 (infra `docs/workshop-ai-product-vision.md`).
New ids `EXT-nn` are used only where no FR covers the need; each has an observable **Check**. Decisions D1–D11 are
vision §17.10; open decisions R1–R12 are vision §17.11 (R10–R12 added 2026-10-20) (the only register; §11 here adds none).

Evidence labels: **Observed** (seen on the maintainer's machine or in this repository's code), **Documented** (official
docs, URL and date), **Verified** (read in the stable VS Code API typings `@types/vscode` 1.140.0, per infra
`docs/vscode-extension-technology-research.md`, 2026-10-18), **Inference**, **Proposed** (designed here),
**Requires verification**, **Not run**. Every statement about what a client or VS Code exposes carries one.

## 1. Scope and non-goals

**In scope:** a VS Code extension ("the extension") that is the main hub over `wai` (D1):

- detect or ask which AI clients the user has (Claude Code CLI, Codex CLI);
- set up or reuse the shared infrastructure clone (D3);
- show projects and tasks, create and pick tasks (through `wai`);
- launch interactive client sessions in visible integrated terminals after an approval, and close them (D4);
- warn when Claude Code runs low, and offer a manual "running low" trigger for every client (D5);
- switch a task to the client the user chooses, with a saved checkpoint, a handoff package and a recap (D6, D9).

**Decisions applied:** D1 `wai` is the backend; D2 TypeScript, no runtime npm dependencies, code in
`vscode-extension/`; D3 one shared infra clone; D4 the extension launches clients itself, interactively, one approval
per launch; D5 automatic warning for Claude Code, manual trigger for all; D6 state + deterministic recap, no
transcripts; D7 approval path decided at Gate B (§8.9); D9 the user chooses the next client; D10 option (a);
D11 English UI strings.

**Non-goals:**

- writing, loading or managing agents or skills inside the extension (owner exclusion, 2026-10-18);
- publishing or distributing the extension (Marketplace, VSIX releases, signing); a local `.vsix` for the owner's
  own install is a build-task question, not a release;
- a webview UI (deferred, vision §2.2), chat panels, or reading client conversation output;
- non-interactive client runs (`claude -p`, `codex exec`, Agent SDK, Codex app-server) and unattended
  continuation: Stage 3, behind the vision §17.2 hard gate;
- automatic routing (Stage 4); new providers (Stage 5);
- the VS Code tasks in `workshop-ai.code-workspace` that start `claude` and `codex` directly: they are the user's
  own shortcuts, outside the product, and the extension does not use them.

## 2. User journeys

Approval points are marked **[A1]** (start a client / run a verify command), **[A2]** (release a handoff package),
**[A3]** (save a checkpoint), as in `docs/stage-1-spec.md` §7, and **[AX-n]** for the extension's own new ones.
"Approval" means the path decided for R1 (§8.9). Steps marked **Stage 3** are not in any Stage 2 increment.

### J1 — First run

1. The user installs the extension locally and opens a folder. If the workspace is not trusted, the extension stays
   inactive and says why (§8.6).
2. The extension looks for `claude` and `codex` on PATH (§4) and shows what it found, labelled "found on PATH".
3. The user confirms each found client, removes any, or adds one by choosing its executable. **[AX-1]** (confirm
   client list; a plain quick pick, no security weight).
4. The extension looks for the infra clone: setting `workshopAi.infraPath`, else env `WORKSHOP_AI_INFRA`, else
   `%USERPROFILE%\workshop\infra`. If it is a git repository whose `clients/` and `tasks/` folders exist, it is reused.
5. If none exists: the user pastes the infra repository URL (never guessed, never stored in any repository). Only
   `https://` and `ssh://`/`git@` URLs are accepted. The extension shows URL and target folder; refuses a non-empty
   target. **[AX-2]** (clone). It runs `git -c protocol.allow=never -c protocol.https.allow=always
   -c protocol.ssh.allow=always clone -- <url> <folder>` with an argument array, no shell (§8.7).
6. The extension checks `wai` (§3.2 invocation rule): `python -E -s -m workshop_ai --version` with the working
   folder set to the configured product folder (machine-scoped setting `workshopAi.waiPath`). Missing → J7c.

### J2 — Open a project and pick or create a task

1. The user opens a project folder. If it has no `.workshop-ai/`, the extension offers `wai init` (no approval; it
   only creates files the user can delete; `wai` refuses the infra repository, exit 3).
2. The Tasks view lists tasks from `wai status --json` (§3.2).
3. "New task": the user enters an id and **chooses the client** from the confirmed list (FR-02); the extension runs
   `wai task new <id> --client <client> --no-edit` and opens `task.md` in the editor for Objective and Acceptance
   criteria.
4. "Add context": the user picks files in the explorer; the extension runs `wai context add <id> <paths…>`.

### J3 — Start a client

1. The user runs "Start task" (or "Resume task") on a task whose contract is valid.
2. The extension calls `wai launch-plan <id> [--resume] --json` (§3.2). `wai` validates the contract, writes and
   scans `brief.md`, and returns the client, folder, exact argument list, context list and the SHA-256 of `brief.md`
   and `task.md`. A scan block stops here.
3. The extension checks that `argv[0]` is the executable the user confirmed for that client (§4), then shows
   client, folder, full command line (untruncated) and context list. **[A1]**.
4. On approval, the extension re-hashes `brief.md` and `task.md`; any change → refuse and restart at step 2. It then
   creates a terminal whose process is the client executable with that argument list (`window.createTerminal` with
   `shellPath`/`shellArgs`, `cwd` = project root; Verified) and sends no text to it (EXT-04). The confirmed
   executable SHOULD be a `.exe`: a `.cmd`/`.bat` shim runs through `cmd.exe`, which re-parses arguments
   (Inference); a shim is refused when any argument contains `" & | % ^ < >`.
5. The terminal is named `Workshop AI: <task-id> (<client>)`. The task's `status` becomes `in-progress` through
   `wai` on the next checkpoint, not by the extension.

If R1 is not decided in favour of the native dialog, step 3–4 are replaced by: the extension opens a visible
terminal running `wai start <id>` (or `wai resume <id>`), and `wai` shows A1 and launches the client as in Stage 1.
This is the **fallback launch path** (§11 Q1).

### J4 — Finish a task, or switch to the next client (D4, D9)

1. The user runs "Finish / switch" on the task. The session may still be open.
2. The extension asks the user to end the session in the client (e.g. `/exit`) so the client writes its final edits
   to `task.md`; it never types into the client terminal. While a client terminal the extension created for this
   task is still running (`exitStatus` undefined), checkpoint and switch are refused (EXT-08).
3. The extension runs `wai checkpoint <id>` through the approval path for A3, and for a `verify` command A1-verify
   (§8.9).
4. "Done": the task stays with its client; stop here. "Switch": continue.
5. The extension shows the confirmed clients. It MAY show a suggestion labelled **Proposed** with its basis
   (available on PATH; usage signal; the task's previous client). **The user chooses.** No choice → nothing opens
   (D9).
6. The extension runs `wai switch prepare <id> --to <client> --json` (§3.2): the package is built from the last
   checkpoint, scanned, and the recap generated (§7.3). A scan block stops here (J7d).
7. The extension runs `wai handoff approve <pkg-id>` through the approval path for A2 (§8.9; recommended: an
   external console window, not an integrated terminal). **[A2]** (Stage 1 rule: the person reviews the package
   and, without gitleaks, types `reviewed`; `wai` re-checks the manifest hashes).
8. `wai task set-client <id> <client>` records the new client in `task.md` (header `client`, a `History` line).
9. J3 runs for the new client with `--resume`; the brief points the new session at the package and recap.
10. The extension offers to close the old client terminal **only** if the checkpoint of step 3 succeeded; the user
    confirms. **[AX-3]**. It never closes a terminal it did not create.

### J5 — Usage running low

- **Manual trigger (every client, first increment):** the user runs "I am running low" on the active task. The
  extension asks which case applies:
  - *context window full* → offer "compact in the client" (the user types `/compact`) or "fresh session, same
    client" (J4 steps 1–3, then J3 with `--resume`);
  - *plan or rate limit reached* → J4 from step 1 with "Switch" preselected.
- **Automatic warning (Claude Code, first increment, after its own gate — R3):** a project-level status line or
  hook writes a small usage file (§6.1); the extension watches it and shows a status bar item and a warning at the
  thresholds of §6.4. The warning offers the same two choices. It never starts a checkpoint, switch or client by
  itself.
- **Automatic continuation (Stage 3 only):** on a plan-limit signal, prepare the switch and open the next client
  without a person's action. Not specified for build; requires the §17.2 hard gate (R7).

### J6 — Resume after VS Code restarts

1. On activation the extension reads `wai status --json`; tasks `in-progress` are shown with their client and last
   checkpoint.
2. The extension creates client terminals with persistence turned off (`isTransient`, Verified), so they are not
   revived after a restart. Whether the client process itself is ended when VS Code closes is **Requires
   verification**; the extension does not re-attach to any terminal it did not create in this window.
3. "Resume task" runs J3 with `--resume`. Unsaved work in the old session is lost unless the client wrote it to
   files; the resume brief tells the new session to trust current files over the contract (Stage 1).

### J7 — Failure cases

| Case | Behaviour |
|---|---|
| a. Client missing (not on PATH, or path setting invalid) | The client is shown "not found"; start and switch to it are disabled; a link to infra `docs/onboarding.md`. `wai launch-plan` also checks PATH (exit 4). |
| b. Clone fails (network, auth, non-empty folder, git missing) | Show git's exit code and the first lines of its error output, with no URL credentials; delete nothing; offer retry or choosing an existing clone. |
| c. `wai` or Python missing | Every action is disabled except "Locate wai". |
| d. Handoff blocked by the secret scan | Show file, line and rule only (never the matched value, Stage 1 §8); the switch stops; the old session stays open. |
| e. Approval declined or closed | Nothing runs; message "Not started (approval declined)"; state unchanged. |
| f. `wai` returns invalid JSON or a non-zero exit | Show the exit code meaning (Stage 1 §9) and `wai`'s message; never retry an action that needs approval. |
| g. Hand edits since the last checkpoint | Handled by `wai` at A3 (NFR-01); the extension never writes state files itself. |

## 3. Components and responsibilities

```text
 VS Code window
 ┌───────────────────────────────────────────────┐
 │ Workshop AI extension (TypeScript, ext. host) │
 │  views · commands · status bar · terminals    │
 └──────┬──────────────┬─────────────────┬───────┘
        │ execFile     │ createTerminal  │ file watcher (read-only)
        ▼ (JSON out)   ▼ (client argv)   ▼
   wai (Python)   client terminal    .workshop-ai/usage/*.json
   state, scans,  (claude / codex,   (written by the project-level
   handoffs,      interactive)       status line or hook, §6.1)
   recap, briefs
        │ reads/writes
        ▼
   <project>/.workshop-ai/   (context store, §7)      infra clone (read-only)
```

### 3.1 Extension UI (TypeScript, VS Code extension API)

- **Owns:** views (Clients, Tasks), commands, a status bar item (active client, usage level), an output channel
  (its own log, §8.2), the approval UI if R1 allows it, creating and disposing **its own** terminals.
- **Launches:** client sessions (J3 step 4) and `wai` approval terminals (J4). Runs `wai` non-interactive commands
  with `child_process.execFile` (Node built-in; Inference, standard Node).
- **Opens and closes:** only terminals it created (tracked by object identity, not by name).
- **Never:** writes `.workshop-ai/` state files directly; calls `Terminal.sendText` on any terminal (EXT-04); reads
  terminal output; reads client config or session folders; stores task state in VS Code storage.

### 3.2 Backend and orchestrator — `wai` (Python standard library)

Keeps all Stage 1 duties: contracts, state, scans, approvals A1–A3, packages. New for the extension (Proposed;
built by the Stage 2 tasks):

| Command / mode | Purpose | Approval inside `wai` |
|---|---|---|
| `--json` on `status`, `resources`, `task show`, `context list`, `handoff show` | machine-readable output, one JSON object on stdout, `schema` field `wai.v1` | none (read-only) |
| `wai launch-plan <id> [--resume] [--client <c>] --json` | validate, write and scan the brief, return `{client, cwd, argv, context, warnings}`; launches nothing | none |
| `wai task set-client <id> <client>` | record the chosen client in `task.md` with a `History` line | none (a header change shown at the next A3) |
| `wai switch prepare <id> --to <client> --json` | refuse if no checkpoint since the session started; `handoff create`; generate the recap; return package id, scan result, recap path | none (A2 follows separately) |
| `wai recap <id> [--json]` | deterministic recap from the last checkpoint and the Stage 2 store (§7.3) | none |
| `wai statusline` / `wai hook stop-failure` | read the client's JSON on stdin, write the allowed fields to `.workshop-ai/usage/` (§6.1) | none; only after the R3 gate |

Interface: argument arrays only; exit codes as Stage 1 §9; JSON errors `{"error": {"code": n, "message": "…"}}`.
`wai` stays the authority for every state change; the extension never edits state itself.

**Invocation rule (EXT-09):** the extension runs `wai` as `<python> -E -s -m workshop_ai --project <project> …` with
the working folder set to the product folder, never the project folder, so a `workshop_ai/` folder or
`PYTHONPATH` in a project cannot replace `wai` (`-m` searches the working folder first; Documented Python
behaviour, Inference for this layout). `workshopAi.waiPath`, `workshopAi.infraPath` and client path overrides are
**machine-scoped** settings, so a repository's `.vscode/settings.json` cannot redirect them.
**Check:** with a project containing a fake `workshop_ai/__main__.py` that writes a marker and a workspace
`.vscode/settings.json` setting `workshopAi.waiPath`, every extension command still runs the real `wai` and no marker
appears.

### 3.3 Client adapters (one per CLI, inside `wai` and mirrored in the extension's detection)

| Adapter | Detection | Start command (built by `wai launch-plan`) | Usage signals | Limitations |
|---|---|---|---|---|
| `claude` | `claude` / `claude.exe` / `claude.cmd` on PATH | `claude --add-dir <infra>\clients "<first message>"` (Stage 1, Observed in code) | §6.1 | interactive only |
| `codex` | `codex` on PATH | `codex` in the project folder with the first message as prompt argument (Requires verification: codex accepts an initial prompt argument), optional `--sandbox read-only` | display only (§6.2) | launched only after R8; no per-agent tool limits (infra `ai-architecture.md` §4) |
| `copilot` (planned, `docs/copilot-and-console-buttons-plan.md`) | `copilot` on PATH | `copilot` in the project folder; interactive start with a first message Requires verification (proposed R10); never `-p`, `--allow-all` or `--yolo` | none | handoff target first; launched only after proposed R10 and R11 |

Adding a client follows FR-13: a new adapter row, no change to the task or state formats.

### 3.4 Context store

Stage 1 files (`docs/stage-1-spec.md` §3–§4) plus the Stage 2 knowledge store of the token-optimization task
(JSON files in `.workshop-ai/`, its own design note) plus the files of §7. All in the project repository; nothing in
infra.

### 3.5 Who launches, opens and closes what (D4)

| Thing | Launched by | Opened / closed by | Condition |
|---|---|---|---|
| Client session | extension (J3) — or `wai start` on the fallback path | extension (own terminals only) | one approval per launch; close only after a saved checkpoint and the user's confirmation |
| `wai` approval prompts (A1-verify, A2, A3) | extension opens `wai …` in the approval channel of §8.9 (external console window or integrated terminal) | extension; the window ends with the command | the extension never writes to it |
| `wai` read-only and prepare commands | extension (`execFile`, no terminal) | — | no approval needed |
| `git clone` / `git pull --ff-only` of infra | extension (`execFile`) | — | AX-2 / AX-4; AX-4 shows the incoming commit range and the changed files under `agents/`, `skills/` and `clients/`, because they load into every client session through `--add-dir` |

## 4. Client detection

- **EXT-01 — Detection is a PATH lookup only.** The extension MUST find clients by searching the directories of
  `PATH` with the extensions in `PATHEXT` for the names `claude` and `codex`, without running them. It MUST NOT run a
  client (not even `--version`), read credential stores or client config folders, or trigger a login.
  **Check:** with a fake `claude.cmd` on PATH that writes a marker file when run, detection lists Claude Code and the
  marker file does not exist.
- The user confirms the list, removes entries, or adds an executable by file picker (J1 step 3).
- **Recorded:** client id and an optional executable path override, as the user setting `workshopAi.clients`
  (machine scope). This is a preference, not task state, and is never written to a repository (user paths).
- The per-task client choice is recorded only in `task.md` (`client:` header), by `wai` (FR-02).
- Account, plan and login state are not detected. The user checks them in the client (`/status`, `codex login
  status`; infra client guides).

## 5. Client-switch and handoff flow

Numbered flow; **[A…]** = approval point, **(S3)** = Stage 3 only.

1. Trigger: the user's "Finish / switch", the manual "running low" trigger, or a Claude Code warning that the user
   clicks. (S3: a plan-limit signal starts step 2 by itself.)
2. The user ends the client session (the extension asks; it does not type). (S3: the session is ended without the
   user.)
3. **Checkpoint:** refused while the task's client terminal is running (EXT-08); `wai checkpoint <id>` —
   **[A1-verify]** for `verify`, **[A3]** for the diff (channels in §8.9).
4. The user picks "Switch" and **chooses the next client** (D9). Suggestion, if any, labelled Proposed.
   (S3: none — automatic routing is Stage 4, so even Stage 3 needs a pre-recorded user choice per task.)
5. **Package and recap:** `wai switch prepare <id> --to <client> --json` → handoff package from the last
   checkpoint, built-in scan + gitleaks if installed, recap.
6. **Secret scan result:** a block stops the flow (J7d).
7. **Release:** `wai handoff approve <pkg-id>` in the A2 channel (§8.9) — **[A2]**; `wai` re-checks the manifest
   hashes, so a package changed after the scan is refused.
8. **Record:** `wai task set-client <id> <client>`.
9. **Open the next client:** J3 with `--resume` — **[A1]**.
10. **Close the old terminal:** offered only after step 3 succeeded — **[AX-3]**.

Every crossing of a provider boundary **that Workshop AI performs** happens at step 7 (FR-08, FR-09, vision §17.5
unchanged). Residual crossings outside its control (§8.1): IDE agents of other providers installed in VS Code can
read the whole workspace, including unapproved packages; and Claude Code started in an integrated terminal may
connect to its VS Code IDE integration and receive open files, selection and diagnostics beyond the selected
context (Requires verification; vision §17.11 R9).

## 6. Usage-limit detection (D5)

### 6.1 Claude Code

| Signal | What it gives | Requires | Reliability | Label |
|---|---|---|---|---|
| Status line stdin JSON: `context_window.used_percentage`, `remaining_percentage` | context-window fill | a `statusLine` command in **project** settings (`.claude/settings.json`) or user settings | updated as the session runs | Documented, <https://code.claude.com/docs/en/statusline>, 2026-10-18 |
| Status line: `rate_limits.five_hour.used_percentage`, `rate_limits.seven_day.used_percentage`, `…resets_at` | plan-limit use (0–100) and reset time | as above; present **only for claude.ai Pro and Max subscribers** (or behind a gateway with spend limits) and only after the first API response; each window may be absent | good when present; absence ≠ zero | Documented, same URL, 2026-10-18 |
| Effect of a custom status line | it hides most footer keyboard hints | — | — | Documented, same URL |
| Whether a project status line replaces the user's own status line in that project | — | — | — | Requires verification (R3) |
| Hook `StopFailure`, matcher `rate_limit` (also `billing_error`, `max_output_tokens`, …) | a turn ended on a rate limit; no percentage | a hook in project `.claude/settings.json` | event only | Documented, <https://code.claude.com/docs/en/hooks>, 2026-10-18 |
| Hooks `PreCompact` / `PostCompact` (matcher `manual` / `auto`) | compaction happened (context window case) | as above | event only | Documented, same URL |
| `/context`, `/cost` | shown to the user | a person reads them | display only | Documented in vision §17.6 |
| `/usage`, `/status`, rate-limit messages | shown to the user | a person reads them | display only | Requires verification (contents not re-read) |

Design (Proposed, gated by R3): the status line or hook command is `python -m workshop_ai statusline` /
`… hook stop-failure`. It reads stdin, keeps **only** `context_window.used_percentage`,
`rate_limits.{five_hour,seven_day}.{used_percentage,resets_at}` and the event name, and writes
`.workshop-ai/usage/claude.json` atomically. It MUST NOT read or store `transcript_path`, prompt text, session ids or
any other field. Only project-level client configuration is used; user-level client configuration is never changed
(vision §17.10 D5). The project `.claude/settings.json` change is shown to the user as a diff and needs its own
approval in the build task.

### 6.2 Codex CLI

| Signal | What it gives | Requires | Reliability | Label |
|---|---|---|---|---|
| `/status` | model, approval policy, writable roots, remaining context capacity, current token usage | a person reads it | display only | Documented, <https://learn.chatgpt.com/docs/developer-commands?surface=cli>, 2026-10-18 |
| `/statusline` (`tui.status_line`) | footer items incl. rate limits and token counters | user-level `config.toml` | display only; not script-readable | Documented, same URL |
| `/usage` | daily/weekly/cumulative token activity | a person reads it | display only | Documented, same URL |
| `notify` | `agent-turn-complete` event, no usage fields | user-level config | — | Documented (research note [5]) |
| app-server `account/rateLimits/read` | rate limits | programmatic interface | — | Requires verification; counts as scripted use before R7 (Inference) |

First increment for Codex: **manual trigger only** (R5).

### 6.3 VS Code

| Signal | Requires | Reliability | Label | Use |
|---|---|---|---|---|
| Shell integration `executeCommand` + `TerminalShellExecution.read()` | shell integration active; only for commands it runs | raw output with escape codes; a client TUI is not a shell command | Verified | **not used** (reads conversation content, D6) |
| Proposed terminal-data APIs | proposed API, not allowed in a normal install | — | Inference | **not used** |
| `workspace.createFileSystemWatcher` on `.workshop-ai/usage/*.json` | — | reliable for files | Verified | used for §6.1 |

### 6.4 Thresholds and fallbacks

- Context window ≥ 80 % → "context almost full": suggest `/compact` or a fresh session with the **same** client.
- `five_hour` or `seven_day` ≥ 90 %, or a `rate_limit` StopFailure → "plan limit almost reached": suggest a switch.
- Values are defaults in settings (`workshopAi.usage.*`); unknown or absent fields show "usage: unknown", never 0.
- Fallback order: hook/status-line file → what the client shows the user → the **manual trigger**, which needs no
  undocumented signal and is always available (EXT-05).

## 7. State model

### 7.1 Files (extending `docs/stage-1-spec.md` §3)

```text
<project>/.workshop-ai/
├── project-state.md            (Stage 1, versioned)
├── tasks/<task-id>/
│   ├── task.md                 (Stage 1, versioned; `client` header + History lines for switches)
│   ├── brief.md                (Stage 1, ignored)
│   └── recap.md                (new, generated, ignored)
├── handoffs/<pkg-id>/          (Stage 1, ignored; may include recap.md)
├── store/                      (Stage 2 knowledge store, token-optimization task)
├── usage/claude.json           (new, ignored; §6.1)
├── .snapshots/                 (Stage 1, ignored)
└── .gitignore                  (adds recap.md, usage/)
```

`History` line for a switch (new; written by `wai task set-client`):

```markdown
- switch 1, 2026-10-25T15:02, claude → codex, package t3-validation-1 (approved), reason: plan limit (user)
```

`usage/claude.json`:

```json
{"schema": "wai.usage.v1", "client": "claude", "updated": "2026-10-25T14:58:10",
 "context_used_pct": 41, "five_hour_used_pct": 92.5, "five_hour_resets_at": 1792936800,
 "seven_day_used_pct": 30, "seven_day_resets_at": 1793368800, "last_event": "StopFailure:rate_limit"}
```

### 7.2 What the extension keeps in VS Code storage

UI preferences only: last selected task per workspace, view state, the confirmed client list and path overrides,
thresholds. **Never** task state, decisions, recaps, package contents or usage history (EXT-06).

### 7.3 Recap format (D6)

Generated by `wai recap` from the last checkpoint of `task.md`, `project-state.md` and Stage 2 store items for the
task; deterministic (same input → same bytes, no timestamps other than the checkpoint's), no model call, no
transcript text; scanned like a package file.

```markdown
# Recap: t3-validation (rev 3, checkpoint 2026-10-25T14:59, commit 3f2a1c0)
From: claude · To: codex · Reason: plan limit (user)

Objective: validate malformed rows in csvsummary.
Done: [x] decisions recorded · Open: [ ] tests for a malformed row · [ ] full test run
Decisions: D-001 error format "row N: <reason>" · D-002 skip the row and warn
Open questions: none
Next action: implement validation in reader.py; run python -m unittest
Read: handoff.md, then context/csvsummary/reader.py
```

### 7.4 Location rules (vision §13)

All state stays in the project repository or its ignored folders. `wai` refuses to init inside infra (Stage 1,
exit 3). The infra clone is read-only for the product (EXT-03).

## 8. Security and trust boundaries

### 8.1 Providers

Each provider is a separate trust boundary. Context that Workshop AI passes to another client crosses only through an
approved package (§5 step 7; FR-08, FR-09). The extension never sends file content to any service. Not covered, and
stated to the user in the extension's first-run notice: other AI extensions installed in the same VS Code can read
the workspace; Claude Code's own IDE integration may share editor state with the session (R9). The build task
verifies whether that integration activates when the extension launches Claude Code, and how to turn it off for
Workshop AI sessions.

### 8.2 Credentials and client files

- **EXT-02 — No credential or session access.** The extension and `wai` MUST NOT read, store or reuse credentials
  and MUST NOT read client session or config files (`~/.claude`, `~/.claude.json`, `~/.codex`, `auth.json`,
  `.credentials.json`). The status line/hook command reads only its stdin.
  **Check:** run the full extension test journey with a process-level file-access monitor (or a test double for
  `fs` and the Python `open` in tests) and assert that no path under those names is opened; grep the extension and
  `wai` sources for those names: only deny-list constants and docs match.
- The extension's log (output channel) records commands and exit codes only, never task text, recap text or
  file contents.

### 8.3 No state in infra

- **EXT-03 — Infra is read-only.** The extension MUST NOT write any file inside the infra clone except through
  `git clone` and `git pull --ff-only` after approval (AX-2, AX-4).
  **Check:** a hash of every file in the infra clone (including ignored files; infra uses a whitelist
  `.gitignore`, so `git status` alone is blind) taken before and after the full test journey is identical, and
  `git status --porcelain --ignored` shows no new entry.

### 8.4 Terminals

- **EXT-04 — The extension never writes to a terminal.** It MUST NOT call `Terminal.sendText` or a shell
  integration `executeCommand` on any terminal, and therefore never writes to a terminal where an approval prompt
  is or may be shown. Client and `wai` terminals get their command through `shellPath`/`shellArgs` at creation.
  **Check:** a source grep for `sendText` and `shellIntegration` in `vscode-extension/` finds nothing (the
  extension legitimately uses `commands.executeCommand`, so that name is not grepped); an integration test spies on
  `Terminal.sendText` for every terminal the extension creates and asserts zero calls.
- **Who else can write to an integrated terminal:** any extension can list all terminals (`window.terminals`,
  Documented <https://code.visualstudio.com/api/references/vscode-api>, 2026-10-18) and call `sendText` on any of
  them (Verified in typings; no restriction found — Inference). So another extension, or an AI agent inside VS Code
  that can drive terminals, could type `y` into a `wai` approval prompt or text into a client session.
- **TTY check:** an integrated terminal is a pseudo-terminal, so `isatty()` is true for anything running in it,
  including commands an IDE agent runs in an integrated terminal (Inference; Requires verification per agent). The
  Stage 1 FR-08 check therefore does not prove a person answered inside VS Code.
- Residual risk accepted for the first increment: a malicious extension already installed in the user's VS Code can
  act as the user. The mitigation is the user's own extension hygiene; the spec does not claim protection against it.

### 8.5 Commands other extensions can invoke

Any extension can run any contributed command: "There are no restrictions when executing commands that have been
contributed by extensions" (Documented, VS Code API reference, 2026-10-18).

- **EXT-07 — Commands never act on arguments alone.** Every command that leads to an approval, a launch, a clone, a
  switch or a terminal close MUST ignore caller-supplied commands, paths and client ids except a task id validated
  against `^[a-z0-9][a-z0-9-]{0,63}$`, MUST rebuild the action from `wai` output, and MUST show its approval.
  Only one approval may be pending at a time; after a decline, the same action is refused for 30 seconds and a
  repeated invocation never stacks dialogs (no approval fatigue).
  **Check:** for **every** contributed command, a test extension calls it with forged arguments (argument list,
  paths, a clone URL starting with `-`, a client id not confirmed by the user): no terminal, clone or close happens
  before the approval UI appears, what is shown is rebuilt from `wai` output or the user's settings, and a second call
  while one approval is pending creates no second dialog.

### 8.6 The extension's own permissions

- Declares `capabilities.untrustedWorkspaces.supported: false` (Restricted Mode) and checks `workspace.isTrusted`
  (Verified).
- Activation events: its commands and views only, never `*`.
- File access: reads `.workshop-ai/usage/` and `wai` JSON output; all writes go through `wai`.
- No network access except the infra clone/pull through git (product `AGENTS.md`).

### 8.7 Supply chain

- Runtime npm dependencies: none (D2). The `vscode` module is supplied by the host (Inference).
- Development tooling (types, compiler, test runner, packager) is approved one package at a time by the build task
  under the infra `dependency-license-review` skill; no package with an install script (e.g. `esbuild` postinstall,
  research note §2) unless approved; a lockfile is committed; installs use `npm ci --ignore-scripts` (run only by
  the build task after approval).
- `git` and `python` are found on PATH and called with argument arrays (`execFile`, no shell); user text (URL,
  task id) is never interpolated into a command string.

### 8.8 Untrusted content

Task files, catalogue text from infra, package files and usage files are data. The extension shows them as plain
text (no trusted Markdown, no command links), never runs text from them, and validates usage JSON against its
schema (unknown fields ignored, out-of-range values → "unknown"). Text written by an AI session (objective, file
names, recap) that appears in an approval is shown in a fixed layout, labelled as content, with control and
bidirectional-override characters removed. The usage file can be written by the session itself, so usage warnings
are labelled advisory and never start an action (J5). The infra clone is never opened as a workspace folder by the
extension, so its `.vscode/` settings do not apply (Inference).

### 8.9 Approval path (D7; decided at Gate B)

| Candidate | How | Strength | Weakness | Label |
|---|---|---|---|---|
| **T — `wai` in a visible integrated terminal** (Stage 1 prompts) | the extension opens a terminal running `wai …`; the person types `y` | reuses tested code; no new approval code | any extension or terminal-driving agent can type into it (§8.4); passes the TTY check | Observed (Stage 1 code); weakness Inference |
| **M — native modal dialog from the extension** (`showWarningMessage(…, {modal: true}, …)`) | the extension shows the full action and waits for a click | not reachable through `sendText`; the extension controls the text | another extension can trigger the command (mitigated by EXT-07); whether any extension or AI agent can **answer** it is unknown | Verified (API); safety Requires verification |
| ~~F — approval token file~~ | `wai` writes an approval file the extension reads | — | rejected: any process with workspace write access, including an AI session's file tools, can forge it | Inference |
| **X — `wai` in an external console window** opened by the extension (e.g. a new `conhost`/Windows Terminal window running `wai …`) | Stage 1 prompts, outside VS Code | not reachable by `Terminal.sendText` or by IDE agents' integrated terminals | worse usability; OS-level automation still possible | Inference; Requires verification |

**Security review (Gate B, 2026-10-18) found T not acceptable for A2 or A1-verify:** other extensions can type into
it, and IDE agents that run commands in integrated terminals pass the TTY check and can read the prompt and answer
it (e.g. an agent runs `wai handoff approve`, reads the prompt, types `reviewed` and `y`). A1-verify is a shell
command that the client session can change in `task.md`, so it needs the same protection as A2.

**Decided at Gate B (2026-10-18, product owner), as recommended:**

- **M** for the A1 client launch and AX-2, AX-3, AX-4, only after the M verification items below pass and with
  EXT-09, the brief hash check (J3 step 4) and the `.cmd` rule (J3 step 4); until then the J3 fallback launch path.
- **X** for A2 and A1-verify; a `verify` command changed since the last checkpoint is refused until approved in X.
- **T** for A3 (local state only) as an interim, with candidate 4 below.
- Never use quick picks or input boxes for approvals (`workbench.action.acceptSelectedQuickOpenItem` is reachable
  through `executeCommand`; Inference).

**M verification items (Requires verification before M is used):**

1. no command reachable through `commands.executeCommand` can accept or dismiss a modal, under both the native and
   the custom `window.dialogStyle`;
2. the default (Enter) button is not the affirmative one, so keystrokes meant for a client terminal cannot approve;
3. long argument lists and context lists are shown without truncation;
4. a test extension invoking the command while a dialog is open cannot complete it.

FR-08 strengthening (R2) — recommended **yes**. Inside VS Code an approval must come through a channel that other
extensions and IDE agents cannot write to or read and answer (M or X). Candidates:

1. a per-prompt one-time code typed back — **not recommended** as the measure: it stops blind injection only;
2. a launch nonce in the environment — **not recommended**: readable by child processes;
3. approvals outside VS Code (X) — **recommended** for A2 and A1-verify;
4. record each approval with its channel in the task `History` — **recommended** for every approval (detects, does
   not prevent).

The FR-08 check gains an injection test: `sendText("y")` into the approval channel, and an IDE agent running the
approve command, both fail to approve.

## 9. Provider-terms check (vision §17.2)

| Automation step | Current Documented position (vision §17.2, 2026-10-17) | Re-confirm before |
|---|---|---|
| Launch an interactive client in a terminal after approval (J3) | Anthropic: ordinary use of the unmodified Claude Code binary by the end user on their own plan is allowed; third-party apps may not offer Claude.ai login, route plan credentials, or store tokens. OpenAI: interactive Codex with the user's own sign-in. Launching from an extension is not addressed by either source | the launch increment ships (R4), with URL and date |
| Read the Claude Code status line/hook data | a documented, user-configured feature of the client | the R3 gate (Inference: no terms issue) |
| Prepare package and recap, release after approval | local files only; no provider call | — |
| Usage-triggered continuation without the user (S3) | `claude -p`/Agent SDK draw from plan limits; `codex exec` reuses the saved login, API keys recommended for automation, ChatGPT auth for automation only as one's own account and never for public repositories | Stage 3 task prompt, per provider and plan (R7) |
| Codex app-server rate-limit read | not checked | R5 / R7 |
| Claude Code's IDE integration when launched in an integrated terminal (editor state shared with the session) | not checked | build task Gate A (R9) |

Not legal advice. Sources as cited in vision §17.2.

## 10. Staged roadmap (D10 option a)

| Increment | Vision stage | Content | Exit criterion | Gate |
|---|---|---|---|---|
| E1 Shell | 2 | detection (EXT-01), infra setup (AX-2), Tasks view and task creation through `wai --json`, Restricted Mode | J1 and J2 Observed on the sandbox | build task Gate B (plan), then its review gate |
| E2 Launch | 2 | J3 with the R1 outcome (M or fallback), EXT-04, EXT-07, J6; console and Start/Resume buttons (`docs/copilot-and-console-buttons-plan.md` part B, A1 on every launch) | J3 Observed with Claude Code; EXT-04/07 tests pass | R1 decided; R4 recorded |
| E3 Switch | 2 | J4/§5 with recap (needs `wai recap`, with the token-optimization task), manual trigger (J5) | one switch with recap Observed (vision §16 Stage 2 exit) | build task gate; token task recap delivered or a Stage 1-only recap approved |
| E4 Claude Code warning | 2 | §6.1 status line/hook, thresholds | warning Observed in a sandbox session at a real or simulated threshold (labelled) | R3 gate |
| E5 Automatic continuation | 3 | §5 (S3) steps | one automated switch Observed with §15.3 data | vision §17.2 hard gate (R7), Stage 3 task prompt |

## 11. Open questions

Register items R1–R8 are in vision §17.11 (the only register). Spec-level questions, each with a recommended
default, are recorded there under the item they belong to:

- **Q1 → R1:** if the modal dialog is rejected, does D4 (extension launches) fall back to `wai start` in a terminal?
  Default: yes (J3 fallback launch path).
- **Q2 → R2:** which FR-08 strengthening (§8.9 list)? Default: X (candidate 3) for A2 and A1-verify, M for
  launches, candidate 4 for every approval; not candidates 1 or 2.
- **Q6 → R9:** does Claude Code's IDE integration activate when launched by the extension? Default: assume yes,
  state it to the user, verify before E2.
- **Q3 → R3:** status line or hook only? Default: hook + manual trigger; status line only after the user sees the
  diff and what it replaces.
- **Q4 → R8:** Codex start argument form. Default: verify in the official Codex CLI docs before E2 supports Codex.
- **Q5 → R6:** use of the official Claude Code / Codex VS Code extensions. Default: not used.

D3, D11: no open point (D3 URL is supplied by the user at J1; D11 English UI).

## 12. Acceptance criteria for the build task

1. EXT-01…EXT-09 checks pass and are reported Pass / Fail / Not run; EXT-02 names its file-access monitor (e.g.
   Process Monitor or a test double) and the test sandbox.
2. J1, J2, J3, J4 (switch Claude Code → Claude Code fresh session at least; Claude Code → Codex once R8 allows) and
   J6 are **Observed** on the sandbox project; J7 a–f covered by tests.
3. No client is opened without the user's client choice (D9) and an approval; tested by declining each approval.
4. The manual "running low" trigger works with no usage file present (EXT-05).
5. Runtime dependencies in `vscode-extension/package.json`: none; every dev dependency has a recorded review.
6. Credentials never read/stored (EXT-02), no client session files read (EXT-02), no state in infra (EXT-03), the
   extension never writes to a terminal (EXT-04): each with its check output attached.
7. `wai` JSON outputs have unit tests; Stage 1 tests still pass; Stage 1 approval behaviour unchanged unless R2 is
   decided.
8. User-facing strings are English (D11) and in `vscode.l10n`-ready form.
9. Vision §17.2 hard gate untouched; no `claude -p`, `codex exec`, SDK or app-server call in the code (grep).

- **EXT-08 — No checkpoint or switch while the session runs.** **Check:** with the task's client terminal still
  running, "Finish / switch" and "running low → switch" refuse with a message, and no `wai checkpoint` or
  `switch prepare` is run.
- **EXT-05 — Manual trigger needs no signal.** "I am running low" MUST work for every client with no usage file.
  **Check:** with `.workshop-ai/usage/` absent, the command offers both J5 choices.
- **EXT-06 — VS Code storage holds preferences only.** **Check:** after the test journey, dump `globalState` and
  `workspaceState` keys: only the keys listed in §7.2 exist, and none contains task text.
