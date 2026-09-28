# Third-party notices

AI-assisted. Original project contributions and third-party work are distinguished below.

- `wzyn20051216/solidworks-automation-skill`, commit `174d6c4770b3229c2fb3eb6babf7a16d56997c58`, is the MIT-licensed implementation referenced by the baseline. Six unmodified Python modules are vendored under `src/sw_workflow/_vendor/`; exact source paths and SHA-256 values are in `upstream.lock.json`. Copyright (c) 2026 SolidWorks Automation Skill Contributors. Its full MIT text is retained in that directory. These files keep their independent MIT terms; the project noncommercial license does not revoke those rights.
- `swapi-pilot` is an optional external documentation service. Its server implementation is not distributed here.
- SOLIDWORKS is third-party commercial software and is not included. Installed templates, SDK binaries and help files are not redistributed.
- PolyForm Noncommercial license text is obtained from the PolyForm Project's published standard text and is not modified.
- `czuryk/SolidworksMCP`, `eyfel/mcp-server-solidworks`, and `xarial/xcad` were considered during architectural review. No code from these projects is bundled. In particular, AGPL source is not copied into or re-licensed by this package.
- Runtime/development dependencies are installed separately through the lockfile and retain their own licenses. Their source distributions and binaries are not vendored. The drawing implementation uses native SOLIDWORKS PDF export; PyMuPDF is not a project dependency.
