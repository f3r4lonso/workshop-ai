# Workshop AI — project rules

Shared rules for every AI client working in this repository (Codex reads this file; Claude Code imports it from
`CLAUDE.md`). The workspace rules in the shared infrastructure (`%USERPROFILE%\workshop\infra\AGENTS.md`) apply
too; its security and privacy rules always win.

- **Purpose:** Workshop AI v2: one local, Spanish-language browser app over the `wai` core (decision D-V2-01,
  approved 2026-10-20). `wai` stays a command-line tool that runs one task with one AI client, saves a verified
  task state in the project's own repository, resumes it in a new session and builds a manual handoff package for
  another client (`docs/stage-1-spec.md`). Requirements: the infrastructure repository's `docs/workshop-ai-v2/`;
  progress: `docs/v2-progress.md`. The VS Code extension (`vscode-extension/`) is paused (D-V2-03): keep it as a
  record, do not develop it.
- **Stage:** local POC; V3 increment in progress per `docs/v2-progress.md`. V1 is paused by the owner; V2 is owner-accepted.
- **Commands:** tests `python -m unittest discover -s tests`; run `python -m workshop_ai --help` or `wai.cmd`.
- **Constraints:**
  - `wai` and the app server are Python 3 standard library only. Front-end and extension packages need approval
    first (`dependency-license-review` skill).
  - The only network listener allowed is the app's loopback server (D-V2-04), with at least the security model of
    the Workshop Infrastructure UI server (v2 `architecture.md` §7); never weaken it. No other daemon or service.
  - No network access from `wai` itself, except an approved `git clone` / fast-forward `git pull` of the shared
    infrastructure repository.
  - `wai` starts clients as interactive sessions after an approval. The app may run an engine non-interactively
    (`claude -p`, `codex exec`, …) only when the owner starts that run, only at the engine's verified level in v2
    `engines.md`, tool-free first, and only after the engine's provider-terms check (R7) is recorded in its client
    guide (D-V2-05, D-V2-06). Nothing ever types input into a client terminal, runs git commands that write to a
    project, or touches credentials or client session files.
  - Every `wai` approval needs a person at a terminal; never add a flag that skips one. An in-app approval path
    needs its own recorded decision that changes this rule and meets v2 `architecture.md` §8 C1.
  - The app writes files only inside the allowlist of v2 `architecture.md` §4, keeping versions in
    `%USERPROFILE%\workshop\.workshop-ai\` (D-V2-07). That folder is private local data: never copy it into a
    repository.
  - Never write project state into the shared infrastructure repository.
- The user is a trader: report outcomes, not code explanations; reply in English.
