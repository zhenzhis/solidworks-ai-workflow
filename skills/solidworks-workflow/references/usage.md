# Usage and readiness

This Skill targets solidworks-ai-workflow **0.3.0**. It carries instructions, not a CAD runtime. The complete runtime and installation instructions are at [the pinned release](https://github.com/zhenzhis/solidworks-ai-workflow/tree/v0.3.0). Do not auto-install over another version or edit global settings just because this Skill was loaded.

## Find the runtime

Prefer available `workflow_*` MCP tools. Otherwise use the installed `sw-workflow` command, or `<workflow-checkout>/.venv/Scripts/sw-workflow.exe` on Windows. Resolve the checkout from the user's project or configuration; never assume the current directory is the runtime checkout.

`workflow_doctor()` returns `cad_ready` for installation/import discovery only. It does not start SolidWorks or check licensing at runtime. The checkout's `.local/install-report.json` distinguishes `configured` (dependencies and real stdio protocol passed) from `cad_smoke_passed` (one synthetic native build, save/reopen, STEP round trip and artifact checks passed). Reports describe that run, not permanent future availability. Opening and trusting the project in the agent host is a separate step.

## MCP inputs

1. `workflow_plan({"spec":{"template":"plate","units":"mm","parameters":{"width":100,"height":60,"thickness":8,"hole_diameter":6,"margin_x":15,"margin_y":15}}})`
2. `workflow_build({"job":"plate-001","spec":<the same approved spec>})`
3. `workflow_verify({"job":"plate-001"})`
4. `workflow_edit({"source_job":"plate-001","job":"plate-002","parameters":{"width":120},"expected_state":<manifest_sha256 from verify>})`

Use only `plate`, `bracket` or `bushing`. Omitted parameters use documented template defaults returned by `plan`; call out inferred/default dimensions before accepting them as engineering intent. Input is strict millimetres, finite numbers, and a Boolean `drawing` option. Unknown specification fields and invalid geometry are rejected. MCP schemas describe the object envelopes; the shared `PartSpec` parser performs detailed geometric validation.

## CLI equivalent

Run from the workflow checkout, or explicitly pass `--root <owned-artifact-directory>` before the subcommand:

```powershell
.\.venv\Scripts\sw-workflow.exe plan examples\plate.json
.\.venv\Scripts\sw-workflow.exe build examples\plate.json --job plate-001
.\.venv\Scripts\sw-workflow.exe verify plate-001
```

The MCP output root is fixed by its startup configuration. CLI roots and MCP roots must match when using the same jobs. Neither interface accepts overwriting an accepted job.

## Failures and delivery

- Check `isError` in MCP results, process exit codes in CLI results, and the acceptance manifest before claiming success.
- A busy writer or queue means wait for the outstanding operation. A cancelled caller does not necessarily stop the native COM call. Inspect the owned job and SolidWorks dialogs before retrying; never force-kill the user's CAD session.
- If a source hash is stale, inspect the changed source and obtain its current state. Do not replace the hash silently to bypass the check.
- Inspect the actual preview. Deliver native CAD, STEP and manifest together. Optional drawings are review drafts; tolerances, GD&T, strength and manufacturability require human review.
- Unsupported operations must be identified as outside this executor's verified scope. Do not silently switch to an unverified arbitrary-code route.
