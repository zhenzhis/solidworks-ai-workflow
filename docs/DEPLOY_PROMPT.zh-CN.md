# 一键部署 Prompt

[English](DEPLOY_PROMPT.md) · 固定版本：**v0.3.0**

将以下完整内容交给能执行本机 Windows 命令的编程 Agent。它是可复制执行的部署指令，不是远程脚本，也不承诺绕过软件安装、授权或操作系统权限。执行前保持 SolidWorks 空闲；需要 Git、uv 和已授权的 SolidWorks，uv 可获取所选 Python 解释器。

```text
请在本机 Windows 安装并验证 https://github.com/zhenzhis/solidworks-ai-workflow 的 v0.3.0 发行版本。

除非我指定其他路径，请新建 %USERPROFILE%\solidworks-ai-workflow-v0.3.0，以 --branch v0.3.0 --depth 1 克隆。目标已存在时，先检查 origin、提交、标签和 git status；仅当确为这个发行版本，且没有已跟踪或未跟踪的用户修改时复用。否则停止并报告冲突。不得 reset、clean、覆盖已有仓库或改写标签。

阅读该版本 README.md、AGENTS.md 和 docs/STANDARDS.md；核对 VERSION、pyproject.toml 与所检出的发行版本一致。检查 Git、uv、Windows 及本机已安装且有授权的 SolidWorks。缺少前置条件或权限不允许执行时，准确报告阻塞项；不要修改全局 Agent 配置、执行策略、安全设置或凭据，不要替我安装商业 CAD 软件。

从仓库运行 .\scripts\setup.ps1 -VerifyCad。我授权本次下载锁定的 Python 依赖及 Python、启动已安装的 SolidWorks，并在被 Git 忽略的 .local/install-checks 下创建一个合成衬套作为安装测试。依赖、Skill 与 MCP 配置限于项目本地。保留用户文档和历史版本；不启用我未要求的远程文档服务。

必须同时满足安装进程退出码为 0，且 .local/install-report.json 的 status 为 cad_smoke_passed。检查报告指向的原生验收清单、检查结果和文件哈希。有任何失败就保留报告与检查点，说明原因，不得称为安装成功；不要盲目重试卡住的 COM 操作。

最终报告发行标签与实际提交、安装目录、MCP 协商协议、原生检查结果、报告位置和实际限制。说明我仍需在 Codex 打开并信任这个项目才能加载其 MCP 与 Skill；未成功调用宿主内工具前，不得声称宿主已连接。单个衬套测试只验证所测路径，不代表全部工程图或任意建模均已验证。宿主工具可用后调用 workflow_doctor 和 workflow_plan 验证宿主连接。
```

已有 v0.2.0 时，推荐新建版本目录并保留旧目录。安装器也支持原样的 v0.2.0 生成 Skill 迁移及安装收据管理的文件升级；遇到用户改动须显式手动合并。Prompt 不能授予宿主或操作系统未提供的权限。
