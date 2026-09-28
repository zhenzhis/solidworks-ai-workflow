# v0.2.0 verification record

AI-assisted. Verified on **2026-09-28**. This is a measured release record, not a global benchmark or engineering certification.

## Local environment

- Windows, SOLIDWORKS 2026 SP04.1; API revision `34.4.1`.
- Python `3.13.9`, pywin32 `312`, comtypes `1.4.17`, MCP SDK `1.30.0`.
- Dependencies frozen in `uv.lock`; the runtime has no LLM or external geometry-service dependency.
- Synthetic geometry only. No original student work, private model or reference photo used as a public fixture.

## Executed checks

`python -m pytest -q`: **45 tests passed** locally, covering invalid inputs, nonfinite dimensions, hole clearance, path escape, reserved names, cross-process locking, immutable job activation, stale state, corrupted artifacts, failed-acceptance checkpoints, optimized Python (`-O`), installer preservation and real stdio MCP error flags.

`python scripts/native_regression.py --live --run-id release02`: **passed**, including the following eight actual CAD jobs:

| Job | Result | Observed job time |
| --- | --- | --- |
| Four-hole plate, default parameters | Native + STEP accepted | 14.448 s |
| Plate native-global-variable edit | Native + STEP accepted; source unchanged | 7.905 s |
| L bracket, default parameters | Native + STEP accepted | 11.649 s |
| Bracket native-global-variable edit | Native + STEP accepted; source unchanged | 6.752 s |
| Bushing, default parameters | Native + STEP accepted | 7.818 s |
| Bushing native-global-variable edit | Native + STEP accepted; source unchanged | 5.767 s |
| Plate with native review drawing | Native + STEP + SLDDRW + PDF accepted within pilot scope | 19.900 s |
| Bushing via a real stdio MCP client/server | Actual CAD execution and artifact integrity passed | Recorded in its job manifest |

Times are single observations on one already available workstation, not p50/p95 estimates or guaranteed latency. See [sanitized regression evidence](evidence/native-regression-v0.2.0.json). Artifact manifests include source specification fingerprints and file hashes; private machine paths and native CAD binaries are not published.

Each part checked: one solid body; independent analytic volume; exact body extents; cylindrical hole/diameter geometry; millimetre display units; feature error/warning state; native driving dimensions; fully constrained sketch status; native save/reopen/rebuild; and STEP import/re-measurement.

The regression placed an unrelated **unsaved synthetic document** in the session, verified its geometry, dirty flag, active state and document count after jobs, then closed only that test-owned document. It also rejected a stale source manifest and refused a duplicate job name.

The optional drawing had four native views, resolved model references after reopening, eighteen imported native model dimensions, millimetre units, view outlines inside the usable sheet region and no view-to-view overlap. Its actual PDF was inspected: one A3 page, readable millimetre values and a visible review-draft notice. Dimension duplicates remain visible and are a documented pilot limitation.

The project-local PowerShell setup script was executed successfully. The portable Skill passed the installed skill validator. Both the wheel and source archive passed version, pinned-source, license and private-content checks. The wheel was installed in a separate empty virtual environment and its planning command ran successfully. Public CI results are available in the repository Actions tab rather than being represented as native CAD results.

## Deliberate limits

- Only the listed Windows/SolidWorks version and synthetic cases were exercised; other versions, locales and custom templates need their own native regression.
- Small assemblies and real mates, manufacturing drawings, GD&T, material assignment, stress analysis, CNC toolpaths, sheet metal and arbitrary existing-model editing are not qualified by this release.
- Drawing checks do not establish complete dimension chains, tolerance correctness, native dimension/PDF text one-to-one matching or all annotation collisions. Human review is required.
- No claim of full B-Rep kernel certification, industrial safety, manufacturability or regulatory compliance follows from these checks.
- The local writer lock does not control external macros or manual UI changes. COM calls can block on UI or add-ins; cancellation and crash recovery are not universal transactions.
- A manifest hash detects changes relative to that manifest. It is not a cryptographic signature or a trust guarantee for a manifest supplied by someone else.

## Defects found and addressed during this release

Actual development failures were retained locally: dimension-input dialogs, an unavailable sketch accessor, cut direction, a global-variable naming conflict, split STEP cylindrical faces, drawing annotation import, inherited inch units and COM array marshalling of view positions. The final regression above was run after their fixes. Earlier failed attempts are not counted as successful native jobs.
