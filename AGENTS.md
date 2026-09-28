# Repository agreements

- This is a noncommercial source-available project. Keep original contributions under PolyForm Noncommercial 1.0.0 and preserve independent third-party licenses. Do not label it OSI open source.
- Keep the runtime small: one spec, one native writer, one acceptance manifest. Prefer improving the shared CLI/MCP service over adding orchestration layers.
- Never commit `.local`, artifacts, user paths, credentials, private reference images or installed CAD templates/binaries.
- Preserve released tags. Use SemVer; while at 0.y.z, incompatible contracts require a minor version bump.
- CAD mutations use explicit owned documents and a writer lock. Never call CloseAllDocuments, overwrite an accepted job, or place executable operations inside assert.
- Pure tests run in CI. Native tests require an explicitly selected Windows workstation with licensed SolidWorks and no concurrent manual modeling. Never attach a public PR runner to that workstation.
- Record actual verification scope and failures. A geometry pass is not a manufacturing release.
