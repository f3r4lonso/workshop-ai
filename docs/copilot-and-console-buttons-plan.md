# Copilot CLI client and client console buttons — plan

> **v2 note (2026-10-20):** Part A (Copilot as an engine) moves to the v2 engine registry (`infra/docs/workshop-ai-v2/engines.md`); the VS Code items of Part B are paused; B1 `wai console` is kept.

Status: decisions taken by the product owner, 2026-10-18; Copilot CLI installed on the maintainer's machine
(2026-10-18, sign-in by the user pending); nothing else here is built. Next: the user signs in (`copilot`, then
`/login`); then part A step A1 (client guide), after E1 is committed. Spec:
`docs/vscode-extension-spec.md` (§3.3 adapters, §8.4 terminals, §8.9 approval path, §10 roadmap). Evidence labels as in
the spec.

## Decisions (product owner, 2026-10-18)

1. **Copilot: GitHub Copilot CLI first.** Workshop AI adds a `copilot` client adapter (a terminal client like Claude
   Code and Codex). Copilot Chat inside VS Code (a `@workshop` chat participant, handing a task to Copilot Chat) is
   not in this plan. A Copilot-style chat panel built into the extension is rejected: it would need network access,
   send file content to a model provider and handle provider sign-in, which the project rules forbid.
2. **Console buttons ask for approval every time.** A plain client console (no task) is a client launch and needs A1
   like any other; no "skip approval" option.
3. This plan is written down; the open register items below go to vision §17.11 (infra repository) when the owner
   approves an edit there.

## Facts used

- Copilot CLI is started as `copilot` in the project folder; first use in a folder asks the user to trust it; `-p` /
  `--prompt` runs non-interactively; `--agent=<name>`, `--continue`, `--resume`; `--allow-all` / `--yolo` grants all
  tool permissions; `/add-dir` loads `.github/skills` and `.github/agents` from a folder; reads
  `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md` and `AGENTS.md`; signs in with
  `/login` or `copilot login`; config in `~/.copilot` (`COPILOT_HOME`). Documented:
  <https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli> and
  <https://docs.github.com/en/copilot/reference/cli-command-reference>, 2026-10-18.
- `copilot --help` (1.0.98) lists `-i, --interactive <prompt>` ("Start interactive mode and automatically execute
  this prompt") and `--add-dir <directory>` (Observed, 2026-10-18). R10 still needs the docs check and one Observed
  start with the brief message before A5.
- Copilot CLI 1.0.98 installed with `winget install GitHub.Copilot` as a portable `.exe` (not a `.cmd` shim) in
  `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GitHub.Copilot_Microsoft.Winget.Source_8wekyb3d8bbwe\`, added to the user
  PATH (Observed, 2026-10-18). GitHub lists PowerShell 6+ as a Windows prerequisite; only Windows PowerShell 5.1 is
  present (Observed).

## Rules that apply unchanged

- Never `-p`/`--prompt`, `--allow-all` or `--yolo`: interactive sessions only, approvals stay with the person.
- Never read `~/.copilot`, `COPILOT_GITHUB_TOKEN`, `GH_TOKEN` or `GITHUB_TOKEN` (EXT-02; infra `SECURITY.md`).
- The extension never writes to a terminal (EXT-04); commands ignore caller-supplied paths and client ids (EXT-07).
- The WinGet install is a `.exe`; an npm install would be a `.cmd` shim, to which the J3 `.cmd` rule applies (refuse
  arguments containing `" & | % ^ < >`).

## Part A — Copilot CLI adapter

| Step | Content | Files / areas | Verification |
|---|---|---|---|
| A1 | Client guide: install, sign-in, trust prompt, how shared rules and skills reach it | infra `clients/copilot-cli/README.md` (infra repo; owner approval) | read-through |
| A2 | `copilot` as a task client and **handoff target only** (manual steps, like Codex today) | `workshop_ai/formats.py`, `workshop_ai/clients.py`, `tests/` | unit tests; one manual handoff Observed |
| A3 | Extension detection: `copilot` in `CLIENT_IDS`, setting enum, Clients view | `vscode-extension/src/clients.ts`, `package.json` | unit tests; EXT-01 marker test with a fake `copilot.cmd` |
| A4 | Shared skills and agents: link `infra/skills` and `infra/agents` into a layout Copilot loads (`.github/skills`, `.github/agents`), via the adapter script | infra `scripts/codex-adapter.py` or a sibling (infra repo) | Copilot `/env` lists them (Observed) |
| A5 | **Launchable** only after R10 and R11 below are closed | `workshop_ai/clients.py` start command | J3 Observed with Copilot CLI |

## Part B — console buttons (in E2)

| Step | Content | Files / areas | Verification |
|---|---|---|---|
| B1 | `wai console <client>`: shows A1 (client, folder, exact command) and starts a plain interactive session, no task | `workshop_ai/cli.py`, `workshop_ai/clients.py`, `tests/` | unit tests; refusal when not confirmed or not found |
| B2 | Console button per client row in the Clients view (inline, `$(terminal)`), only when the client is confirmed and found | `package.json` menus `view/item/context`, `src/views.ts` | Observed |
| B3 | "Start" / "Resume" buttons per task row (E2 as planned) | `package.json`, `src/extension.ts` | J3 Observed with Claude Code |
| B4 | Launch: a visible terminal named `Workshop AI: <client>` or `Workshop AI: <task-id> (<client>)`, created with `shellPath`/`shellArgs`, `cwd` = project root, `isTransient`; on the fallback path it runs `wai console|start|resume`, which asks A1; modal M only after the §8.9 verification items pass | `src/terminals.ts` (new) | EXT-04 grep and `sendText` spy; EXT-07 test |
| B5 | Track own terminals by object identity; close only own terminals, only after a saved checkpoint and confirmation (AX-3) | `src/terminals.ts` | unit tests; Observed |
| B6 | Optional status-bar entry "Workshop AI: open console" with a client pick | `src/extension.ts` | Observed |

Order of clients behind the buttons: Claude Code (E2), then Gemini CLI (already planned), then Copilot CLI (A5),
Codex after R8.

## Open items for vision §17.11 (proposed numbers)

| Id | Question | Default |
|---|---|---|
| R10 | Documented form of starting Copilot CLI **interactively** with a first message, and of adding the infra `clients` folder at start-up | verify in GitHub docs and `copilot --help` before A5 |
| R11 | GitHub terms: launching the unmodified Copilot CLI from an extension under the user's own sign-in (as R4 for Anthropic/OpenAI) | record with URL and date before A5 |
| R12 | Copilot agent mode in VS Code can run commands in integrated terminals and could answer a `wai` prompt (§8.4); it also raises the risk when Copilot Chat is installed | approvals only through M or X (§8.9); state it in the first-run notice |

## Risks

- Copilot's trust prompt on first use in a folder is a client prompt, not a Workshop AI approval; the extension never
  answers it (Inference: it appears in the client terminal like any other client input).
- Skills layout for Copilot (A4) may differ from Claude Code and Codex; if linking needs files inside each project,
  that touches projects and needs its own approval.
