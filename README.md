# Homework 2 — Simple Workflow MVP（文档生成流程）

本工程实现了一个 **2 Agent + 确定性校验器** 的简单 Workflow：

```text
代码仓库 → 扫描器 → 代码分析 Agent → 文档编写 Agent → Markdown 校验器 → 输出文档
```

- `CodeAnalyzerAgent`：分析代码仓库，输出结构化 JSON（模块、入口点、依赖、架构关系）。
- `DocWriterAgent`：根据分析结果生成 README / 架构文档。
- `MarkdownChecker`：确定性校验章节完整性、代码围栏和文件引用，发现问题后自动触发修订。

详细设计见 [`Design.md`](Design.md)。

## 已实现的加分项（简化版）

- **条件分支**：按仓库文件数自动切换「全量分析 / 摘要分析」。
- **循环控制**：文档校验未通过时自动修订，最多重试若干次。
- **执行日志与状态追踪**：每个步骤记录事件和耗时，并输出 `*.run_log.json`。
- **错误处理与恢复**：LLM 网络错误/限流自动重试 3 次；分析 JSON 解析失败自动重试 1 次。

（并行执行与可视化编排界面未实现，属于可后续扩展项。）

## 运行要求

- Python 3.9+
- 默认零第三方依赖，Mock 模式可完全离线运行
- 真实模式需要 OpenAI 兼容的 Chat Completions 接口

## 快速开始（Mock 模式，无需 API Key）

```powershell
python main.py --repo sample_project --type all --mock
```

生成结果默认写入 `output/` 目录。

## 真实模式（DeepSeek / OpenAI 兼容接口）

推荐把配置写入项目根目录的 `.env`（该文件已被 `.gitignore` 忽略）：

```text
OPENAI_API_KEY=sk-你的key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat

# 可选：本机演示时的默认仓库
DEMO_REPO=C:\path\to\demo-repo
```

然后运行：

```powershell
python main.py --type all
```

也可以直接使用环境变量：

```powershell
$env:OPENAI_API_KEY="sk-..."
$env:OPENAI_BASE_URL="https://api.deepseek.com"
$env:OPENAI_MODEL="deepseek-chat"
python main.py --repo sample_project --type all
```

> 如果 `.env` 中设置了 `DEMO_REPO`，不传 `--repo` 时会使用该仓库；否则默认使用内置的 `sample_project`。这样既方便本机演示，也保证提交后在其他机器上可直接运行。

## 主要命令参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--repo` | 目标代码仓库路径 | `DEMO_REPO` 或 `sample_project` |
| `--type` | `readme` / `architecture` / `all` | `readme` |
| `--output` | 单种文档的输出文件路径 | 无 |
| `--output-dir` | 输出目录；`--type all` 时推荐使用 | `output` |
| `--mock` | 使用离线 Mock，不调用 API | 自动判断 |
| `--model` | 模型名称 | `gpt-4o-mini` |
| `--max-files` | 最多扫描文件数 | `60` |
| `--max-file-bytes` | 单个文件最大读取字节数 | `8000` |
| `--max-retries` | 校验失败后最多修订次数 | `2` |
| `--debug` | 打印详细事件日志 | 关闭 |

## 输出文件

每次运行会在输出目录生成：

```text
readme.md / architecture.md
readme.analysis.json / architecture.analysis.json
readme.run_log.json / architecture.run_log.json
```

## 目录结构

```text
Homework2_WorkflowMVP/
├── main.py                 # CLI 入口
├── Design.md               # 设计文档
├── README.md               # 使用说明
├── workflow/
│   ├── state.py            # 共享状态与数据模型
│   ├── scanner.py          # 仓库扫描器
│   ├── llm.py              # LLM 客户端（真实 + Mock）
│   ├── agents.py           # 两个 Agent 的实现
│   ├── checker.py          # 确定性 Markdown 校验器
│   └── orchestrator.py     # 流程编排
├── sample_project/         # 内置演示代码仓库
├── output/                 # 默认输出目录
├── .env.example            # 配置模板
├── run_mock.ps1            # 离线一键运行
├── run_deepseek.ps1        # DeepSeek 一键运行
└── requirements.txt        # 当前为零依赖
```
