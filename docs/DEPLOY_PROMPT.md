# Deploy with one prompt

[简体中文](DEPLOY_PROMPT.zh-CN.md) · Target release: **v0.3.0**

Paste the following into a coding agent with local Windows shell access. This is an installation instruction, not a remote script or a promise of unattended CAD setup. It authorizes one synthetic CAD check; keep SolidWorks idle. Git, uv and a licensed SolidWorks installation are prerequisites. uv can obtain the selected Python interpreter.

```text
Install and verify https://github.com/zhenzhis/solidworks-ai-workflow at release v0.3.0 on this Windows machine.

Use a new versioned checkout at %USERPROFILE%\solidworks-ai-workflow-v0.3.0 unless I supplied another target. Clone with --branch v0.3.0 --depth 1. If the target exists, inspect its origin, commit, tag and git status; reuse it only when it is this release and has no tracked or untracked user changes. Otherwise stop and report the conflict. Never reset, clean, overwrite or retag an existing checkout.

Read that release's README.md, AGENTS.md and docs/STANDARDS.md. Confirm VERSION, pyproject.toml and the checked-out release agree. Check Git, uv, Windows and the installed, licensed SolidWorks. If a prerequisite is missing or a permission gate prevents execution, report the exact blocker. Do not change global agent settings, execution policy, security settings or credentials, and do not install commercial CAD software.

Run .\scripts\setup.ps1 -VerifyCad from the checkout. This may download locked Python dependencies and Python, start the installed SolidWorks, and create one synthetic bushing in the ignored .local/install-checks directory. Use only project-local .venv, Skill and MCP configuration. Preserve user documents and previous releases. Do not enable optional remote documentation services unless I request them.

Require a zero installer exit code and .local/install-report.json status cad_smoke_passed. Inspect the reported native manifest, its checks and artifact hashes. If anything fails, keep the report and checkpoints, explain the failure, and do not label the installation ready. Do not repeat a blocked COM operation blindly.

Report the release tag and actual commit, installation directory, negotiated MCP protocol, native-check result, report location and remaining limitations. Explain that I must open and trust the checkout in Codex to load project MCP and Skill configuration; do not claim the host has connected until a host tool call succeeds. The smoke test qualifies the tested bushing path only, not all drawings or arbitrary modeling. After host activation, call workflow_doctor and workflow_plan to verify that connection when those tools are available.
```

For users who prefer commands, use [Quick start](../README.md#quick-start). For an existing v0.2.0 checkout, a separate versioned clone is the recommended upgrade. The installer also supports exact, unmodified v0.2.0 generated Skill migration and receipt-managed file updates; edited local files require an explicit manual merge. A deployment prompt cannot grant permissions that the agent host or operating system withholds.
