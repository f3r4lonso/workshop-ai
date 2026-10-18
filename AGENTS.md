# Workshop AI — project rules

Shared rules for every AI client working in this repository (Codex reads this file; Claude Code imports it from
`CLAUDE.md`). The workspace rules in the shared infrastructure (`%USERPROFILE%\workshop\infra\AGENTS.md`) apply
too; its security and privacy rules always win.

- **Purpose:** Workshop AI, Stage 1: a local command-line tool (`wai`) that runs one task with one AI client, saves
  a verified task state in the project's own repository, resumes it in a new session, and builds a manual handoff
  package for another client. Specification: `docs/stage-1-spec.md`. Product vision: the infrastructure
  repository's `docs/workshop-ai-product-vision.md`.
- **Stage:** local POC.
- **Commands:** tests `python -m unittest discover -s tests`; run `python -m workshop_ai --help` or `wai.cmd`.
- **Constraints:**
  - Python 3 standard library only; no background processes; no network access.
  - The tool never starts a client non-interactively (`claude -p`, `codex exec`), never launches Codex, never runs
    git commands that write, and never touches credentials.
  - Every approval needs a person at a terminal; never add a flag that skips one.
  - Never write project state into the shared infrastructure repository.
- The user is a trader: report outcomes, not code explanations; reply in English.
