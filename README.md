# Workshop AI

Workshop AI v2 is one local app, in Spanish, over the `wai` core. Requirements: the infrastructure repository's
`docs/workshop-ai-v2/`; progress: [docs/v2-progress.md](docs/v2-progress.md).

- **The app** (`server/` + `web/`, merged from the Workshop Infrastructure UI in increment V1): double-click
  `INICIAR.cmd` → http://127.0.0.1:8770/. Seven sections: Inicio, Tareas, Conversar (agent chains), Agentes y Skills,
  Archivos (with the document editor), Motores (every AI engine at its verified level) and Historial (aggregate timeline pending). The first
  start builds the interface (`npm ci`, `npm run build` in `web\`; needs Node.js). Security model:
  infra `docs/workshop-ai-v2/architecture.md` §7.
- **`wai`** runs one task with one AI client and keeps the task's verified state in your project, so a new session
  can resume it and another client can take it over from a reviewed package. Specification:
  [docs/stage-1-spec.md](docs/stage-1-spec.md).
- **Engine list:** `workshop_ai/engines.json`, read by both `wai` and the app.
- The VS Code extension (`vscode-extension/`) is paused (decision D-V2-03).

## Set up on another Windows PC

Workshop AI is a local app, not a hosted website. Each PC needs its own clone and its own engine installations
and sign-ins. The [two-PC setup plan](docs/two-pc-local-setup-plan.md) records the current portability limits.
On a work PC, first confirm workplace policy allows Git, Python, Node.js/npm and access to the private Workshop AI
GitHub repository. Never copy client credentials between PCs.

Install Git, Python 3.10+ and Node.js/npm. In PowerShell, clone the shared infrastructure and the private app:

```powershell
$root = Join-Path $env:USERPROFILE 'workshop'
New-Item -ItemType Directory -Force -Path (Join-Path $root 'applications') | Out-Null
git clone https://github.com/f3r4lonso/ai-dev-framework.git (Join-Path $root 'infra')
git clone https://github.com/f3r4lonso/workshop-ai.git (Join-Path $root 'applications\workshop-ai')
```

The GitHub account used on that PC must be authorized for the private `workshop-ai` repository. If either
directory already exists, do not clone over it; inspect its Git status and follow the update steps below instead.
The first launch installs the exact frontend versions in the lockfile and builds the interface:

```powershell
Set-Location (Join-Path $root 'applications\workshop-ai')
.\INICIAR.cmd
```

To update later, close the app, confirm each checkout has no unreviewed changes (`git status --short`), and
fast-forward the repositories separately:

```powershell
git -C (Join-Path $root 'infra') pull --ff-only
git -C (Join-Path $root 'applications\workshop-ai') pull --ff-only
```

If a checkout has local changes, stop and review them before updating; do not reset or overwrite them. The UI
catalogue only shows project folders present under `applications`; clone other authorized project repositories
there if you want them listed.

**Portability limit:** the document-reading actions rely on the neighboring `applications\ai-reading-assistant`
project. That project has no GitHub remote configured in the current Workshop, so cloning the two repositories
above does not provide that helper; those reader actions are not yet verified on a clean second-PC setup. The
app's own server remains loopback-only. Conversations, notes, settings and document versions stay in the local
`workshop\.workshop-ai` folder and are not synchronized between PCs.

## Use it

PowerShell, in a normal terminal (approvals do not work from inside an AI session):

```powershell
Set-Alias wai "$env:USERPROFILE\workshop\applications\workshop-ai\wai.cmd"   # once per terminal
cd <your project repository>
wai init                                   # creates .workshop-ai/
wai task new my-task --client claude       # fill in Objective and Acceptance criteria
wai context add my-task src/file.py        # only the files the task needs
wai start my-task                          # asks first, then opens Claude Code
wai checkpoint my-task                     # after the session: save the verified state
wai resume my-task                         # later, in a new session
wai handoff create my-task --to codex      # package for another client
wai handoff approve my-task-1              # you review and release it
wai handoff show my-task-1                 # steps for the other client
wai status
```

Requires Python 3.10+ and Claude Code on PATH. The shared infrastructure is found at
`%USERPROFILE%\workshop\infra`, or set `WORKSHOP_AI_INFRA`, or pass `--infra`.

## Test

```powershell
python -m unittest discover -s tests   # wai core and app server
Push-Location web
npm.cmd ci
npm.cmd run build
Pop-Location
```

The full app test suite expects the surrounding Workshop workspace and its sibling projects; a minimal two-repository
clone is not a complete integration-test fixture.
