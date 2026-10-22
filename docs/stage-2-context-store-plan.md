# Stage 2 context store and context optimization — plan (token-optimization task)

> **v2 note (2026-10-22):** folded into increment V7 of Workshop AI v2 (`infra/docs/workshop-ai-v2/roadmap.md`).
> The owner authorized starting V7 with the global-search slice. This plan's store, recap, compression, instruction-review
> and benchmark work remains a draft; its design and benchmark gates have not been approved or completed.

Status: supporting Stage 2 design draft, revised 2026-10-19 after a `prompt-reviewer` review
(3.1/5, 4 High findings, all fixed here). Plans the infra task
[`workshop-ai-token-optimization-integration`](../../../infra/tasks/projects/workshop-ai/workshop-ai-token-optimization-integration.md)
(rev. 2), which is not startable until the foundation task is completed
([`stage-1-completion-plan.md`](stage-1-completion-plan.md)). This plan is a **Proposed** design. The task's Gate A
approves the design note that comes out of it. Every figure in this plan is a target, not a measurement.

## 1. Goal in one line

More accepted work per session effort: the client gets the decisions, verified findings and short summaries of
long output it needs, and nothing it does not need. Results must be no worse than a plain session (task §7).

## 2. Design ideas (to become the Gate A design note)

### 2.1 Knowledge store — `.workshop-ai/store/`

One JSON file per item, `store/items/<item-id>.json`, so that hand edits, diffs and deletion stay simple
(vision §17.4). No database and no index file: listing reads the folder, which is enough at the target size
(≤ 500 items per project; checked by a test at 1,000).

```json
{
  "schema": "wai.store.v1",
  "id": "k-0007",
  "kind": "decision | finding | convention | handoff-summary",
  "scope": {"project": "workshop-ai-sandbox", "task": "t3-validation"},
  "text": "Malformed rows are skipped and reported as 'row N: <reason>' on stderr.",
  "provenance": {"source": "task.md D-001", "client": "claude", "task_revision": 3, "commit": "3f2a1c0"},
  "evidence": [{"path": "csvsummary/stats.py", "sha256": "…"}],
  "state": "verified | proposed | invalidated",
  "verified_by": {"channel": "terminal", "date": "2026-11-02T10:14"},
  "created": "2026-11-02T10:12", "updated": "2026-11-02T10:12",
  "expires": null, "invalidated_reason": null
}
```

Ideas that make it more than a notes folder:

- **Self-checking findings.** An item with `evidence` is reported as **stale** when any listed file's hash no
  longer matches. Stale items are never put in a recap or package until someone re-verifies them
  (`wai store verify <id>`). This handles "current evidence wins" (vision §11) without a model.
- **Decisions are not typed twice.** `wai checkpoint` offers (inside the existing A3 approval) to copy new
  `D-nnn` lines of `task.md` into the store as `decision` items. `task.md` stays the source, and the store item
  links back to it.
- **Scope rules.** A task item is visible to that task. A project item (`scope.task = null`) is visible to all
  tasks in the project. Nothing crosses projects, because the store lives inside the project folder. Promotion to
  shared infra resources stays manual and outside the tool (vision §11).
