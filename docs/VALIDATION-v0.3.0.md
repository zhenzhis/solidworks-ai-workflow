# v0.3.0 verification record

AI-assisted. Executed on **2026-10-04**. This records observed results, not a universal compatibility or manufacturing qualification. Historical [v0.2.0 evidence](VALIDATION.md) is retained unchanged.

## Environment and contracts

- Windows; SOLIDWORKS 2026 SP04.1, API revision 34.4.1; Python 3.13.9.
- pywin32 312, comtypes 1.4.17; official MCP SDK 2.2.0 pinned in the lockfile.
- Real stdio probes: current 2026-07-28 and legacy 2025-11-25; five tools, valid schemas, structured success, semantic failure and path rejection.
- An independent, already installed MCP SDK 1.30.0 client connected to the 0.3.0 server and passed tool listing, valid planning and error-flag checks.
- 54 automated tests passed locally after the final runtime changes. Coverage includes native-control invariants, input/state integrity, configuration conflicts/upgrade/rollback, Windows config newlines/template overrides, failed-environment activation prevention and cancellation-aware queue capacity.
- The portable Skill passed `skills-ref==0.1.1` and the installed Codex Skill validator. `skills@1.7.0` discovered it and copied it into an isolated project; every copied resource hash matched.
- Wheel and source-archive checks validate versions, upstream file hashes, independent licenses, complete Skill resources, deployment prompts and private-content exclusions. Hosted CI exercises Windows/Linux with Python 3.11/3.13; consult the corresponding public Actions result for that environment's status.

## Actual installation and native execution

`scripts/setup.ps1 -Development -VerifyCad` completed with `cad_smoke_passed`. It started the installed SolidWorks, created a synthetic bushing through the current MCP protocol, saved/reopened the native file, checked geometry, re-imported STEP and verified artifact hashes before installing the local Skill/configuration. Reports and native files remain in ignored `.local` directories.

`scripts/native_regression.py --live --run-id release03 --root .local/native-v030` passed all eight CAD jobs:

| Case | Acceptance | Observed job time |
| --- | --- | --- |
| Plate creation | Native + STEP | 17.017 s |
| Plate variable edit | Native + STEP; source unchanged | 10.115 s |
| Bracket creation | Native + STEP | 15.387 s |
| Bracket variable edit | Native + STEP; source unchanged | 9.581 s |
| Bushing creation | Native + STEP | 8.415 s |
| Bushing variable edit | Native + STEP; source unchanged | 7.189 s |
| Plate review drawing | Native + STEP + SLDDRW + PDF, pilot checks | 26.205 s |
| Bushing over real legacy stdio MCP | Native + STEP and integrity | In job manifest |

[Sanitized native regression evidence](evidence/native-regression-v0.3.0.json) records hashes and verdicts. Single observations are not performance benchmarks and are not directly comparable to another run's cold/warm conditions.

The regression preserved an unrelated unsaved synthetic document's geometry, dirty flag, active state and document count. It rejected stale source state and duplicate job names. Native checks cover the recorded geometry, units, feature state, dimension bindings, sketch constraints, reopen and STEP round trip. Drawing layout/annotation completeness remains pilot scope; no additional manufacturing qualification is implied by this SDK migration.

## Issues found during verification

- The old doctor returned exit code zero when CAD discovery failed. A regression test first reproduced that false success; unavailable CAD now returns nonzero.
- SDK 2 requires parameterized dictionary return annotations to generate these structured-output schemas. The real stdio probe detected the missing schema before the fix.
- One mocked acceptance test initially contended with the real workstation writer lock. Its lock now uses a test-local path; actual cross-process locking retains its separate test and unchanged runtime scope.
- The older installed Skill validator does not recognize the optional top-level `compatibility` field. Requirements use standard string metadata instead, passing both validators without changing the validators.

## Limits

Installation verification is a local subprocess result, not proof that the Codex UI loaded the project. Open/trust the project and exercise its host tools separately. The smoke test alone covers one bushing. Full native regression covers only the listed cases on this workstation; other locales, versions and custom templates need their own checks. Assemblies, mates, manufacturing drawings, GD&T, strength and arbitrary existing-model edits remain outside the verified executor scope.

The installer restores its configuration writes after ordinary failures; environment changes and sudden power loss are not transactional. COM may block on dialogs or add-ins. Caller cancellation does not forcibly stop CAD. Existing release tags and artifacts remain immutable; versioned checkouts provide the supported rollback path.
