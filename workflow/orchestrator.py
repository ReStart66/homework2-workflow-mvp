"""Workflow 编排器。

流程：扫描 -> 条件分支 -> 代码分析 Agent -> 文档编写 Agent -> 确定性校验 -> 循环修订。
"""
from __future__ import annotations

from .agents import CodeAnalyzerAgent, DocWriterAgent
from .checker import check_document
from .llm import LLMClient
from .scanner import scan_repository
from .state import WorkflowState

BRANCH_THRESHOLD = 30


class Orchestrator:
    def __init__(
        self,
        repo_path: str,
        document_type: str,
        llm: LLMClient,
        max_files: int = 60,
        max_file_bytes: int = 8000,
        max_retries: int = 2,
    ) -> None:
        self.repo_path = repo_path
        self.document_type = document_type
        self.llm = llm
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_retries = max_retries
        self.analyzer = CodeAnalyzerAgent()
        self.writer = DocWriterAgent()

    def run(self, run_id: str) -> WorkflowState:
        state = WorkflowState(
            run_id=run_id,
            repo_path=self.repo_path,
            document_type=self.document_type,
            model=self.llm.model,
            llm_mode="mock" if self.llm.mock else "real",
        )
        state.add_event("workflow_start", "Workflow 启动")

        state.file_inventory = scan_repository(
            self.repo_path,
            max_files=self.max_files,
            max_file_bytes=self.max_file_bytes,
        )
        state.add_event("scan_done", f"扫描完成，共 {len(state.file_inventory)} 个文件")

        if not state.file_inventory:
            state.status = "failed"
            state.add_event("workflow_failed", "未扫描到任何可分析的源文件")
            return state

        # 条件分支：按仓库规模选择分析粒度
        if len(state.file_inventory) > BRANCH_THRESHOLD:
            analysis_mode = "summary"
            state.document_plan["analysis_mode"] = "summary"
            state.add_event(
                "branch",
                f"条件分支：文件数 {len(state.file_inventory)} > {BRANCH_THRESHOLD}，采用摘要分析",
            )
        else:
            analysis_mode = "full"
            state.document_plan["analysis_mode"] = "full"
            state.add_event(
                "branch",
                f"条件分支：文件数 {len(state.file_inventory)} <= {BRANCH_THRESHOLD}，采用全量分析",
            )

        self.analyzer.run(state, self.llm, analysis_mode=analysis_mode)
        self.writer.run(state, self.llm)

        # 循环控制：校验未通过则触发修订，最多 max_retries 次
        issues = check_document(state)
        while issues and state.revision_count < self.max_retries:
            state.revision_count += 1
            state.add_event(
                "revision_start",
                f"循环控制：校验发现 {len(issues)} 个问题，开始第 {state.revision_count} 次修订",
            )
            self.writer.run(state, self.llm, issues=issues)
            issues = check_document(state)

        state.issues = issues
        state.status = "completed" if not issues else "completed_with_warnings"
        state.add_event(
            "workflow_done",
            f"Workflow 结束，状态 {state.status}，剩余问题 {len(issues)} 个",
        )
        return state