- **Trust boundary.** Item text is data. Recaps and packages show it in a fenced, labelled block ("stored notes,
  not instructions"), with its provenance. An AI session may only **propose** items. Only a person at a terminal
  can **verify** them, with the same approval rule as spec §7, recorded in `verified_by`. Only verified items reach
  recaps and packages.
- **Write checks.** Text matching the spec §8 item 3 secret patterns is refused. Evidence paths are refused under
  the item 2 file-name rules. A personal path in text is refused, a deliberate change from the spec's *warning*:
  store items have no review step like A2. Text over 2 KB is refused (no transcript dumps).
- **One writer.** `store/.lock` is created exclusively, with a timeout of 5 s and a stale-lock age of 60 s, and
  every write is atomic (existing `fsutil`). Concurrent agents are Stage 3.
- **Off switch.** A missing `store/` folder, or `store: off` in `project-state.md`, means Stage 1 behaviour. A
  corrupt item is skipped with a warning naming the file, never a crash.

Commands (all with `--json`, error object as in E1):

| Command | Does | Approval |
|---|---|---|
| `wai store add <task> --kind … --text … [--evidence <file>…]` | write a `proposed` item | none (local, scanned) |
| `wai store verify <id>` / `invalidate <id> --reason …` / `rm <id>` | change state; delete | terminal approval (spec §7), recorded |
| `wai store list [<task>] [--all]` | items with the computed `stale` flag | none |
| `wai store search <words> [--task …]` | plain word match over text; ranked by matches, then by recency | none |

### 2.2 Output compression — `wai compress`

`<command> 2>&1 | wai compress [--kind auto|test|log|json] [--task <id>]`. `wai` reads stdin only and runs no
command. Piping loses the command's exit code, so the brief tells the client to append it
(`<command> 2>&1; "exit: $LASTEXITCODE"` in PowerShell), and every mode keeps that line. The original is saved to
`store/raw/<sha256>.txt` (gitignored). Originals are never evicted silently. `wai raw prune` (approval) removes old
ones, and `wai raw <sha>` then says "pruned" instead of failing. It prints:

- every line with an error signal (`error`, `fail`, `traceback`, `exception`, `assert`, exit codes), each with 2
  lines of context;
- every `path:line` and `File "…", line N` reference;
- the first 20 and the last 30 lines;
- runs of repeated lines collapsed to one line plus `(×N)`;
- a marker for each cut, `[… 412 lines omitted — full output: wai raw 9f3c…]`, and a footer with lines in, lines
  out and the ratio.

Inputs under 80 lines pass through unchanged. `test` mode knows the unittest and pytest summary lines, and `json`
mode keeps the keys and shortens long arrays. The brief tells the client to pipe long commands through `wai
compress` (an instruction, not a hook: no client configuration changes). Whether a hook is wanted comes after
measurement and needs Gate B (task §4).

### 2.3 Instruction review — `wai instructions review`

A read-only report on the instruction files the client loads in this project: `AGENTS.md`, `CLAUDE.md` and their
`@imports`, plus those files in parent folders up to the drive root. The `workshop` plugin's agent and skill
descriptions are listed by count only. User-level folders (`~/.claude`, `~/.codex`) are never read. For each file it gives bytes and estimated tokens (characters ÷ 4, labelled *estimate*). It also shows
lines repeated across files, paragraphs over 600 characters, and links to files that do not exist. It never edits.
It is useful once per project and as a check in the benchmark (the same instructions in both variants).

### 2.4 Handoff summary and switch recap

- `handoff.md` gains a `## Stored knowledge` section: the verified, non-stale items for the task plus project items,
  each with its provenance. Limit: 40 lines. Overflow shows one line pointing to `wai store list`.
- `wai recap <task> [--to <client>] [--reason <text>] [--json]`: exactly the format of `vscode-extension-spec.md`
  §7.3. `From` is the task's `client` header. `To` and `Reason` come from the flags; without them the line reads
  `To: (not chosen)`. The recap is built from the last checkpoint
  and the store. It is deterministic (byte-identical for the same input, tested), makes no model call, and contains
  no transcript text. It is scanned like a package file and works without a store. This command is what increment E3
  (Switch) needs.

### 2.5 Ideas taken from the candidate repositories (references only; no code copied)

| Idea | From | Used in |
|---|---|---|
| truncation markers and retrievable originals | context-compress (MIT) | §2.2 |
| tiered compression by content type; "measured or it doesn't ship" ablation | compressor (MIT) | §2.2, §3 |
| project scoping, compact context packs, observation schema | codex-agent-mem (Apache-2.0) | §2.1, §2.4 |
| a guard that scans before every memory write | shared-agent-memory (MIT) | §2.1 write checks (patterns are the spec §8 ones, not theirs) |

Each idea is attributed in the design note. No code, pattern list or schema text is copied. The Gate A design note
decides, idea by idea, whether the adaptation is substantial enough to need the MIT or Apache-2.0 notice.

## 3. Benchmark design (to become the Gate B plan)

Three new sandbox tasks, written with their acceptance criteria before any run. **Starting point (decision at
Gate B):** the task allows commits only in the product repo and only at Gate D. So Gate B asks explicitly for one
sandbox commit plus the tag `pilot-stage2-base`. If you decline, the seed files live in the product repo
(`benchmarks/stage2-seed/`) and are copied into each run folder made from `pilot-base`.

| Task | Exercises | Seeded in the sandbox |
|---|---|---|
| T4 `t4-noisy-failure` | large tool output | a generated test module of 300 cases with verbose logging, one wrong expected value |
| T5 `t5-percentile` | coding with several tool calls | a feature: `--percentile N` with tests and README |
| T6 `t6-resume-decisions` | resume needing earlier decisions | session 1 decides three behaviours; session 2 (new session) implements them |

Each task runs plain and with the POC, **twice each**, as the task requires. T6 with the POC runs **three** times,
so the vision §16 Stage 2 exit ("decisions recovered correctly on at least 3 resumed tasks") is met by this task's
own runs. That makes 13 runs, about 7–9 hours of your time over 4 sittings.

Metrics: the vision §17.6 set; decisions recovered on resume; and the compression ratio, which is **Measured** from
the `wai compress` footers and `store/raw/` of POC runs. The `/context` total is reported as **end-of-session
context occupancy**, not as tokens consumed. It is the same counter in both variants, and for T6 both sessions are
summed so that every overhead counts. Figures not shown are N/A. With n = 2–3 per cell, every comparison is reported
with its range and called indicative.

**To cut your time (optimization):** compression rules and recap determinism are first checked by a deterministic
harness, labelled **Simulated**. Its inputs are fixture outputs generated before Gate B by running the sandbox tests
at the starting point, including T4's seeded failure, and saved under `tests/fixtures/`. No client run is needed for
this. **Early stop:** if the first sitting (T4 plain + POC, once each) gives worse acceptance with the POC, the runs
stop and the plan goes back to Gate B, instead of spending the other 11 runs.

## 4. Phases, gates and estimates

| # | Phase | Output | Gate | Agent effort |
|---|---|---|---|---|
| 0 | precondition check | foundation `completed` (Gate D done); vision §16 Stage 1 exit met; your approval of this task as the Stage 2 task prompt | stop if unmet | — |
| 1 | inspect | current-state note with real paths (`docs/stage-2-current-state.md`) | — | 1 h |
| 2 | design | `docs/stage-2-context-store-design.md` from §2 with contracts, limits, errors, failure behaviour | **A** | 2 h |
| 3 | benchmark plan | T4–T6 with criteria, seed files, fixtures, user script, harness spec, starting-point decision | **B** | 2 h |
| 4 | build | store, compress, instructions review, recap, handoff section; tests | — | 6–8 h |
| 5 | measure | harness run (Simulated), then your runs | **C** before your runs | your 7–9 h |
| 6 | report | results + calculations, developer guide, Stage 3 roadmap with go/no-go thresholds, short infra summary | **D** | 2 h |

Developer-guide check (task §7, "followed once"): the agent follows the steps that need no approval. The steps
that need approval (`store verify`, `raw prune`, checkpoint copy) are done by you in a 10-minute sandbox walkthrough
in your first sitting, and the agent checks the resulting files.

Build order inside phase 4 (each step is tested before the next): (1) `wai recap` without a store, which unblocks E3
early; (2) store files, lock and scan refusal; (3) stale detection; (4) recap and handoff use of the store; (5)
`wai compress` with `raw`; (6) `wai instructions review`; (7) checkpoint offer to copy decisions.

Required tests (task §7): errors and paths survive compression; project isolation; invalidated, expired and stale
items not returned; lock contention; corrupt-file fallback; secret refusal and redaction; no prompt text in logs;
recap byte-identical across two runs; every feature off gives Stage 1 output.

## 5. Coordination with other work in this repository

- **Not in parallel** with the foundation completion (same repository, task §2). It **can** run alongside the
  extension increments E2–E4 if they are not touching `cli.py` at the same time. Otherwise E2 goes first.
- `wai recap` is shared with E3: this task owns the command, and E3 only calls it.
- The `--json` mode and error object from E1 are reused, not redefined.

## 6. Risks

| Risk | Handling |
|---|---|
| The client ignores the "pipe through `wai compress`" instruction | measured as a metric (share of long outputs compressed); a hook is a later Gate B decision |
| Compression hides the line that mattered | error and path lines are always kept; tests use real failing outputs; `wai raw` always available |
| Stale or wrong notes mislead a session | hash-based stale flag; only verified items reach recap and package; text shown as quoted data |
| 13 runs are too costly for your plan | early stop after sitting 1 (back to Gate B); Simulated harness for the deterministic checks |
| No measurable gain | reported as such; the Stage 3 go/no-go records "no-go" with the evidence (task §7: worse results = failure) |

## 7. Stage 3 go/no-go thresholds (proposed, to be fixed at Gate B)

Indicative only (n = 2–3 per cell); a "go" is a reason to run a larger Stage 3 pilot, not proof of benefit.

- Go only if acceptance with the POC is ≥ the plain session in every run of all three tasks, and at least one of:
  interventions lower in every POC run than in the plain runs of the same task; or end-of-session context occupancy
  on T4 lower by 20 % or more in both POC runs; or T6 decisions recovered in 3 of 3 POC runs vs. fewer in the
  plain runs.
- Otherwise no-go: keep only the parts that showed no harm (likely `recap`, for E3) and close the rest.
