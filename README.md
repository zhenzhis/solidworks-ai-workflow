# SolidWorks AI Workflow

AI-assisted · **非商业源码公开 / Noncommercial source-available** · Windows + licensed SOLIDWORKS

用一条短流程完成机械零件：**明确参数 → 预检 → 原生建模 → 几何与文件验收 → 人工工程复核**。

这是一套可以检查结果、保留历史、持续维护的本机工作流。CLI 与五个 MCP 工具共用执行器；不需要数据库、向量检索或多代理调度。输入参数采用毫米，模型包含可在 SolidWorks 中编辑的原生尺寸和 `wf_*` 全局变量。

## 版本与范围

| 版本 | 内容 | 定位 |
| --- | --- | --- |
| `v0.1.0` | 脱敏后的原始工作约定、MCP 配置样例、固定上游提交 | 历史基线；不是推荐执行入口 |
| `v0.2.0` | 受控执行器、CLI/MCP、参数化模板、证据清单、安装与测试 | 首个可执行版本；仍处于 `0.y.z` 初始开发期 |

`v0.1.0` 保存在 Git 标签和 [baseline](baseline) 中。原工作站的私人脚本只在本地 `.local/original-workflow` 留档，不属于公开发行包。它们未被包装成可供任意机器安全执行的通用程序。

当前执行器支持四孔板 `plate`、直角支架 `bracket`、衬套 `bushing`，以及这些模板的原生变量改型。可选 `drawing: true` 生成四视图原生审阅草图和 PDF。工程图仍为 **pilot**：尺寸可重复、布局需人工复核，未承诺 GB/T 制造图、完整公差、GD&T 或工艺要求。小型装配、真实配合、钣金、螺纹及任意现有模型编辑尚未进入该执行器的验证范围。

本机验证环境、实际通过的案例和限制见 [验证记录](docs/VALIDATION.md)。本项目不宣称“全球最先进”，也不将 API 返回成功或测试数量当作制造质量证明。

## 快速开始

需要 Windows、已授权安装的 SolidWorks、Python 3.11+ 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。预检、输入规划和纯测试可在无 CAD 的环境运行。

```powershell
git clone https://github.com/zhenzhis/solidworks-ai-workflow.git
cd solidworks-ai-workflow
.\scripts\setup.ps1

.\.venv\Scripts\sw-workflow.exe doctor
.\.venv\Scripts\sw-workflow.exe plan examples\plate.json
.\.venv\Scripts\sw-workflow.exe build examples\plate.json --job plate-001
.\.venv\Scripts\sw-workflow.exe verify plate-001
```

安装使用仓库的 `uv.lock`，只写项目 `.venv`、`.codex/config.toml` 和 `.agents/skills/solidworks-workflow`。不会修改全局 Codex 配置。已有配置不同时停止并保留文件，供手动合并。可用 `-Python <python.exe 路径>` 指定解释器，或 `-Development` 安装测试依赖。

