# VS Code extension — increment E1 (Shell): requirements and plan

> **v2 note (2026-10-20):** paused with the VS Code extension (proposed Workshop AI v2, `infra/docs/workshop-ai-v2/`, decision D-V2-03).

Status: approved by the product owner, 2026-10-18 (engineering-lifecycle stages 1–2). Spec:
`docs/vscode-extension-spec.md` (§10 row E1). Toolchain decision: `docs/adr/0001-extension-build-toolchain.md`.

## Requirements

Goal: a locally installed VS Code extension that detects the user's AI clients, reuses the existing infra clone, and
lists, creates and adds context to tasks through `wai`.

In scope: client detection (EXT-01) and confirmation (AX-1); infra location and reuse (J1 step 4); `wai` check
(J1 step 6, EXT-09); Tasks view, `wai init` offer, New task, Add context (J2); Restricted Mode (§8.6); J7a, J7c, J7f;
`--json` output in `wai` for the commands E1 calls.

Out of scope (owner decisions 2026-10-18): cloning infra (AX-2) — moves to E2 with the modal-dialog verification
items (§8.9), because AX-2 may use the modal only after they pass; launching clients (E2); switch and recap (E3);
usage warnings (E4); anything automatic (E5); packaging or publishing; automated tests inside a real VS Code
(`@vscode/test-electron` downloads VS Code; not approved).

Acceptance criteria:

1. Given an untrusted folder, when VS Code opens it, then the extension contributes nothing active and says why.
2. Given a fake `claude.cmd` on PATH that writes a marker when run, when detection runs, then Claude Code is listed
   and no marker exists (EXT-01).
3. Given `workshopAi.infraPath`, else `WORKSHOP_AI_INFRA`, else `%USERPROFILE%\workshop\infra`, when the folder is a
   git repository with `clients/` and `tasks/`, then it is reused; otherwise the user is told and nothing is cloned.
4. Given an initialized project, when the Tasks view loads, then it lists the same tasks, clients and statuses as
   `wai status --json`.
5. When the user runs New task with an id and a confirmed client, then `wai task new <id> --client <c> --no-edit`
   runs and `task.md` opens in the editor.
6. When the user runs Add context on explorer files, then `wai context add` records them.
7. Given a project with a fake `workshop_ai/__main__.py` and a workspace setting for `workshopAi.waiPath`, when any
   command runs, then the real `wai` runs and no marker appears (EXT-09).
8. Given `wai`/Python missing or a client missing, then the matching actions are disabled with a message (J7a, J7c);
   given a non-zero `wai` exit or invalid JSON, then its meaning and message are shown and nothing is retried (J7f).
9. A source grep for `sendText` and `shellIntegration` in `vscode-extension/` finds nothing (EXT-04).
10. Stage 1 tests still pass; new `--json` outputs have unit tests.
11. J1 (without clone) and J2 are Observed on `workshop-ai-sandbox` in an Extension Development Host.

## Plan

| # | Step | Files / areas | Verification | Rollback |
|---|---|---|---|---|
| 1 | `--json` on `status`, `resources`, `context`, `task new`; JSON errors `{"error": {...}}` | `workshop_ai/cli.py`, `tests/` | new unit tests; full suite | revert (additive) |
| 2 | Scaffold: manifest (Restricted Mode, command/view activation, machine-scoped settings), tsconfig, `vscode.l10n` strings | `vscode-extension/` | `npm run compile`; manifest test | delete folder |
| 3 | `wai` runner: `<python> -E -s -m workshop_ai --project …`, cwd = product folder, `execFile`, exit-code mapping | `vscode-extension/src/wai.ts` | unit tests; EXT-09 test | revert |
| 4 | Client detection (PATH × PATHEXT, never runs) and confirmation | `src/clients.ts` | unit tests; EXT-01 marker test | revert |
| 5 | Infra location and validation, reuse only | `src/infra.ts` | unit tests | revert |
| 6 | Tasks view, init offer, New task, Add context, status/messages | `src/extension.ts`, `src/tasks.ts` | unit tests; Observed J1/J2 | revert |
| 7 | Review (`code-reviewer`, `security-reviewer`), EXT-04 grep, report | — | no open blockers | — |

## Next (owner decisions, 2026-10-18, after E1 was built)

1. Finish E1 first: the owner's hand check of J1/J2 (criterion 11), fixes, then the E1 commit.
2. E2 launch buttons: "Start" / "Resume" per task on the J3 fallback launch path (a visible integrated terminal
   running `wai start|resume <id>`; `wai` shows A1). Before it ships: R4 (provider-terms check, Documented with URL
   and date) and R9 (Claude Code IDE integration check). Claude Code only until R8 makes Codex launchable.
3. Gemini CLI as a full provider, in steps, per infra `docs/ai-architecture.md` §8: client guide, `wai` adapter
   (detection, task client, handoff target) and extension detection; launching only after its start form is
   Documented and verified (same rule as Codex, R8). This brings a Stage 5 item forward (vision §16).
4. Copilot CLI as a client, and console buttons per client with an approval on every launch (owner decisions
   2026-10-18): `docs/copilot-and-console-buttons-plan.md`. The buttons join E2; Copilot CLI is installed (1.0.98)
   and comes after Gemini.

Risks: no in-VS Code automated tests in E1, so UI behaviour is Observed by hand; dev packages are pinned and
installed with `--ignore-scripts`.
