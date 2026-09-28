# Design and maintenance priorities

AI-assisted. The intended scope is local, reproducible mechanical work with explicit evidence and a short operating path.

```mermaid
flowchart LR
  A[Requirement and dimensions] --> B[Strict PartSpec and analytic targets]
  B --> C[CLI or five MCP tools]
  C --> D[Single STA writer and owned documents]
  D --> E[Native globals and dimensions]
  E --> F[Save and reopen / STEP round trip]
  F --> G[Checks and hashed manifest]
  G --> H[Human engineering review]
```

## Core choices

- Reuse six pinned, unmodified MIT modules for installation discovery, COM compatibility, sketches and exports. Keep all project policy in our own adapter. The vendored helper namespace is internal, not an unrestricted supported tool surface.
- Use native global variables prefixed `wf_` to avoid naming conflicts (the unprefixed `thickness` failed in the local test). All input dimensions and exported display units are millimetres; internal SolidWorks API coordinates are metres.
- Fix only sketch reference origins. Use driving dimensions and equations for geometry. Verify fully constrained sketch status and dimension values on both the initial and reopened native part.
- Use exact body extreme points, analytic volume targets and cylindrical surface geometry. STEP may split a cylindrical surface at its seam, so merge geometrically equivalent surface observations before comparing hole counts.
- Persist recoverable native checkpoints after the first solid features. Each run owns only documents it creates or explicitly opens. Save explicitly and close owned documents only. Never use CloseAllDocuments.
- Treat a finished job as immutable. Edits require the current manifest digest, verify source artifacts and copy the native file before changing its global variables. This prevents stale edits and accidental source overwrites; hashes are not an authenticity mechanism.
- Serialize native operations within the MCP process and across this package's local processes. The lock is not a general desktop scheduler. Native COM can still block on dialogs; do not kill the user's application or silently replay a possibly completed mutation.
- Finish native model checks in a staging folder, move the model to its final folder, optionally create linked drawings there, and write the acceptance manifest last. No manifest means no accepted delivery, even if output files exist.
- Read-only discovery does not imply a working CAD runtime. A passed synthetic regression proves only its recorded version, templates and cases. Manufacturing release remains a separate human decision.

## What is intentionally small

The first executable release has no database, RAG, custom browser, cloud model service, generic graph executor or autonomous repair loop. The high-level MCP has no arbitrary code execution endpoint. Jev is optional future semantic assistance; it has no role in precise geometry arithmetic or the default installation. AutoCAD and a C# add-in should be added only for a measured requirement that the current interface cannot satisfy.

## Next increments

1. **Small assemblies:** add a synthetic fixture with real coincident/concentric mates, stable entity references, degrees-of-freedom checks, interference checks and dependency packaging. Do not equate component placement with a valid assembly.
2. **Manufacturing drawings:** explicit projection standard, templates supplied by the user, dimension selection/de-duplication, hole callouts, tolerances, BOM and machine-readable PDF text collision checks. Current review drawings intentionally carry no standards-compliance claim.
3. **Threaded holes and fillets:** adopt selected upstream operations only after new synthetic negative cases, rebuild/reopen and changed-parameter regression. Preserve cosmetic-versus-modeled thread distinctions.
4. **Reliability:** a broker or C# add-in becomes justified if measured COM hangs or cross-client contention persist. First record p50/p95 completion time, pass rate, manual intervention and recovery success on a fixed case set.

These are priorities, not promises of already implemented capabilities. Changes must beat the existing baseline on successful deliverables and recovery cost, not tool count or a self-assigned score.

## Sources considered

- [wzyn20051216/solidworks-automation-skill](https://github.com/wzyn20051216/solidworks-automation-skill): selected MIT helpers are actually vendored and pinned.
- [czuryk/SolidworksMCP](https://github.com/czuryk/SolidworksMCP): reviewed checkpoint and structured-operation ideas; no source copied.
- [eyfel/mcp-server-solidworks](https://github.com/eyfel/mcp-server-solidworks): considered state/version and STA concepts; no AGPL source is included or re-licensed.
- [xarial/xcad](https://github.com/xarial/xcad): potential future C# abstraction; not a current dependency.
- [SOLIDWORKS API: Equation](https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IEquationMgr~Equation.html), [sketch constraint status](https://help.solidworks.com/2026/English/api/swconst/SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.swConstrainedStatus_e.html), [model units](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelDoc2~SetUnits.html).