在 Codex 中打开并信任该项目后使用项目 Skill；项目配置加载规则见 [官方 MCP 文档](https://developers.openai.com/codex/mcp)。也可以直接使用 CLI。实际执行时保持 SolidWorks 空闲；本项目锁只协调本项目的进程，不能阻止鼠标操作或其他宏。

如模板发现失败，先在 SolidWorks 设置可用的默认模板，或通过 `SW_WORKFLOW_PART_TEMPLATE` / `SW_WORKFLOW_DRAWING_TEMPLATE` 指定本地文件。零件模板必须只有一个配置。模板和商业软件均不随仓库分发。

## 参数化修改与交付

```powershell
$state = (.\.venv\Scripts\sw-workflow.exe verify plate-001 | ConvertFrom-Json).manifest_sha256
.\.venv\Scripts\sw-workflow.exe edit plate-001 --job plate-002 --parameters examples\plate-edit.json --expected-state $state

# 可选：四视图审阅草图，包含 SLDDRW / PDF / BMP
.\.venv\Scripts\sw-workflow.exe build examples\plate-drawing.json --job plate-drawing-001
```

每次改型复制已验收的原生文件，修改原生全局变量，重新重建和验收。源任务及其文件保持不变；任务名不能复用。图纸引用在最终目录生成，避免临时目录搬移造成悬空引用。

每个成功任务位于 `artifacts/<job>/`，包含 `.SLDPRT`、`.step`、`.bmp` 和 `manifest.json`，可选增加 `.SLDDRW`、`.pdf` 及图纸预览。清单记录输入指纹、软件版本、配置、尺寸绑定、检查结果、耗时和文件 SHA-256。

自动验收检查实体数量、解析体积、实际外形尺寸、圆柱孔位/直径、原生毫米单位、特征错误、原生驱动尺寸、草图完全定义、保存重开和 STEP 往返。`verify` **只复核文件完整性**，不会重新启动 CAD，也不是数字签名或防伪认证。

最终清单是接受标记。失败可能留在 `.partial` 目录，或在已经生成图纸的目标目录留下 `failure.json`；没有接受清单的目录不能交付为已通过。发生 COM 卡住时查看本机对话框和检查点，勿重复发送建模任务；本版本不强杀 SolidWorks，也不保证所有 COM 调用都能超时取消。

## 五个 MCP 工具

| 工具 | 用途 |
| --- | --- |
| `workflow_doctor` | 只读发现安装与依赖，不启动 CAD |
| `workflow_plan` | 校验参数并计算独立几何目标 |
| `workflow_build` | 新任务建模、导出与验收 |
| `workflow_edit` | 校验预期状态，在副本中修改原生变量 |
| `workflow_verify` | 复核产物哈希并返回当前清单指纹 |

错误通过 MCP `isError` 传播。服务使用单个 STA 工作线程和跨进程写锁，输出根目录由启动配置确定；没有任意 Python 执行接口或全会话关闭接口。

`swapi-pilot` 是可选文档服务，安装时加 `-WithDocumentation` 即可生成其项目配置。只发送通用 API 名称/问题，不上传模型。Jev 不在默认依赖中；未来只在语义分类等可测量地受益的任务中作为可选组件接入。两者都不参与当前模板的几何求解。

## 开发与维护

```powershell
uv sync --frozen --extra cad --extra mcp --extra test
uv run --no-sync pytest -q
uv build

# 只在明确选定的空闲 Windows CAD 工作站运行，run-id 每次必须不同
uv run --no-sync python scripts\native_regression.py --live --run-id trial01
```

托管 CI 运行纯测试、真实 stdio MCP 协议测试和包构建；不连接任何 CAD 工作站。真实 CAD 回归验证三模板的创建/修改、源文件不变、无关未保存文档保护、审阅草图和一次真实 MCP 建模。它没有替代跨版本回归和人工工程复核。

采用 [SemVer](https://semver.org/)：已发布标签不改写；`0.y.z` 阶段不兼容接口变更提升次版本，兼容修复提升补丁版本。设计与后续优先级见 [DESIGN](docs/DESIGN.md)，版本差异见 [CHANGELOG](CHANGELOG.md)。

## 来源与许可

原创执行控制、契约、验收和测试采用 **[PolyForm Noncommercial 1.0.0](LICENSE)**。使用必须符合该许可证的非商业用途条款。本项目属于 source-available，**不是 OSI 定义的开源软件**。

经选择复用的 `wzyn20051216/solidworks-automation-skill` MIT 模块保持原文和独立 MIT 许可，来源、提交与逐文件哈希见 [upstream.lock.json](upstream.lock.json)；不能将这些第三方代码声称为我们的原创，也不能撤销其 MIT 权利。其他参考项目及服务见 [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md)。

私有 CAD、学生原件、参考照片、凭据、商业软件、模板与 SDK 二进制均不进入发行包。贡献请使用自行创作的合成样例。

## English

A small local SolidWorks workflow with one shared CLI/MCP implementation. It builds three dimension-driven part templates, changes native global variables in immutable job copies, and binds actual geometry checks and artifact hashes to a manifest. Optional native review drawings remain pilot quality. Windows and licensed SolidWorks are required for CAD; hosted CI runs without CAD. Original contributions are PolyForm Noncommercial 1.0.0 source-available, not OSI open source. Independently licensed MIT modules retain their original terms.
