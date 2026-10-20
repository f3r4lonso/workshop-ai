# Stage 1 completion — plan (foundation task, Phases 5–6, Gates C and D)

> **v2 note (2026-10-20):** folded into increment V1 of the proposed Workshop AI v2 (`infra/docs/workshop-ai-v2/roadmap.md`). Still a draft awaiting approval.

Status: draft for the product owner's approval, 2026-10-19. Revised the same day after a `prompt-reviewer` review
(3.4/5, 6 High findings, all fixed here). Executes the remaining part of the infra task
[`workshop-ai-product-foundation`](../../../infra/tasks/projects/workshop-ai/workshop-ai-product-foundation.md) (rev. 2). It does not
change that task's gates or acceptance criteria. The single exception is decision P0, which needs your approval and
is recorded in the handover. Spec: [`stage-1-spec.md`](stage-1-spec.md). Evidence labels as in the vision.

## 1. Where the task stands (checked 2026-10-19)

| Phase | State | Evidence |
|---|---|---|
| 0–1 Re-verify, gap analysis, Gate A | done 2026-10-17 | vision §17 items 1–9 |
| 2 Vision revised | done | infra `docs/workshop-ai-product-vision.md` v1.1 |
| 3 Stage 1 spec, Gate B | done 2026-10-17 | `docs/stage-1-spec.md` (Status line) |
| 4 Build | done; the tool repository has 3 commits and the sandbox 1 commit plus tag `pilot-base` | 50 unit tests pass (Observed 2026-10-19 on the working tree, which includes the uncommitted E1 `--json` change). The brief says "leave all changes uncommitted" and only the sandbox commit is a recorded exception (spec §12), so **the approval for the tool commits is not recorded**: you confirm it at Gate D and the handover notes it |
| C Codex (optional) | **not decided** | Codex CLI 0.163.0 is on PATH (Observed). Gate C covers "installing and authenticating", but no approval record for the install was found: you confirm it at Gate C. Sign-in and client guide §5 not run |
| 5 Validate and measure | **not started** | `workshop-ai-sandbox/pilot-results/results.md` is an unfilled template; no run worktrees exist |
| 6 Handover | **not started** | infra `docs/workshop-ai-stage-1-handover.md` does not exist |
| D Commits | **open** | — |

Facts that changed since Gate B and affect the pilot:

1. **Shared agents now load from the `workshop` Claude Code plugin** (Observed: `claude plugin list` shows
   `workshop@workshop-local`, enabled, user scope). The old `infra\clients\.claude` folder is empty. `wai`
   (`clients.py`, start and handoff steps), spec §6 and §11.2, the project `CLAUDE.md`, the sandbox
   `pilot/user-script.md` and `vscode-extension-spec.md` §3.3/§3.5 still use `claude --add-dir "<infra>\clients"`.
   That flag now adds no agents and gives the session read access to the infra client folder for no benefit. The
   brief's §2 precondition (junctions) can no longer hold as written: see P0.
2. **gitleaks is on PATH** (Observed). Packages get the gitleaks check (spec §8 item 4). The A2 `reviewed` step is
   not asked, so the script lines that say "type `reviewed`" (C.8, E.4) are wrong: typing it at a y/N prompt would
   decline the release.
3. **The E1 extension work is uncommitted in the same repository.** The pilot must measure a known `wai` version.
4. **A stray empty task `321`** (2026-10-18) sits in the main sandbox's untracked `.workshop-ai/`.

## 2. Decisions needed before the pilot (asked one at a time)

