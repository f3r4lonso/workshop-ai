# Workshop AI

Workshop AI v2 is one local app, in Spanish, over the `wai` core. Requirements: the infrastructure repository's
`docs/workshop-ai-v2/`; progress: [docs/v2-progress.md](docs/v2-progress.md).

- **The app** (`server/` + `web/`, merged from the Workshop Infrastructure UI in increment V1): double-click
  `INICIAR.cmd` → http://127.0.0.1:8770/. Seven sections: Inicio, Tareas, Conversar (agent chains), Agentes y Skills,
  Archivos (with the Lector), Motores (every AI engine at its verified level) and Historial (arrives in V2). The first
  start builds the interface (`npm install`, `npm run build` in `web\`; needs Node.js). Security model:
  infra `docs/workshop-ai-v2/architecture.md` §7.
- **`wai`** runs one task with one AI client and keeps the task's verified state in your project, so a new session
  can resume it and another client can take it over from a reviewed package. Specification:
  [docs/stage-1-spec.md](docs/stage-1-spec.md).
- **Engine list:** `workshop_ai/engines.json`, read by both `wai` and the app.
- The VS Code extension (`vscode-extension/`) is paused (decision D-V2-03).

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
cd web; npm run build                    # interface
```
