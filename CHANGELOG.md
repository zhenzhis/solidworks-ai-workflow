# Changelog

## 0.3.0 — Verified installation and portable Skill — 2026-10-04

- Migrate to pinned official MCP Python SDK 2.2.0 with structured outputs, explicit version and real current/legacy protocol checks.
- Bound the serial STA queue; retain running-job capacity after caller cancellation and shut down the executor with the server.
- Fix false-success doctor exit codes and validate actual CAD dependency imports.
- Verify installation through a real MCP subprocess; `-VerifyCad` adds a synthetic native build and STEP round trip. Report `configured`, `cad_smoke_passed` or `failed` explicitly.
- Activate project config only after checks; copy the whole portable Skill and licenses, track managed hashes, preserve custom files and roll back configuration write failures.
- Add standard Skill metadata and relative usage guidance, official format validation, fixed-version English/Chinese deployment prompts, and standards/provenance mapping.
- Expand English-primary and Chinese-secondary documentation with readiness, host activation, Skill-only installation and isolated upgrade/rollback guidance.
- Keep original releases, vendored MIT sources, native modeling semantics and historical validation records intact.

## 0.2.0 — Guarded executable workflow — 2026-09-28

- Add one shared CLI and five-tool MCP interface with proper protocol error flags.
- Add strict millimetre specifications, native dimensions/global variables, and copy-on-write parameter editing for plates, brackets and bushings.
- Bind document ownership, source manifest state and configuration; serialize native operations with a cross-process writer lock and STA MCP worker.
- Replace score-based acceptance with required geometry checks, exact extents, cylindrical feature checks, fully defined sketches, saved/reopened native checks and STEP round trips.
- Save recoverable native checkpoints, preserve failed outputs, refuse completed-job overwrites, and bind deliverables with hashes and provenance.
- Add optional native four-view review drawings and PDF export with unit, reference, view-boundary and reopen checks. Manufacturing completeness and dimension layout remain pilot scope.
- Add a project-local installer, concise portable Skill, frozen dependencies, pure/stdio tests, explicit native workstation regression, hosted CI and distributable Python packages.
- Preserve third-party MIT source attribution and keep private assets out of the public repository.

## 0.1.0 — Original baseline — 2026-09-27

- Preserve the original mechanical workflow and tool selection with private paths replaced by placeholders.
- Identify upstream implementation and known execution limitations.
- Establish noncommercial source-available licensing and exclude private learning material.
