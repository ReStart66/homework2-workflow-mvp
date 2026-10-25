"""Simple Workflow MVP — CLI 入口。

示例：
    python main.py --repo sample_project --type readme --mock
    python main.py --repo sample_project --type architecture --mock
    python main.py --type all --output-dir output
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import uuid
from pathlib import Path

if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from workflow.llm import LLMClient
from workflow.orchestrator import Orchestrator


def load_dotenv(path: str | None = None) -> None:
    """极简 .env 加载器：从工程根目录读取 KEY=VALUE 到环境变量。

    已存在的环境变量不会被覆盖，因此 PyCharm 运行配置里的值优先级更高。
    """
    env_path = Path(path) if path else Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and value:
            os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simple Workflow MVP：代码分析 Agent + 文档编写 Agent + 确定性校验器"
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("DEMO_REPO", "sample_project"),
        help="目标代码仓库路径（默认读取环境变量 DEMO_REPO，否则使用 sample_project）",
    )
    parser.add_argument(
        "--type",
        choices=["readme", "architecture", "all"],
        default="readme",
        help="生成文档类型",
    )
    parser.add_argument("--output", default=None, help="单种文档的输出文件路径")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="输出目录；--type all 时推荐使用，避免覆盖两种文档",
    )
    parser.add_argument("--mock", action="store_true", help="使用离线 Mock，不调用 LLM API")
    parser.add_argument(
        "--model",
        default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        help="模型名称",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        help="OpenAI 兼容接口地址",
    )
    parser.add_argument("--max-files", type=int, default=60, help="最多扫描文件数")
    parser.add_argument("--max-file-bytes", type=int, default=8000, help="单文件最大读取字节数")
    parser.add_argument("--max-retries", type=int, default=2, help="校验失败后最多修订次数")
    parser.add_argument("--debug", action="store_true", help="打印详细事件日志")
    return parser.parse_args()


def build_llm(args: argparse.Namespace) -> LLMClient:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if args.mock:
        return LLMClient(model=args.model, base_url=args.base_url, api_key=None, mock=True)
    if api_key:
        return LLMClient(model=args.model, base_url=args.base_url, api_key=api_key, mock=False)
    print("[提示] 未检测到 OPENAI_API_KEY，自动使用 Mock 模式（离线演示）。")
    return LLMClient(model=args.model, base_url=args.base_url, api_key=None, mock=True)


def run_one(
    repo: str,
    doc_type: str,
    args: argparse.Namespace,
    multi_type: bool = False,
) -> str:
    llm = build_llm(args)
    run_id = f"{doc_type}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    orchestrator = Orchestrator(
        repo_path=repo,
        document_type=doc_type,
        llm=llm,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_retries=args.max_retries,
    )
    state = orchestrator.run(run_id)

    if args.output and not multi_type:
        doc_path = Path(args.output)
    else:
        out_dir = Path(args.output_dir) if args.output_dir else Path("output")
        doc_path = out_dir / f"{doc_type}.md"

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(state.draft, encoding="utf-8")
    (doc_path.parent / f"{doc_type}.analysis.json").write_text(
        json.dumps(state.analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (doc_path.parent / f"{doc_type}.run_log.json").write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[{doc_type}] 状态: {state.status}")
    print(f"[{doc_type}] 扫描文件: {len(state.file_inventory)} 个")
    print(f"[{doc_type}] 修订次数: {state.revision_count}")
    if state.issues:
        for issue in state.issues:
            print(f"    - {issue}")
    print(f"[{doc_type}] 文档: {doc_path}")
    print(f"[{doc_type}] 分析: {doc_path.parent / (doc_type + '.analysis.json')}")
    print(f"[{doc_type}] 日志: {doc_path.parent / (doc_type + '.run_log.json')}")

    if args.debug:
        print(f"\n===== {doc_type} 事件日志 =====")
        for event in state.events:
            print(f"  [{event['kind']}] {event['message']}  (+{event.get('elapsed_ms', 0)}ms)")
    return str(doc_path)


def main() -> int:
    load_dotenv()
    args = parse_args()

    types = ["readme", "architecture"] if args.type == "all" else [args.type]
    multi_type = args.type == "all"
    for doc_type in types:
        print(f"\n===== 生成 {doc_type} 文档 =====")
        run_one(args.repo, doc_type, args, multi_type=multi_type)
    return 0


if __name__ == "__main__":
    sys.exit(main())
