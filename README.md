# Workshop AI (Stage 1)

`wai` runs one task with one AI client and keeps the task's verified state in your project, so a new session can
resume it and another client can take it over from a reviewed package. Specification: [docs/stage-1-spec.md](docs/stage-1-spec.md).

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

## Work in VS Code

Open `workshop-ai.code-workspace` (File > Open Workspace from File). It shows this repository, the sandbox and the
shared infrastructure side by side. Terminal > Run Task… then pick:

- **Claude Code + Codex** — both clients in split terminals, started in this repository (Claude with the shared
  agents and skills);
- **Claude Code** or **Codex** — one client;
- **Workshop AI terminal (wai)** — a PowerShell terminal with the `wai` alias, in the sandbox. Approvals work here:
  it is a normal terminal, not an AI session.

VS Code suggests the official Claude Code and Codex extensions (chat panels); they are optional and use the same
sign-in as the command-line clients.

## Test

```powershell
python -m unittest discover -s tests
```
