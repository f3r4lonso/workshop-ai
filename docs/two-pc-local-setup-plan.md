# Two-PC local setup plan

Status: **owner-directed implementation in progress; work-PC acceptance remains pending**.
Date: 2026-10-22

## Goal

Make the same committed Workshop AI browser app usable locally on the owner's work and personal Windows PCs,
with the app source obtained from its private GitHub repository. Keep private app data separate on each PC.

## Current state and evidence

- Workshop AI is already a browser app. `INICIAR.cmd` starts its local server at `http://127.0.0.1:8770/`;
  converting it into a website is not needed. See the [project README](../README.md) and the
  [v2 architecture](../../../infra/docs/workshop-ai-v2/architecture.md).
- The app reads the shared Workshop infrastructure, normally at `%USERPROFILE%\workshop\infra`; both
  repositories therefore need to be present in a compatible local layout. The app can also use
  `WORKSHOP_AI_INFRA`.
- The first UI build uses npm and requires Node.js. The server uses Python. Existing dependencies and the
  [project's setup instructions](../README.md) should be reused; do not add a package or installer unless a
  clean-machine trial demonstrates a need.
- Conversations, notes, settings and app-managed versions are private local state outside Git. They are not
  intended to move between PCs. See [architecture §2](../../../infra/docs/workshop-ai-v2/architecture.md#2-where-state-lives)
  and [§4](../../../infra/docs/workshop-ai-v2/architecture.md#4-files-editing-and-versions).
- Readiness observed on 2026-10-22: `origin/main` was at `29ceb66` when the clean setup trial began. The
  personal-PC app worktree has numerous modified and untracked files and is not a clean release snapshot.
  GitHub access from the work PC has not been verified.
- Workshop AI v2 is still in progress. “Same functionality” means the functionality in the selected committed
  snapshot, not every feature still pending in the v2 roadmap.

## Scope and boundaries

**In scope**

- A repeatable, documented Windows setup using the existing private app repository and the shared
  infrastructure repository.
- Starting and updating the app independently on each PC.
- A clean-checkout trial that verifies the documented prerequisites, startup, local-only access and data
  separation.

**Out of scope**

- Hosting the UI publicly or making it remotely reachable.
- Synchronizing conversations, notes, settings, versions or other private data.
- Publishing the private app repository, adding an automatic updater, or creating a desktop installer.
- Changing Workshop AI's feature scope or its existing loopback security boundary.

## Requirements and acceptance criteria

1. On each authorized Windows PC, a clean clone of the selected app revision starts using the documented
   instructions and displays the same functionality available in that revision.
2. The app listens only on loopback; it is not accessible from another device on the network.
3. The app reads the expected shared Workshop resources on both PCs without committing those resources into
   the app repository.
4. Conversations, notes, settings and versions remain local to their own PC, outside Git, and do not appear
   in either repository's change list.
5. Updating the app or infrastructure checkout does not overwrite the local private state.
6. The work-PC setup is attempted only after confirming workplace rules permit the required tools and access
   to the private GitHub repository.
7. No existing local changes are discarded, and no commit or push is made without the owner's approval.

## Plan

| # | Step | Files / areas | Verification | Rollback |
|---|---|---|---|---|
| 1 | Select a publishable source snapshot. Review the existing modified and untracked work, determine which changes belong in the release, and obtain approval before committing or pushing. Do not treat the current worktree as installable. | `applications/workshop-ai` Git history and working tree | Confirm the chosen commit is available from the configured upstream; run the repository's test suite and production build against that exact snapshot. | Leave all current changes untouched; abandon the release attempt without cleaning or resetting the worktree. |
| 2 | Confirm prerequisites and layout on Windows: Git, Python, Node.js/npm for the first frontend build, the private app clone and the shared infrastructure clone at the expected paths. Check workplace policy and repository access before cloning on the work PC. | Existing setup in `applications/workshop-ai/README.md`, `INICIAR.cmd`, infrastructure path/configuration | Fresh local clone resolves the infrastructure, builds the frontend, and starts successfully. Record exact prerequisite versions only after testing them. | Stop before changing workplace settings or installing tools; retain existing clones and state. |
| 3 | Close only the onboarding gaps found in the clean-clone trial. Prefer a concise README update; add a helper only if manual steps prove error-prone. Include first start, normal start, update order, and troubleshooting. | `applications/workshop-ai/README.md`; `INICIAR.cmd` only if a tested gap requires a change | A second person can follow the instructions from a clean checkout without relying on this development machine's environment. | Revert only the approved documentation/helper change; do not remove repositories or private state. |
| 4 | Verify isolation and repeatability using the selected snapshot. Start the app, check key available sections, inspect the listening address, and perform an update check while confirming private data is unaffected. | App startup, local state directory, both repositories | Acceptance criteria 1–5 pass; no private state is tracked by Git. | Stop the local server; preserve both clones and all local state; restore the prior instructions if needed. |
| 5 | Owner performs the work-PC acceptance after Step 2 clears the workplace-policy and access checks; record any IT restriction or environment difference and adjust documentation only for an evidenced need. | Work PC setup, workplace policy | Owner confirms the app starts and the local-only/data-separation expectations hold. | Do not bypass workplace controls; use only an approved alternative if blocked. |

## Risks and decisions

- **Private GitHub access:** the app repository is documented as private. The work PC may not have access or may
  prohibit cloning it. Do not make it public as a workaround.
- **Uncommitted source:** the current worktree contains many uncommitted changes. A fresh clone will not include
  them, and publishing them requires review and explicit approval.
- **Prerequisites or network restrictions:** npm dependency installation or GitHub access may be blocked at work.
  Test this before promising a one-click setup; do not install unapproved software.
- **Separate data:** data will differ between PCs by design. Any future request to synchronize it or access it
  remotely is a new product/security decision, not part of this plan.
- **Feature maturity:** both PCs can match one another while still reflecting unfinished v2 increments. Do not
  describe planned features as delivered.

## Execution record (2026-10-22)

- Created isolated clean checkouts of Workshop AI and the infrastructure repository in the documented folder
  layout, using app commit `29ceb66` and infrastructure commit `62abc2c`.
- `npm ci` and the production frontend build passed. The local server returned HTTP 200 and loaded 122 resources
  across seven sections; the listener was verified on `127.0.0.1:8770` only.
- The focused server test file passed (43 tests). The complete app test suite did not pass in the reduced clean
  checkout: tests also depend on adjacent Workshop projects and legacy catalogue data. Supplying the local
  reader source resolved its reader tests, but the reader project has no configured GitHub remote and cannot
  currently be installed from GitHub on the second PC.
- The app repository is not a self-contained test fixture: its workspace-level tests expect sibling projects,
  including the retired Infrastructure UI. That legacy project is documented as read-only history and is not a
  required runtime dependency for Workshop AI.
- The work PC has not been accessed. Workplace approval, private-repository access, its prerequisite versions,
  and owner acceptance there remain unverified.
- The original app worktree contains unrelated modified and untracked files. A separate clean clone is being
  used for any focused release so those changes are not included.

## Review

This plan matches the selected approach (local clone on both PCs) and the explicit choice to keep private data
separate. It preserves the approved local-only architecture and avoids a public deployment. A clean clone builds
and starts, but the full reader integration and work-PC access are not yet portable/verified. No architecture
decision record is needed unless the scope later changes to remote hosting or cross-device data synchronization.

**Open before the two-PC setup is complete:** make the reader helper available from an approved source, and have
the owner confirm workplace policy allows private-repository access and the required tools on the work PC.
