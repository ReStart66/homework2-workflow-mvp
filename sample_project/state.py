"""共享状态。"""
from dataclasses import dataclass, field
from typing import List


@dataclass
class WorkflowState:
    topic: str
    facts: List[str] = field(default_factory=list)
