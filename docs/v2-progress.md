# Workshop AI v2: progress

Progress record for the task `infra/tasks/projects/workshop-ai/workshop-ai-v2-unified-app.md`. Requirements:
`infra/docs/workshop-ai-v2/`. One row per increment; each run reads this first and continues with the first
increment that is not accepted.

| Inc. | State | Gate A | Gate B | Tests | Open items |
|---|---|---|---|---|---|
| V0 | done (2026-10-20); awaiting owner acceptance | 2026-10-20 (decisions approved) | — | `wai` 50 OK; UI 104 OK, 1 skipped (no code changed) | Fix 2 code part and the commits move to V1 |
| V1 | paused by owner | 2026-10-20 | not accepted | 180 tests run, OK, 1 skipped (rechecked 2026-10-21) | Sandbox pilot and 15-minute first-use session remain unrun |
| V2 | accepted by owner as working acceptably | 2026-10-21 | owner acceptance recorded in current session | 204 backend tests, OK, 2 skipped; 8 parser tests; 11 frontend tests; build passed | Browser/keyboard/responsive and Notepad/Explorer checks were not separately recorded |
| V3 | in progress | Owner requested V3–V6 continuation in current session | pending | — | Persisted chat/chain work must pass security review; only Claude is currently verified for chat; Ollama setup remains open |
| V4 | authorized after V3 | Owner requested V3–V6 continuation in current session | pending | — | Build after V3 |
| V5 | partial owner-requested implementation; not accepted | Agent/skill authoring UI requested directly | pending | 224 backend tests OK, 2 skipped; 11 frontend tests; build and adapter check passed | Built ahead of V4 acceptance; all-client synchronization, security review and live UI acceptance remain open |
| V6 | authorized after V5 | Owner requested V3–V6 continuation in current session | pending | — | Build only within architecture §8 approvals and isolation requirements |
| V7 | in progress (initial global-search slice; not accepted) | Owner requested V7 implementation on 2026-10-22; initial search slice authorized | Stage 2 design and benchmark gates remain pending for the store/recap/compression work | 7 focused backend tests; 232 backend tests (2 skipped); 11 frontend tests; production build passed | Context store, recap, compression, instruction review, benchmark, and owner acceptance remain |

## Reports

### 2026-10-22: V7 global search started

- Implemented the first V7 slice: the global search endpoint covers current eligible document contents, saved
  conversations and prior document versions. Searches are bounded by query length, terms, resource count, result
  count and a 16 MiB read budget; protected paths and expired or scanner-flagged conversations are excluded.
- The UI debounces queries, reports partial results/omitted records, and opens matching documents or saved chats.
  Selecting an older-version result opens that exact version in the existing comparison/restore view.
- Verification: focused global-search tests 7 passed; full backend suite 232 passed, 2 skipped (a transient Windows
  connection-abort on one HTTP test passed in isolation and on the complete rerun); frontend tests 11 passed;
  production build passed; `git diff --check` passed. No browser/keyboard/accessibility session was recorded.
- This is not V7 acceptance. The Stage 2 store, deterministic recap, output compression, instruction review and
  benchmark remain unimplemented; their design and benchmark gates remain pending. No commit or push.

### 2026-10-21: agent and skill authoring preview

- Continued the owner-requested authoring and discovery UI. The combined Agentes y Skills section exposes the guided
  authoring form and browser-mediated GitHub search; search results are not downloaded or installed.
- Agent previews now include the generated Codex wrapper and updated Claude plugin manifest as actual diffs.
  Saving regenerates and checks these outputs and rejects the transaction if either differs from the approved preview.
  Existing Codex wrapper-name collisions and symlinked registration paths are rejected.
- The preview and safety copy now state the exact scope: agent creation refreshes the Codex infra wrapper and Claude
  plugin only; skills get a canonical folder and infra shared link. Copilot/Gemini and user/project copies require
  the documented synchronization workflow; the wizard does not claim those copies are installed.
- A read-only preview against the real Workshop tree produced the expected canonical, catalogue, inventory, count,
  Codex and plugin diffs; no resource or adapter file was written. No actual agent or skill has been registered.
- Verification: full app suite 224 tests OK, 2 skipped; frontend logic suite 11 passed; production build passed;
  `codex-adapter.py agents --check` reported 26 agents and no drift; `git diff --check` passed in both repositories.
- Not verified: browser/keyboard/responsive owner acceptance or an independent security review of this registration
  flow. V5 remains partial and unaccepted; this work does not imply V4 acceptance. No commit or push.

### 2026-10-21: UI refinement and resource discovery

- The owner asked for readable Markdown previews with a plain-text option, a more comfortable UI/filter layout,
  quick console access for Claude, Codex, Copilot and Gemini, agent/skill discovery from the UI, guided resource
  creation, and clearer task assignment across clients.
- Implemented the concrete UI scope locally: Markdown preview now formats headings, emphasis, lists, quotes,
  code and simple tables, with a plain-text view. Raw HTML remains text, links are restricted to HTTP(S)/mailto,
  and remote images are not loaded. No Markdown dependency was added.
