# V2 editor, personal notes and Workshop folder shortcuts

Status: built locally, 2026-10-21; V2 owner-accepted as working acceptably. Separate browser/keyboard/responsive,
Notepad/Explorer and edit/save/restore observations remain unrecorded. V1 remains paused and unaccepted.
Evidence and remaining checks: [progress](v2-progress.md).
Owner request: replace the right-hand reading assistant with an editor for the selected document; add a
personal TXT shortcut opening Windows Notepad and a shortcut opening the running Workshop folder.

## Verified starting point

- Active application: `applications/workshop-ai`; `workshop-infrastructure-ui` is read-only history.
- V1 is committed (`211b06c`, `29ceb66`). The sandbox pilot and observed owner first-use session remain pending.
- The right panel is currently `DetailPanel` / `ResourceInteraction`, containing the reader.
- Existing document/save endpoints support text, allowlists, hash conflict detection and atomic replacement.
  They do not yet provide persistent versions, restoration, creation from templates or a frontend editor.
- Resource-specific folder opening exists. A fixed Workshop-root shortcut and a Notepad-specific notes route do not.
- TXT is supported by the document backend but is not discovered by the current Markdown-only document catalogue.
- `infra/docs/notes` does not currently exist. No personal note was created during this planning review.

## Proposed UI: a working desk

Keep Workshop's navy navigation, blue actions and light document surfaces. Use the existing Segoe UI and
Cascadia Mono fonts; no new packages, web fonts or image assets. The editor is the main work surface.

Desktop arrangement:

```text
Navigation       Resource list                  Selected document editor
                 Search / filters               Title and relative path
                                                [Editar] [Vista previa] [Versiones]
Sections         Selected resource              [Datos de la ficha, when supported]
                                                Document content
Mis notas                                       [Revisar cambios] [Guardar]
Abrir Workshop                                  Sin cambios / Cambios sin guardar / Guardado
```

- Allocate about half the usable content width to the editor, with an adjustable divider and minimum widths.
  On narrow screens open the editor as a full-width view with a return-to-list action, preserving selection,
  draft and scroll. Do not squeeze the editor into the old reader's narrow column.
- Remove the right-hand reader controls, player, translation controls and reader wording. This supersedes
  the right-side Lector requirement in `infra/docs/workshop-ai-v2/ux-design.md` sections 2 and 3 for this change.
  Removing unrelated reading services or the standalone reading-assistant application is outside this request.
- Use clear Spanish states: "Selecciona un documento para editarlo", "Solo lectura", "Cambios sin guardar",
  "Guardando...", "Guardado". Read-only resources explain why they cannot be edited.
- Keep the save/review bar visible. Show differences before saving; previous versions remain accessible.
  Switching resources, sections or closing the page must protect a dirty draft.
- Preserve the existing structured-header requirements: shared parser, duplicate-key rejection, verbatim
  unknown fields, explicit tools/model review, and advanced mode when a form cannot be parsed safely.
- Keyboard: visible focus, labelled controls, Ctrl+S saves through validation/review, Ctrl+K opens global search;
  document fields keep native Ctrl+F. Announce save/errors through accessible status messages; respect reduced
  motion and use 44px touch targets. Implement the divider for keyboard users as well.

## Personal notes

- Add a compact "Mis notas" shortcut with a notebook icon and subtitle "Tu bloc de ideas" in the sidebar footer.
  Primary action "Abrir en Bloc de notas" opens one fixed TXT, proposed `infra/docs/notes/my-notes.txt`.
  An optional secondary "Editar aquí" selects that same file in the editor; both views share one file.
- The first click creates the directory/file only if absent. Repeated clicks never truncate an existing note.
  The filename is proposed, not an existing owner file.
- Because `infra` is public, implement an explicit local-only ignore for the personal TXT before creation.
  Verify that Git ignores it. Do not blanket-ignore unrelated shared documentation.
- Exclude the personal note from ordinary catalogues, search snippets, engine prompts, chain context, handoff
  packages and adapter scans. Give owner-only notes access a narrow fixed-file route, without broadening access
  to hidden state or arbitrary paths. The ignore rule alone does not provide these exclusions.
- Use a trusted Windows Notepad executable with fixed arguments; a default file association is insufficient.
  Report "Se ha solicitado abrir el Bloc de notas" after launch; do not claim its window is visible or text saved.
