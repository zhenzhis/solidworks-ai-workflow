# SolidWorks AI Workflow

AI-assisted. A lightweight, noncommercial, source-available SolidWorks workflow.

## v0.1.0: original workflow baseline

This release preserves the original workflow instructions and the 29-tool local MCP / 5-tool documentation MCP profile. Machine-specific paths are replaced with placeholders. It is an archival baseline, not the recommended executable release.

The original approach is: clarify requirements → reuse a short script or template → execute through SolidWorks → inspect real geometry → deliver native and interchange files.

See `baseline/WORKFLOW.md` and `baseline/config.toml.example`. The upstream implementation is identified in `upstream.lock.json`; it is not represented as original code of this project.

Known limitations: active-document targeting, incomplete parameter-driven sketches, unsafe all-document close behavior in the upstream profile, review scores that do not imply engineering acceptance, and machine-specific installation. These are recorded so later versions can be compared honestly. Do not run this historical profile on a session containing valuable unsaved documents.

No student originals, screenshots, reference product images, private credentials, installed commercial software, or native CAD project files are included. Original local scripts are retained only in a Git-ignored local archive.

## License

Original contributions are licensed under **PolyForm Noncommercial 1.0.0**. Commercial use is not permitted by this license. This is source-available software, not OSI-approved open source. Third-party materials retain their own licenses; see `THIRD_PARTY_NOTICES.md`. A separately licensed installation of SOLIDWORKS is required for CAD execution.

## 中文

本版本保存原始工作流的可公开配置和约定，用作后续改进的对照。私人路径已替换为占位符，学习原件、照片、私人模型和凭据不进入仓库。原版存在已知执行风险，仅作历史参考。

本项目原创部分采用 PolyForm Noncommercial 1.0.0，限非商业用途；第三方代码保留各自许可证。
