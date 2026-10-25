"""LLM 客户端。

- 真实模式：调用 OpenAI 兼容的 Chat Completions 接口，带自动重试；
- Mock 模式：完全离线，根据输入结构生成可复现的占位结果。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}


class LLMClient:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        api_key: Optional[str] = None,
        mock: bool = False,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.mock = mock or not api_key

    def complete(self, system: str, user: str, expect_json: bool = False) -> str:
        if self.mock:
            return self._mock_complete(user, expect_json)
        return self._real_complete(system, user, expect_json)

    # ------------------------------------------------------------------ 真实模式
    def _real_complete(self, system: str, user: str, expect_json: bool) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}

        url = f"{self.base_url}/chat/completions"
        last_error: Optional[str] = None

        for attempt in range(1, 4):
            try:
                request = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=180) as response:
                    data = json.loads(response.read().decode("utf-8"))
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise RuntimeError(f"LLM 响应格式异常: {json.dumps(data)[:500]}") from exc
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code in RETRYABLE_HTTP_CODES and attempt < 3:
                    last_error = f"HTTP {exc.code}"
                    time.sleep(attempt)
                    continue
                raise RuntimeError(f"LLM 请求失败 HTTP {exc.code}: {body}") from exc
            except urllib.error.URLError as exc:
                if attempt < 3:
                    last_error = f"网络错误 {exc.reason}"
                    time.sleep(attempt)
                    continue
                raise RuntimeError(f"LLM 网络错误: {exc.reason}") from exc

        raise RuntimeError(f"LLM 调用重试 3 次后仍失败: {last_error}")

    # ------------------------------------------------------------------ Mock 模式
    def _mock_complete(self, user: str, expect_json: bool) -> str:
        if expect_json:
            return self._mock_analysis(user)
        return self._mock_document(user)

    def _mock_analysis(self, user: str) -> str:
        repo_match = re.search(r"Repository:\s*(.+)", user)
        project_name = repo_match.group(1).strip() if repo_match else "unknown-project"

        paths: List[str] = re.findall(r"^### FILE:\s*(\S+)", user, flags=re.MULTILINE)
        paths = list(dict.fromkeys(paths))

        languages: Dict[str, str] = {}
        for block in re.findall(
            r"^### FILE:\s*(\S+)\s*\[(\w+),", user, flags=re.MULTILINE
        ):
            languages[block[0]] = block[1]

        modules = []
        for p in paths:
            modules.append(
                {
                    "path": p,
                    "purpose": f"实现与 {p} 相关的功能（Mock 占位描述，接入真实 LLM 后自动补充）",
                    "public_api": [],
                    "dependencies": [],
                    "evidence": ["file present in repository"],
                }
            )

        entry_candidates = [p for p in paths if p.endswith(("main.py", "main.js", "main.ts", "app.py", "index.js", "index.ts"))]
        entry_points = entry_candidates[:3] or paths[:1]

        components = []
        for p in paths:
            name = p.split("/")[0]
            if name not in components:
                components.append(name)

        result = {
            "project_name": project_name,
            "language": self._dominant_language(paths, languages),
            "entry_points": entry_points,
            "dependencies": [],
            "modules": modules,
            "architecture": {
                "components": components,
                "relationships": ["Mock 模式未推断具体依赖关系，接入真实 LLM 后自动补充"],
            },
            "uncertainties": [
                "当前为 Mock 模式：模块用途、接口与依赖关系为占位内容，仅供流程演示。"
            ],
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def _mock_document(self, user: str) -> str:
        match = re.search(r"### ANALYSIS_JSON\n(.*?)(?:\n### |\Z)", user, flags=re.DOTALL)
        analysis: Dict[str, Any] = {}
        if match:
            try:
                analysis = json.loads(match.group(1))
            except json.JSONDecodeError:
                analysis = {}

        doc_type_match = re.search(r"Document type:\s*(\w+)", user)
        doc_type = doc_type_match.group(1) if doc_type_match else "readme"
        project_name = analysis.get("project_name", "unknown-project")

        modules = analysis.get("modules", []) or []
        entry_points = analysis.get("entry_points", []) or []
        components = (analysis.get("architecture") or {}).get("components", []) or []
        relationships = (analysis.get("architecture") or {}).get("relationships", []) or []

        if doc_type == "architecture":
            return self._mock_architecture(project_name, components, relationships)

        lines = [
            f"# {project_name}",
            "",
            "> 本文档由 Simple Workflow MVP 自动生成（Mock 模式）。",
            "",
            "## 项目简介",
            "",
            f"{project_name} 是一个用于演示 Simple Workflow MVP 的代码仓库。"
            "该仓库展示了一个由多个 Agent 协作完成任务的最小可运行示例。",
            "",
            "## 项目结构",
            "",
        ]
        for m in modules:
            lines.append(f"- `{m['path']}` — {m['purpose']}")
        lines += ["", "## 入口点", ""]
        if entry_points:
            lines += [f"- `{p}`" for p in entry_points]
        else:
            lines.append("- 未识别到明确的入口点。")
        lines += ["", "## 安装与运行", ""]
        lines.append("本仓库未发现独立的依赖安装配置，启动方式需要结合实际入口点确认。")
        lines.append("")
        lines += ["", "## 模块说明", ""]
        for m in modules:
            lines.append(f"### {m['path']}")
            lines.append("")
            lines.append(m["purpose"])
            lines.append("")
        lines += ["", "## 已知限制", ""]
        uncertainties = analysis.get("uncertainties", []) or ["未发现明确的限制。"]
        for u in uncertainties:
            lines.append(f"- {u}")
        return "\n".join(lines)

    def _mock_architecture(self, project_name: str, components: List[str], relationships: List[str]) -> str:
        lines = [
            f"# {project_name} — 架构说明",
            "",
            "> 本文档由 Simple Workflow MVP 自动生成（Mock 模式）。",
            "",
            "## 架构概览",
            "",
            f"{project_name} 采用模块化结构，主要组件如下。",
            "",
            "## 组件",
            "",
        ]
        for c in components:
            lines.append(f"- {c}")
        lines += ["", "## 依赖关系", ""]
        if relationships:
            lines += [f"- {r}" for r in relationships]
        else:
            lines.append("- 未推断出明确的依赖关系。")
        lines += ["", "## 关键流程", ""]
        lines.append("- 当前为 Mock 模式，未推断出可确认的关键流程，接入真实 LLM 后会自动补充。")
        lines += ["", "## 扩展建议", ""]
        lines.append("- 可新增文档类型或替换 LLM 后端，架构本身保持不变。")
        return "\n".join(lines)

    @staticmethod
    def _dominant_language(paths: List[str], languages: Dict[str, str]) -> str:
        if not paths:
            return "Unknown"
        counts: Dict[str, int] = {}
        for p in paths:
            lang = languages.get(p, "Unknown")
            counts[lang] = counts.get(lang, 0) + 1
        return max(counts, key=lambda k: counts[k])