- If Notepad changes the file while an in-app draft exists, block stale saves, preserve the draft and offer
  "Ver diferencias" / "Recargar archivo". Never silently overwrite external edits.
- App versions cover app saves/restores. Notepad writes bypass that pipeline; do not promise per-keystroke or
  complete external-save history. No automatic background watcher is required for this increment.

## Workshop folder

- Add a folder icon and "Abrir Workshop" beside the notes shortcut; show the current folder as secondary text.
- Open the active server's configured Workshop root in Explorer. Derive it server-side, never from a browser-
  supplied absolute path or a hardcoded user profile. Reuse existing safe-open validation patterns.
- New launch actions use authenticated same-origin POSTs, fixed server actions, no shell interpolation, existing
  path/link checks and actionable errors. No dependency installation or permission relaxation.

## Delivery sequence and verification

1. Close V1: run the approved sandbox pilot, record its results and hold the 15-minute owner first-use session.
   Commits already exist; no new commit is required merely to unblock that pilot. Mark accepted only with evidence.
2. Present V2 Gate A using this plan: file areas, focused tests, no new dependencies and no engine test prompts
   or provider calls. New requirements are captured; full V2 implementation remains subject to the existing gate.
3. Build backend version-before-save, authenticated version read/list/restore and safe creation; complete the
   shared-parser header rules and retain existing protections. Restore itself creates a recoverable version.
   Change the inherited HTTP 200 conflict payload to the approved HTTP 409 response with both texts; expose
   adapter regeneration results and run `--check` after relevant saves. Complete only the approved allowlist.
4. Replace the right reader with the editor, review/preview/version views, draft protection and accessible layout.
5. Implement the private fixed-note route and Explorer/Notepad shortcuts, including conflict handling and exclusions.
6. Review security/accessibility and verify allowlist rejections, symlinks/junctions, conflict behavior, failed-save
   recovery, unknown header fields, version access/restore, missing/unsupported files, note creation without
   truncation, Git ignore/context exclusions and fixed launch targets. Run backend tests and frontend build.
7. Owner acceptance: open Workshop, create/open the note in Notepad, edit a selected document on the right,
   review/save it and restore a prior version. Record results in `v2-progress.md`; retain unverified items explicitly.

Expected implementation areas: `web/src/App.jsx`, `components/Sidebar.jsx`, `DetailPanel.jsx`,
`ResourceInteraction.jsx` (or a replacement editor), `api.js`, `styles.css`; server routing,
`resource_interaction.py`, `workshop_data.py`, a private version-store module and fixed desktop launch handlers;
focused tests; `infra/.gitignore` for the single personal note; canonical UX/architecture and progress docs.

Relevant roles: frontend-developer, ui-designer, security-reviewer, accessibility-expert, backend-architect,
code-reviewer and ui-ux-tester. Relevant methods: engineering-lifecycle, frontend-design, interaction-design,
responsive-design, ui-ux-pro-max and wcag-audit-patterns. Three parallel read-only reviews informed this plan:
project status, UI/UX and backend/security. Resources unrelated to this feature were not invoked.

## Baseline verification on 2026-10-21

- `python -m unittest discover -s tests`: 180 tests run, OK, one skipped.
- `npm.cmd run build -- --configLoader runner`: passed (Vite 7.3.7).
- Default `npm run build` was blocked by PowerShell script policy; `npm.cmd run build` then failed while the
  default esbuild config loader tried to access an ancestor directory denied by this sandbox. Runner succeeded
  without changing policy or project configuration.
- No browser acceptance, Notepad/Explorer flow, sandbox pilot or real engine run was performed in this review.

## Continuation review: 2026-10-21

The owner requested continuation with all available agents and skills. Three concurrent read-only delegates
covered backend/security, frontend/accessibility, and V1 acceptance, using the relevant canonical role and
skill instructions. These were manually instructed delegates, not a claim that every installed Workshop
agent or unrelated skill was executed. No provider calls or engine-level changes are part of this plan.

Fresh continuation checks: 180 backend tests ran successfully, one skipped; the frontend build passed with
`npm.cmd run build -- --configLoader runner`; `python -m workshop_ai --help` succeeded. The pilot results
remain blank. Automated checks do not substitute for the owner's interactive pilot or first-use acceptance.

### Concrete implementation boundaries