- Updated the visual palette and filter toolbar, and restored four always-visible console shortcuts. These only
  open existing client consoles; no engine capability level was raised.
- Added a guided public GitHub repository search for agents and skills. Research used official GitHub REST
  documentation ([repository search](https://docs.github.com/en/rest/search/search#search-repositories),
  [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api);
  unauthenticated search has a 10-request/minute limit and code search requires authentication) and
  [CommonMark's formatting reference](https://commonmark.org/help/). To avoid adding network access or
  credentials to the app, search terms remain local until the owner opens a fixed GitHub search link. Results
  are never downloaded or installed.
- Verification: 11 frontend tests passed; production build passed; backend regression suite passed (204 tests,
  2 skipped); `git diff --check` passed. No browser, keyboard, screen-reader or narrow-screen acceptance session
  was available.
- Still not implemented: the transactional agent/skill creation wizard, task board and per-task client
  assignment, persisted V3 conversations/chains, or V7 store/compress/recap/global search. These require their
  own secured workflows and acceptance evidence. Only Claude currently has verified level-2 chat; Codex,
  Copilot and Gemini remain console-only until their documented tool-free and provider checks pass.
- V1 pilot and first-use acceptance and V2 owner acceptance remain pending; this report does not mark either
  increment accepted.
- Organized follow-on work: close V1/V2 owner checks; complete V3 persistence and conversation flow using only
  verified engine levels (Ollama setup and provider checks remain prerequisites); build V4 task pages and client
  assignment; implement V5 as a reviewed multi-file registration transaction; then run V7's gated benchmark and
  deliver context store, recap, compression and global search. The new GitHub discovery remains browser-mediated;
  any future direct API integration needs a separate privacy, rate-limit and outbound-network review.

### 2026-10-21: V2 implemented, owner acceptance pending

- The owner asked to start the pending Workshop/UI plans after the concrete V2 scope was presented.
  Recorded as V2 Gate A and authorization to build while retaining V0/V1 acceptance as pending. No terminal
  approval was impersonated, and no acceptance, provider run or later-increment approval is inferred.
- Built the selected-document editor replacing the right reader, safe scalar header forms with advanced
  editing, change/capability review, text preview, per-document versions and restore, and creation from fixed
  document/task templates. Drafts live in browser memory above selection/filter remounts; unload warns about
  unsaved work. Notes are never stored in localStorage. Browser restart recovery is not promised.
- Saves back up existing bytes in the private workspace version store before atomic replacement; restore
  uses that pipeline. Retention keeps the latest 50 or anything newer than 90 days. HTTP 409 includes current
  text/hash and submitted draft. UTF-8 BOM and existing Windows line endings survive ordinary saves/restores.
- Added fixed-target Mis notas / Abrir en Bloc de notas / Editar aquí and Abrir Workshop actions. Notes are
  created only on use, after checking they are ignored and untracked; ordinary catalogue, reader, document,
  agent-profile and handoff paths exclude them. No actual personal note was created during implementation.
- Shared canonical header parsing now serves the adapter and app, rejects duplicates and unsupported syntax,
  preserves unknown fields, and semantically decodes quoted values. Independent security review found an
  escaped Agent-tool bypass; fixed it and added a regression that rejects the change before backup/write.
  Final review: no remaining blocking findings in this scope. C1/C2/C3/H1/H2/H4/M2/M3 stay with later increments;
  current work covers H3/H5/M1/M4/L2 and retains the §7 server protections.
- Adapter generation/check results are returned to the editor. Correct semantic parsing changed one existing
  description's apostrophe; regenerated its adapter and four existing native copies inside infra.
- Final verification: application suite ran 204 tests, OK, 2 skipped (Windows symlink creation denied); canonical
  parser 8 tests passed; frontend 4 focused tests passed; production build passed with the runner loader.
  One earlier full run hit a Windows reset while rejecting a request with an unread body; the HTTP boundary
  test now sends no body for those rejection checks, and the complete rerun passed.
- Workshop checks: 12 resource-sync tests ran, OK, one skipped; 504 installed infra resource files have zero
  drift; agent/plugin and personal adapter checks pass. User-wide/protected-root installation and discovery
  in fresh clients remain pending, as do Ollama installation and provider capability checks.
- Not verified: actual browser/keyboard/screen-reader/responsive behavior, native windows opening visibly,
  owner edit/save/restore flow, V1 pilot/first-use acceptance, real engine runs. No new dependency, commit or push.

### Next work, in order

1. Owner checks V2: open the app; select/edit a document; review/save; inspect versions and restore; try Mis notas
   and Abrir Workshop. Check keyboard and narrow-screen behavior. Record observations before Gate B approval.
2. Complete the fixed V1 sandbox pilot and observed 15-minute first-use session; retain actual usage and timings.
3. Finish Workshop resource installation in a normal terminal and verify fresh-client discovery, following
   `infra/docs/manuals/shared-resource-installation.md`. Restricted session checks cover infra only.
4. Run the separate gated Ollama installation/runtime tasks, then V3 conversations. Continue V4 tasks, V5 wizard,
   V6 controlled engine edits/handoffs and V7 token optimization through their recorded plans and gates.
5. Treat the hooks/tools and creative-provider research as proposals to select and review, not installed features.

### 2026-10-21: continuation readiness review

- Used all three available subagent slots for independent backend/security, frontend/accessibility and V1
  acceptance reviews, with relevant shared role/skill instructions. Findings and concrete implementation
  boundaries are appended to [the editor and notes plan](v2-editor-and-notes-plan.md).
- Fresh verification: 180 backend tests ran successfully, one skipped; the frontend production build passed
  with the runner config loader; the CLI help command succeeded. No engine received content.
- Required implementation work includes persistent authenticated versions, HTTP 409 conflict text, shared
  strict header parsing, note exclusions in generic document/agent/handoff routes, and draft state that survives
  filtering and navigation. These are readiness findings; no product code was changed.
- Pilot results remain blank and the owner first-use session remains unrecorded. Do not mark V0/V1 accepted.
  Follow the fixed pilot script rather than the different order in the older draft completion plan.
- Asked the owner whether to retain V1-first sequencing or approve the documented V2 scope while keeping V1
  acceptance pending. V2 Gate A is not recorded as approved while that answer is outstanding.
- No commit, push, dependency installation, terminal approval, real engine run or native desktop launch.

### Owner continuation decision: V1 pause, V2 acceptance, V3–V6

- The owner explicitly paused V1, described V2 as complete and working acceptably, and authorized continuing
  through V3–V6. V1 remains unaccepted; its pilot and observed first-use session are not claimed as complete.
- V2 Gate B is recorded as owner-accepted based on that statement. Separate browser, keyboard, responsive,
  Notepad/Explorer, and edit/restore observations remain unrecorded.
- V3 is now the active increment. V4–V6 are authorized to follow in roadmap order, with their own security,
  provider-capability and owner-acceptance requirements intact. At the time of this decision V7 was out of scope;
  the owner's 2026-10-22 authorization for the initial V7 global-search slice is recorded above.
- Provider availability is not inferred from this product authorization: only Claude currently has verified
  level-2 chat. Codex, Copilot and Gemini remain console-only until their tool-free checks and provider terms
  (R7) are recorded. "ChatGPT" is not a separate configured provider in the current registry.

### 2026-10-21: status audit and owner UI additions

- Git evidence supersedes the older uncommitted status below: `211b06c` merges the app and engine registry;
  `29ceb66` updates rules, README and plans. The application working tree was clean at the start of this audit.
  V1 still lacks recorded sandbox pilot and owner first-use acceptance; it is not marked accepted.
- Captured the owner's new requirements in [the V2 editor and notes plan](v2-editor-and-notes-plan.md): replace
  the right reader with the selected-document editor, open a fixed personal TXT in Notepad, and open the active
  Workshop root in Explorer. The personal note needs local-only publication/context exclusions because infra is
  public. No personal note or UI feature was created in this review.
- Three parallel read-only reviews covered status/roadmap, UI/UX, and backend/security. Existing save routes are
  useful groundwork; persistent versions, restore and the frontend editor remain missing.
- Fresh baseline: `python -m unittest discover -s tests` ran 180 tests, OK, one skipped;
  `npm.cmd run build -- --configLoader runner` passed. The default build was blocked by PowerShell script policy
  and then the sandbox's ancestor-directory restriction in esbuild's config loader; no policy was changed.
- Not verified: browser owner acceptance, sandbox pilot, native Notepad/Explorer actions or real engine runs.
  Next: close V1 acceptance, then present V2 Gate A using the concrete plan. No commit or push in this review.

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

  ### 2026-10-21: V3 chat and history hardening (ongoing)

  - Added locally persisted, bounded chat history with metadata validation, sensitive-text scanning, generic titles
    for flagged records, expiry enforcement on direct loads, and a 100-conversation cap that rejects new records
    rather than evicting existing ones.
  - Added Claude effort dispatch and pre-dispatch scanning. Unverified providers remain disabled for in-app chat;
    chain execution is still enforced as Claude-only.
  - Independent V3 security review identified five findings. Four mitigations were implemented: validate/scan
    metadata, hide flagged transcript snippets, enforce expiry on direct loads, and cap conversation count. These
    mitigations have not had a second independent review.
  - **Retention remains unresolved:** the current code/UI assumes 90 days, while architecture §2 says conversations
    are kept until the owner deletes them and §8 M4 requires a default retention. No owner decision was available,
    so the mismatch remains open and V3 is not accepted.
  - Verification after these changes: backend suite 215 passed, 2 skipped; frontend logic tests 11 passed; Vite
    production build passed; `git diff --check` passed. No browser, keyboard, screen-reader or responsive
    acceptance was recorded.
