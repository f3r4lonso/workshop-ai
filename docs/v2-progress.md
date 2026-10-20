# Workshop AI v2: progress

Progress record for the task `infra/tasks/projects/workshop-ai/workshop-ai-v2-unified-app.md`. Requirements:
`infra/docs/workshop-ai-v2/`. One row per increment; each run reads this first and continues with the first
increment that is not accepted.

| Inc. | State | Gate A | Gate B | Tests | Open items |
|---|---|---|---|---|---|
| V0 | done (2026-10-20); awaiting owner acceptance | 2026-10-20 (decisions approved) | — | `wai` 50 OK; UI 104 OK, 1 skipped (no code changed) | Fix 2 code part and the commits move to V1 |
| V1 | built (2026-10-20); awaiting commit approval, pilot and owner session | 2026-10-20 | — | 180 OK, 1 skipped (merged repo) | Commit deferred by the owner (2026-10-20), so the pilot waits for a commit; 15-minute first-use session |
| V2 | not started | — | — | — | — |
| V3 | not started | — | — | — | — |
| V4 | not started | — | — | — | — |
| V5 | not started | — | — | — | — |
| V6 | not started | — | — | — | — |
| V7 | not started | — | — | — | — |

## Reports

### 2026-10-20: V0 documents

The v2 document set was written from four read-only reviews (Workshop AI documents and code, UI documents and code,
engine audit, UX research), then reviewed by `prompt-reviewer` (task brief: 3.0/5, fixes applied) and
`security-reviewer` (design: 3 critical, 5 high, 4 medium, 3 low; all recorded as binding requirements in
`architecture.md §8`). Status banners were added to the superseded or paused documents. No code was changed. Not
verified: nothing was run end to end; no owner usability session.

### 2026-10-20: V0 decisions and cleanup

- **Decisions:** the owner approved D-V2-01…09 as recommended (one answer covering all nine, offered as an option
  alongside one-at-a-time review). Recorded in `product-vision.md §6`; v2 documents set to approved.
- **Rules files (M5):** `workshop-ai` `AGENTS.md`/`CLAUDE.md` now allow the loopback app server (D-V2-04), owner-started
  engine runs at verified levels after R7 (D-V2-05/06) and allowlisted writes with versions (D-V2-07); the terminal
  approval rule is unchanged (C1 needs its own decision). UI `AGENTS.md`/README: merging into v2.
- **document-review §4 fixes:** 1 banners present; 2 `--add-dir` removed from stage-1 spec, sandbox user script,
  inventory, reading-assistant page and project `CLAUDE.md` (code in `clients.py`, the test and `vscode-extension-spec`
  left for V1 / paused); 3 gitleaks/`reviewed` steps corrected; 4 foundation task §2 dated update; 5 R10–R12 added to
  the vision register, extension spec header says R1–R12; 6 web-architecture §3–§4 and UI README corrected; 7 UI brief
  marked superseded (file name kept so links work; catalogue and INDEX updated); 8 reading-assistant page says local
  Ollama, not Gemini; 9 Copilot/Gemini matrix, client-list contract, ai-architecture §9 and seven client rows in the
  inventory; 10 counts reconciled (26 shared + 3 personal agents, 31 skills, 26 Codex wrappers; dated observation
  records left as history); 11 stray sandbox task `321` and the UI `.preview-edge/` folder deleted with owner approval.
- **Not done:** nothing committed (Gate C). `ai-environment-auditor` was not run; counts were checked by direct listing.

### 2026-10-20: V1 one app, every engine visible (built; Gate B pending)

- **What the owner can do:** start the single app with `INICIAR.cmd` in `applications/workshop-ai`. It has the seven
  sections of ux-design §2: Conversar holds the agent chains, Historial is a placeholder until V2, and the Lector
  stays beside the lists. **Motores** shows all ten engines with level, installed state, session ("desconocida"),
  goal, what unlocks the next level, Probar (version check only), Abrir consola (the four console engines), Ver guía
  and Web oficial.
- **Built:**
  - Code merge: the UI's `server/`, `web/`, tests and `INICIAR.cmd` were copied into this repository; the old UI repo
    is kept as history with a banner. The legacy WinForms `src/` was not copied.
  - Engine list: `workshop_ai/engines.json` with validation in `engines.py`. `wai`'s clients and the server's console
    allow-list come from it.
  - `wai` drops `--add-dir` and warns, without blocking, when the `workshop` plugin is missing.
  - New `procutil.run_bounded`, which ends the whole process tree on timeout.
- **Code review (`code-reviewer`):** no critical or high findings; 2 medium and 6 low. Fixed:
  - the plugin check runs only a `claude` found on an absolute PATH folder outside the project and the current
    folder;
  - version and plugin checks no longer block when a `.cmd` wrapper's child holds the output;
  - `wai_client` is limited to claude/codex;
  - a broken registry gives a clear error;
  - the registry is loaded once, so the cards and the launch list agree;
  - stricter field checks;
  - more tolerant plugin-list parsing.
  Not changed: Probar may run `dsh --version` (detection at every level, architecture §6); `/api/engines/check`
  accepts no-Origin POSTs with the token, like `/api/launch`.
- **Tests:** 180 OK, 1 skipped (symlink not permitted). That is the 154 existing tests plus 26 new ones covering the
  registry, plugin parsing, bounded runs, the trusted path and the server engine routes. `npm run build` OK.
- **Manual check (browser, 2026-10-20):** the seven sections, Motores with ten cards, Probar on Claude
  (2.1.304), Conversar and Agentes y Skills all render; no app console errors. Real Probar results: claude 2.1.304,
  codex 0.163.0, gemini 0.64.0, copilot 1.0.101 (updated since the audit), dsh 0.2.1-rc.2; ollama not installed.
  Plugin check: enabled.
- **Not done / not verified:**
  - nothing committed;
  - the sandbox pilot has not been run;
  - no owner first-use session;
  - no provider received any content (0 engine runs);
  - UI docs (`web-architecture.md` etc.) stay in the old repo as records;
  - `workshop-ai.code-workspace` (VS Code, paused) still passes `--add-dir`.