1. **Documents and versions:** `server/resource_interaction.py`, a new private version-store module, and
   document tests own the approved allowlist, save/restore/create pipeline and retention. Keep one routing
   owner for `server/server.py`. Store the current bytes before replacement; failure to create a backup
   blocks the save. Restore uses that same pipeline. Every version list/read/restore route requires the token.
   Return HTTP 409 with current text/hash and submitted draft. Specify `base_sha256` consistently in both
   browser and server rather than leaving it inconsistent with the existing `version` field.
2. **Shared headers:** extract the parser from `infra/scripts/codex-adapter.py` into a canonical shared module,
   imported by both adapter and app. Cover duplicate keys, unknown-field preservation and ambiguous syntax.
   Preserve the current header lock until the shared implementation is ready. Review tools/model changes
   separately; reject `Agent` in tools. Return bounded regeneration output and the subsequent check result.
3. **Private notes and desktop launch:** fixed-target handlers, `server/workshop_data.py`,
   `workshop_ai/scan.py`, and the single-note ignore rule in `infra/.gitignore` own privacy. Ordinary document,
   reader, dispatch and handoff/context routes must reject the note. Dispatch must require an actual agent
   resource rather than treating any document ID as a profile. Use exclusive first creation and verify Git
   ignore before creating. Empty notes are valid. Notepad and Explorer targets come only from the server;
   use trusted executables and fixed argument arrays. External Notepad saves do not gain automatic history.
4. **Editor and navigation:** `web/src/App.jsx` owns drafts above resource remounts and filtering;
   `DetailPanel.jsx` and the replacement for `ResourceInteraction.jsx` render the editor; `Sidebar.jsx`,
   `api.js`, and `styles.css` provide shortcuts, contracts and layout. Keep keyboard list focus distinct from
   opening a document. Route all selection/navigation changes through one dirty-draft guard. Search/filter
   changes must not discard the opened document. Preserve draft and scroll when switching narrow-screen
   views. Replace the current global Ctrl+F interception with Ctrl+K so native document find works.

### Focused acceptance evidence to collect

- Reject missing tokens, wrong origins, traversal, Windows drive/ADS paths, links/junctions and blocked paths;
  test private version-store ancestors as well as document paths.
- Backup failure leaves the original untouched; replacement failure preserves recovery bytes; concurrent
  saves produce one success and one conflict; restoring creates a recoverable version. Version IDs remain
  scoped to their document and cannot select arbitrary files.
- Notes survive repeated creation/open requests; ignore verification fails closed; generic catalogue,
  search, document, reader, agent profile and handoff paths exclude them. Dedicated routes work. A stale
  draft after an external edit remains available with a 409 comparison/reload action.
- Shared parser preserves unknown fields and rejects duplicates; unsafe headers use advanced mode;
  regeneration failures and check results remain visible.
- Verify dirty-draft behavior across resource, section, filter/search, refresh, history and notes transitions,
  plus browser unload; check keyboard save/review, native find, status announcements and the divider.
  On narrow screens verify explicit editor/list views and preserved draft/scroll. Build success alone does
  not prove these browser behaviors.
- Mock desktop launch calls to verify exact targets/arguments. Record actual Notepad/Explorer and owner
  editor/save/restore acceptance separately; do not infer visible windows from process creation.

### Owner sequence decision (2026-10-21)

After presentation of this concrete plan and the sequence choice, the owner requested starting the pending
Workshop/UI work. V2 Gate A is recorded and this implementation proceeds while V1 acceptance stays pending.
This authorizes the documented local build without new packages or provider calls. It does not accept V1/V2,
approve later increments, replace human terminal approvals, or authorize commits/pushes.

Implemented details: private versions use self-describing timestamp/UUID filenames rather than a separate
index file; drafts stay in browser memory and warn before unload; preview is safe plain text. New templates
live in `infra/docs/manuals/templates/`. See the progress record for final tests and the owner checklist.

For V1, retain the fixed script order in `workshop-ai-sandbox/pilot/user-script.md`: T1 baseline, T1 tool,
T2 tool, T2 baseline, T3 baseline, T3 tool. The older draft Stage 1 completion plan proposes a different order;
it does not override the fixed script. The pilot's terminal approvals must be given by a person, and its times,
interventions and usage must be observed rather than simulated. The owner first-use session is 15 minutes.
