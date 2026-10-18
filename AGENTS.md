# Workshop AI — project rules

Shared rules for every AI client working in this repository (Codex reads this file; Claude Code imports it from
`CLAUDE.md`). The workspace rules in the shared infrastructure (`%USERPROFILE%\workshop\infra\AGENTS.md`) apply
too; its security and privacy rules always win.

- **Purpose:** Workshop AI: a local command-line tool (`wai`) that runs one task with one AI client, saves a verified
  task state in the project's own repository, resumes it in a new session, and builds a manual handoff package for
  another client (Stage 1, `docs/stage-1-spec.md`); and a VS Code extension that is the main hub over `wai`
  (Stage 2, specified, not built: `docs/vscode-extension-spec.md`). Product vision: the infrastructure
  repository's `docs/workshop-ai-product-vision.md`.
- **Stage:** local POC.
- **Commands:** tests `python -m unittest discover -s tests`; run `python -m workshop_ai --help` or `wai.cmd`.
- **Constraints:**
  - `wai` is Python 3 standard library only. The extension (in `vscode-extension/`) is TypeScript on the VS Code
    extension API with no runtime npm dependencies; each development package needs approval first.
  - No daemon, service or network listener. The VS Code extension host and user-visible terminals do not count as
    background processes.
  - No network access, except an approved `git clone` and fast-forward `git pull` of the shared infrastructure
    repository, run by the extension.
  - The tool (`wai` or its extension) starts clients only as interactive sessions, after an approval, never
    non-interactively (`claude -p`, `codex exec`); it launches Codex only once Codex is a supported executing client.
    It never types input into a client terminal, never runs git commands that write to a project, and never touches
    credentials or client session files.
  - Every approval needs a person at a terminal; never add a flag that skips one. Any other approval path for the
    extension needs a recorded decision (vision §17.11 R1). The extension never writes to a terminal where an
    approval prompt is or may be shown.
  - Never write project state into the shared infrastructure repository.
- The user is a trader: report outcomes, not code explanations; reply in English.
