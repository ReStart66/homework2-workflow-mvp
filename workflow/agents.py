"""Workflow 中的两个 Agent。

- CodeAnalyzerAgent: 分析代码仓库，输出结构化 JSON（带一次 JSON 解析重试）。
- DocWriterAgent: 根据分析结果生成 Markdown 文档。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .llm import LLMClient
from .state import WorkflowState


def _extract_json(text: str) -> Dict[str, Any]:
    """从 LLM 输出中稳健地提取 JSON 对象。"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


class CodeAnalyzerAgent:
    """代码分析 Agent：把仓库内容转成结构化事实。"""

    name = "CodeAnalyzerAgent"

    SYSTEM_PROMPT = (
        "你是一名资深软件架构师，负责阅读代码并提取结构化事实。"
        "只输出一个合法的 JSON 对象，不要输出任何解释性文字。"
    )

    def run(
        self,
        state: WorkflowState,
        llm: LLMClient,
        analysis_mode: str = "full",
    ) -> Dict[str, Any]:
        state.add_event("agent_start", f"{self.name} 开始分析仓库", agent=self.name)
        user = self._build_prompt(state, analysis_mode)

        last_error: Optional[str] = None
        for attempt in range(1, 3):
            state.add_event("llm_call", f"{self.name} 请求 LLM（第 {attempt} 次）", agent=self.name)
            raw = llm.complete(self.SYSTEM_PROMPT, user, expect_json=True)
            try:
                analysis = _extract_json(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = str(exc)
                if attempt < 2:
                    state.add_event("retry", f"{self.name} JSON 解析失败，准备重试: {exc}", agent=self.name)
                    continue
                state.add_event("agent_error", f"{self.name} 输出不是合法 JSON: {exc}", agent=self.name)
                raise RuntimeError(f"{self.name} 未能输出合法 JSON: {exc}") from exc

            state.analysis = analysis
            state.add_event(
                "agent_done",
                f"{self.name} 完成，识别到 {len(analysis.get('modules', []))} 个模块",
                agent=self.name,
            )
            return analysis

        raise RuntimeError(f"{self.name} 重试后仍失败: {last_error}")

    def _build_prompt(self, state: WorkflowState, analysis_mode: str) -> str:
        if analysis_mode == "summary":
            detail_rule = "分析粒度 summary：每个模块只需概括 purpose，public_api 可简略。"
        else:
            detail_rule = "分析粒度 full：尽量提取 path、purpose、public_api、dependencies 与 evidence。"

        parts = [
            f"Repository: {state.repo_path}",
            f"Document type: {state.document_type}",
            "请分析以下代码仓库，并输出 JSON，包含这些字段：",
            "- project_name: 项目名称",
            "- language: 主要语言",
            "- entry_points: 入口文件列表",
            "- dependencies: 外部或内部依赖列表",
            "- modules: 数组，每项包含 path、purpose、public_api、dependencies、evidence",
            "- architecture: 包含 components 和 relationships",
            "- uncertainties: 无法从代码确认的事项",
            "",
            "要求：只能描述代码中确实存在的内容；不确定的地方写入 uncertainties。",
            detail_rule,
            "",
            "### FILES",
            "",
        ]
        for f in state.file_inventory:
            parts.append(f"### FILE: {f.path} [{f.language}, {f.lines} lines]")
            parts.append(f.content)
            parts.append("")
        return "\n".join(parts)


class DocWriterAgent:
    """文档编写 Agent：根据分析结果生成 Markdown。"""

    name = "DocWriterAgent"

    SYSTEM_PROMPT = (
        "你是一名严谨的技术文档工程师。"
        "根据提供的结构化分析结果编写 Markdown 文档，只能使用分析结果中确认的事实，"
        "不得编造安装命令、配置项或接口。"
    )

    def run(
        self,
        state: WorkflowState,
        llm: LLMClient,
        issues: Optional[List[str]] = None,
    ) -> str:
        action = "修订文档" if issues else "生成文档"
        state.add_event("agent_start", f"{self.name} 开始{action}", agent=self.name)
        user = self._build_prompt(state, issues)
        state.add_event("llm_call", f"{self.name} 请求 LLM", agent=self.name)
        draft = llm.complete(self.SYSTEM_PROMPT, user, expect_json=False)
        draft = draft.strip()
        if not draft:
            raise RuntimeError(f"{self.name} 输出为空")

        state.draft = draft
        state.add_event("agent_done", f"{self.name} 完成{action}，长度 {len(draft)} 字符", agent=self.name)
        return draft

    def _build_prompt(self, state: WorkflowState, issues: Optional[List[str]] = None) -> str:
        parts = [
            f"Document type: {state.document_type}",
            "",
        ]
        if state.document_type == "architecture":
            parts += [
                "生成《架构说明》文档，至少包含以下章节：",
                "## 架构概览",
                "## 组件",
                "## 依赖关系",
                "## 关键流程（如可确认）",
            ]
        else:
            parts += [
                "生成 README 文档，至少包含以下章节：",
                "## 项目简介",
                "## 项目结构",
                "## 安装与运行",
                "## 模块说明",
                "## 已知限制",
            ]
        parts += [
            "",
            "请基于下面的分析 JSON 生成文档，只能使用其中已确认的事实。",
        ]
        if issues:
            parts += ["", "### ISSUES", "上一版校验未通过，请修复以下问题："]
            parts += [f"- {i}" for i in issues]
        parts += [
            "",
            "### ANALYSIS_JSON",
            json.dumps(state.analysis, ensure_ascii=False, indent=2),
        ]
        return "\n".join(parts)
