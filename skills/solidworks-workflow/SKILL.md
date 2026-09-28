---
name: solidworks-workflow
description: Build and edit dimension-driven SolidWorks plate, bracket and bushing parts using this repository's guarded CLI or five MCP tools, with native and STEP acceptance evidence. Use for these managed templates and their delivery review; assemblies and general CAD editing require a separately verified adapter.
---

# SolidWorks Workflow

Use the installed `sw-workflow` CLI or the `workflow_*` MCP tools. Run `doctor` when the local environment is unknown. The CLI and MCP call the same implementation; use one route per job.

1. Translate the requirement into a template and millimetre parameters. Keep inferred dimensions visible. Run `plan`; it validates input and calculates independent geometry targets without starting CAD.
2. Run `build` with a fresh lowercase ASCII job name. Each job owns its new document, native file, STEP, preview and manifest. A finished job cannot be overwritten.
3. Inspect the returned validation and preview. A passed automatic check covers the recorded geometry and native rebuilds; it does not certify tolerances, strength, manufacturability or drawing completeness.
4. For changes, run `verify` to obtain the current manifest hash, then `edit` into a new job with that `expected_state`. This changes native global variables in a copy and repeats acceptance; preserve the earlier job.
5. Deliver the native file, STEP and manifest together. `verify` checks file integrity only, not fresh CAD state. Failed jobs retain `.partial` checkpoints and must not be described as accepted.

Keep SolidWorks idle while the job operates. The workflow lock coordinates this package's processes, not the user's mouse or unrelated macros. Never replace an unsupported operation with arbitrary Python through MCP or a whole-session close.

See the repository README for installation and exact command examples. Optional API documentation tools can help check signatures; they are not required for the three templates. Do not upload private CAD or photographs to documentation or model services without the user's authorization.
