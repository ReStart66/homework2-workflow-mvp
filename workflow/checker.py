"""确定性 Markdown 校验器。

不属于 LLM Agent，只做规则检查。发现问题后由编排器触发 DocWriterAgent 修订。
"""
from __future__ import annotations

import re
from typing import List

from .state import WorkflowState

REQUIRED_SECTIONS = {
    "readme": ["# ", "## 项目简介", "## 项目结构", "## 安装与运行", "## 模块说明"],
    "architecture": ["# ", "## 架构概览", "## 组件", "## 依赖关系"],
}

MIN_LENGTH = 200

FILE_PATTERN = re.compile(r"`([^`\n]+\.[A-Za-z0-9]{1,6})`")

# 文档中明确说明“不存在 / 未提供”的路径，不应视为错误引用。
NEGATION_MARKERS = (
    "未提供",
    "不存在",
    "未发现",
    "无法确认",
    "未确认",
    "not found",
    "does not exist",
)


def check_document(state: WorkflowState) -> List[str]:
    text = state.draft
    issues: List[str] = []

    required = REQUIRED_SECTIONS.get(state.document_type, [])
    for section in required:
        if section not in text:
            issues.append(f"缺少必需章节：{section.strip()}")

    if len(text) < MIN_LENGTH:
        issues.append(f"文档内容过短（{len(text)} 字符 < {MIN_LENGTH}）")

    if text.count("```") % 2 != 0:
        issues.append("代码块围栏 ``` 不配对")

    known_files = {f.path for f in state.file_inventory}
    known_files.update({f.path.split("/")[-1] for f in state.file_inventory})

    for line in text.splitlines():
        if any(marker in line for marker in NEGATION_MARKERS):
            continue
        for candidate in FILE_PATTERN.findall(line):
            if candidate.startswith(("http://", "https://", "#")):
                continue
            if candidate in known_files:
                continue
            # 没有目录层级且不在文件清单中的短名称，不强行判错。
            if "/" not in candidate:
                continue
            issues.append(f"文档引用了仓库中不存在的文件：{candidate}")

    return issues
