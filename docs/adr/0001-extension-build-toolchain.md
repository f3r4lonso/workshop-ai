# 0001. Build and test toolchain for the VS Code extension

> **v2 note (2026-10-20):** applies only to the paused VS Code extension (proposed Workshop AI v2, decision D-V2-03).

Status: accepted
Date: 2026-10-18

## Context

The extension (`vscode-extension/`) is TypeScript with no runtime npm dependencies (spec D2, §8.7). Each development
package needs the owner's approval and a `dependency-license-review`. Packages with install scripts or downloaded
binaries are avoided unless approved.

## Options considered

1. `tsc` only, unit tests with Node's built-in `node:test` on the compiled output; logic that needs no `vscode`
   module (detection, infra lookup, the `wai` runner) lives in its own files and is tested directly, including
   against the real `wai` — three dev packages, no bundler, no test framework.
2. Add `@vscode/test-electron` for tests inside a real VS Code — closer to the real host, but downloads a VS Code
   build at test time (network, a binary).
3. A bundler (`esbuild`) — faster builds, but a native binary via postinstall; not needed for a small extension.

## Decision

Option 1, approved by the product owner on 2026-10-18. Pinned dev dependencies (reviewed 2026-10-18 from npm
registry metadata):

| Package | Version | License | Dependencies | Install scripts | Reason |
|---|---|---|---|---|---|
| `typescript` | 6.0.3 | Apache-2.0 | none | none | compiler; 7.x was rejected because it installs ~20 native per-platform binary packages |
| `@types/vscode` | 1.140.0 | MIT | none | none | API typings; matches the version the spec was verified against (VS Code 1.142.0 installed, so `engines.vscode` `^1.140.0` holds) |
| `@types/node` | 22.20.5 | MIT | `undici-types` 6.21.0 (MIT, no deps) | none | Node typings for `child_process`, `fs`, `path`; the 22 line is the conservative choice for the extension host's Node (Inference) |

Installs use `npm ci --ignore-scripts` (or `npm install --ignore-scripts` for the first lockfile); the lockfile is
committed.

## Consequences

- UI behaviour is checked by hand in an Extension Development Host until option 2 is approved.
- Moving to option 2 or 3 later needs a new ADR and a new review; this one is then superseded.
