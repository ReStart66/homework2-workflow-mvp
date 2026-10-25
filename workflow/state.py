"""共享状态与数据模型。

整个 Workflow 中所有 Agent 不直接互相调用，而是通过 WorkflowState 传递信息。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FileRecord:
    """扫描到的一个源文件。"""

    path: str
    size: int
    language: str
    lines: int
    content: str


@dataclass
class WorkflowState:
    """贯穿整个流程的共享状态。"""

    run_id: str = ""
    repo_path: str = ""
    document_type: str = "readme"
    model: str = "gpt-4o-mini"
    llm_mode: str = "mock"
    started_at: float = field(default_factory=time.monotonic, repr=False)

    file_inventory: List[FileRecord] = field(default_factory=list)
    analysis: Dict[str, Any] = field(default_factory=dict)
    document_plan: Dict[str, Any] = field(default_factory=dict)
    draft: str = ""
    issues: List[str] = field(default_factory=list)
    status: str = "created"
    revision_count: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)

    def add_event(self, kind: str, message: str, **extra: Any) -> None:
        elapsed_ms = int((time.monotonic() - self.started_at) * 1000)
        self.events.append(
            {"kind": kind, "message": message, "elapsed_ms": elapsed_ms, **extra}
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "repo_path": self.repo_path,
            "document_type": self.document_type,
            "model": self.model,
            "llm_mode": self.llm_mode,
            "file_count": len(self.file_inventory),
            "analysis": self.analysis,
            "document_plan": self.document_plan,
            "draft": self.draft,
            "issues": self.issues,
            "status": self.status,
            "revision_count": self.revision_count,
            "events": self.events,
        }