| Id | Decision | Recommended default | Why |
|---|---|---|---|
| P0 | Precondition | **replace the junction check with "the `workshop` plugin is installed and enabled"**; acceptance item 1 is reported against the new check, and the change is recorded in the handover §4 | the junctions were retired on purpose |
| P1 | Pilot `wai` version | **commit E1 first** (under the E1 plan's own gate), then pilot on that commit; record `git rev-parse HEAD` in `results.md` | the pilot measures a fixed, reproducible tool |
| P2 | Start-command fix (fact 1) | **drop `--add-dir`; warn (never block) when the plugin is missing** | smaller data surface; agents still load |
| P3 | Gate C (Codex) | **approve**, including confirming the install already done | without it acceptance item 7's Codex part stays Not run |
| P4 | Stray task `321` | **delete it** after you see it | noise in status and resume checks |
| P5 | Pilot results in git | **commit `results.md` in the sandbox at Gate D** (force-add the ignored file) | the vision §16 Stage 1 exit requires "results committed" |

## 3. Plan

### Step 1 — Prepare (agent; about 1 hour; no client runs)

1. P1: E1 review and commit through the E1 plan's gate (separate approval, not part of this plan).
2. P2 fix, test first. `claude_command` returns `[claude]` and warns if `claude plugin list` has no enabled
   `workshop` plugin. Then update `handoff_steps`, spec §6 and §11.2 (dated note), `vscode-extension-spec.md` §3.3
   and §3.5, and the project `CLAUDE.md`.
3. Sandbox script, edited **before** any run (the "do not edit `pilot/`" rule applies during runs). Remove
   `$shared` and `--add-dir`, remove the `reviewed` steps in C.8 and E.4, and set the order line to the Step 3
   order. **The tag `pilot-base` is not moved.** The edited script is an uncommitted change in the main sandbox
   folder, while run worktrees keep the `pilot-base` copy of `pilot/`. Always read the script from the main folder.
   Committing the edit is a Gate D item.
4. Tests: full suite passes; new tests check that the argv has no `--add-dir`, and that a missing plugin warns and
   does not block.
5. Dry run, without a client and without approvals. The integration test runs the journey with the prompt function
   replaced (as the existing tests do; spec §7 refuses approvals without a real terminal). It is followed by a real
   `wai handoff create` in a throwaway worktree, to see gitleaks run on a package. The approval steps (A1, A2, A3)
   are first seen for real in your T2 run.
6. P4 cleanup; write the `wai` commit and date at the top of `results.md`.

Done when: tests pass, the dry run result is recorded (Pass or Fail), and the script matches the tool.

### Step 2 — Gate C (you run it, the agent checks; about 15 minutes)

In a normal terminal you run `codex login status` (and `codex login` if needed), then the client guide §5 checks.
The agent cannot drive an interactive Codex session, and `codex exec` is not allowed (vision §17.2). The agent
records the results in the guide's matrix row. A check that ran and failed is **Fail** with the reason; **Not run**
only if sign-in was not done.

### Step 3 — Pilot runs (you; about 3–4 hours in total)

Order: **T2 tool → T1 baseline → T1 tool → T2 baseline → T3 baseline → T3 tool.** T2 with the tool runs first
because it alone covers the journey, resume and handoff checks (acceptance items 5–7). That way the minimum Stage 1
evidence exists even if you stop early. Within each task the order is the same as in spec §11.2; only the order
across tasks changes, and that is stated as a limitation. Each run fills one row of `results.md`.

Sittings: (A) T2 tool + resume + Codex package check (script part D); (B) T1 both + T2 baseline; (C) T3 both.

### Step 4 — Verify each run's files (agent, after each sitting)

For each run, the agent re-checks the criteria in the worktree (runs the tests, limits the diff to the allowed
folders). It reads the task and state files, and for packages it checks the manifest hashes, the gitleaks result
and that the file list holds only `handoff.md`, `manifest.json` and `context/`. The resume and Codex answers are
compared with the recorded `Decisions`. Each item is marked Pass, Fail or Not run. A run is **Observed** only after
its files are checked. Worktrees stay until Gate D.

### Step 5 — Handover (agent; about 2 hours)

1. Update vision §16 with the Stage 1 result, and add a Documented provider-terms recheck only if a term changed.
2. Write infra `docs/workshop-ai-stage-1-handover.md` with the brief's §8 seven sections. It is public: outcomes
   only, no user paths, no private file listings. Section 4 records P0, and section 1 records the commit and install
   confirmations from §1.
3. `prompt-reviewer` on the final vision and the handover. Fix the findings and **re-run until a run reports no
   High finding**; cite that run.
4. Checklist items 1–13. User-path grep and gitleaks run in all three repositories. Internal links are checked by
   a script. For item 8, infra `git status` must show the expected files: the handover, the vision, the task file,
   `docs/catalogues/tasks.md`. Any other change already present before this step (for example `docs/images/`) is
   listed as pre-existing and not touched.
5. Task `Status:` → `completed (<date>)`; catalogue row, `INDEX.md` and `WORKSHOP-CONTEXT.md` updated.

### Step 6 — Gate D (you approve a commit plan per repository; never pushed)

| Repository | Proposed commits |
|---|---|
| workshop-ai | "Start Claude Code without --add-dir; rely on the workshop plugin" (P2, tests, spec notes) |
| workshop-ai-sandbox | "Update the pilot script for the workshop plugin"; "Add Stage 1 pilot results" (P5) |
| infra | "Add the Workshop AI Stage 1 handover and close the foundation task" |

The worktrees are removed after the commits, with your OK.

## 4. Risks

| Risk | Handling |
|---|---|
| Runs use much of your Claude plan quota | separate sittings; stop after any run; T2 tool first secures the minimum evidence |
| `/cost` is not meaningful on Pro/Max | record what it shows or N/A; no money conversion |
| Learning effect, n = 3 × 2, one user, not blinded | stated as limitations; no improvement is claimed from this sample |
| P2 breaks start where the plugin is missing | warning only; a unit test covers it |
| Codex sign-in or §5 fails | Fail or Not run with the reason; the Stage 1 exit is still reachable on Claude Code |

## 5. What finishing this unlocks

- The foundation task is completed, which is the precondition of
  [`stage-2-context-store-plan.md`](stage-2-context-store-plan.md).
- Extension E2 (launch) and the Copilot plan build on a committed, measured `wai`.
