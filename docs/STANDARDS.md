# Standards, references and verification

AI-assisted. Reviewed for **v0.3.0** on **2026-10-04**. Requirements come from the specifications below; repository conventions are design references, not additional standards or certifications.

## Normative contracts

| Contract | Implementation | Evidence and boundary |
| --- | --- | --- |
| [Agent Skills specification](https://agentskills.io/specification) | Matching lowercase directory/name; descriptive YAML frontmatter; string metadata for version/requirements; short entry point; relative usage reference; included license and notice | `skills-ref==0.1.1` validates the portable directory in tests. Requirements metadata also works with older host validators. Installing instructions alone does not install a runtime. |
| [MCP tools specification, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | Five bounded high-level tools; input/output schemas; structured content and text fallback; `isError`; read/write annotations; fixed local output root | Real stdio probes validate schemas, successful output, semantic failure and path rejection. Object schemas are intentionally broad; `PartSpec` enforces detailed numerical/geometric constraints. No claim of complete protocol certification. |
| [Official MCP Python SDK v2.2.0](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.2.0) | Exact SDK pin in `pyproject.toml` and hashes in `uv.lock`; current `MCPServer`, snake-case Python types; explicit package version | Tests exercise `2026-07-28` and legacy `2025-11-25`. Server shutdown releases its executor; running COM calls cannot be force-cancelled safely. |
| [Codex Skills](https://developers.openai.com/codex/skills) and [MCP](https://developers.openai.com/codex/mcp) | Project `.agents/skills` and `.codex/config.toml`; explicit interpreter/cwd/output path; no global settings mutation | Installer checks actual subprocess communication. Trusting/opening the project and successful host tool calls are separate activation evidence. |
| [Semantic Versioning](https://semver.org/) | Coherent package, source, `VERSION` and Skill metadata; immutable release tags; minor bump for the SDK migration and installer behavior changes | Release-content checks enforce version coherence and exclude local state. `0.y.z` denotes initial development, not production certification. |

The Agent Skills [reference library](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref) is a development validator, not an installer runtime dependency. Source/API references were inspected rather than copied into executable instructions.

## Practices adopted from projects

| Reference snapshot | Practice adopted | Scope |
| --- | --- | --- |
| [mattpocock/skills, c55ee460](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7) | Focused reusable Skill, explicit installation choices, useful feedback and tests | Independently written CAD instructions; no added interview ritual, orchestrator or duplicated installation path. MIT repository used as a design reference. |
| [Vercel skills, 36947403](https://github.com/vercel-labs/skills/tree/3694740352eeef5cdd689af694c485f1ff62eec3) | Discoverable `skills/<name>/SKILL.md`, optional project-local installation, clear full-runtime versus Skill-only choices | CLI example pins `skills@1.7.0` and this project's release. Discovery and installation are exercised in an isolated directory. |
| [Anthropic skills, 8a1541c4](https://github.com/anthropics/skills/tree/8a1541c4a3ffa5a20a5a91de0dcf3f0bab1d1ef4) | Portable instructions and progressive disclosure of resources | Reference only; no third-party Skill text copied or relicensed. Individual upstream licenses vary. |

Original project contributions implement the short execution chain: strict spec → one native writer → measured acceptance → manifest. We retain the selected vendored MIT files and their exact hashes in `upstream.lock.json`; those independent rights remain intact. Noncommercial original contributions make this project **source-available**, not OSI open source.

## Installation and release gates

1. **Isolate:** develop outside the active checkout; use a release-specific installation directory. Frozen dependencies prevent implicit SDK upgrades. The default setup remains one PowerShell command.
2. **Prepare:** detect config conflicts and changed managed files before native checks. A hash receipt identifies files the installer may update; it is not a security signature. Exact v0.2.0 generated Skill hashes support conservative migration.
3. **Verify:** import CAD dependencies, discover the installation, run a real stdio probe and optionally create one native bushing. `configured` and `cad_smoke_passed` have distinct meanings.
4. **Activate:** write only local config and the complete Skill after successful checks. Atomically replace individual files, roll back this run's writes after an ordinary error, and preserve concurrent user edits. This is not a crash-atomic filesystem transaction or a Python-environment rollback.
5. **Release:** run pure/transport tests on Windows and Linux, build wheel and source archive, validate versions/vendor hashes/licenses/private-content exclusions, run explicitly authorized native regression separately, publish a new tag and SHA-256 asset list. Never modify prior tags/assets.

The bounded MCP worker allows eight outstanding calls. It rejects excess work and retains capacity for a running job after caller cancellation. The cross-process lock coordinates this package's writers; neither mechanism controls manual SolidWorks interaction or unrelated macros. Keep the workstation idle during jobs.

## Evidence layers

See [v0.3.0 validation](VALIDATION-v0.3.0.md) for this release and [v0.2.0 validation](VALIDATION.md) for the historical baseline. Tests without CAD establish protocol and control behavior. Native tests establish the recorded synthetic cases on the recorded workstation. A host connection, engineering review, other SolidWorks versions and manufacturing completeness require their own evidence. No star count, test total or successful API call proves a universally superior production workflow.
