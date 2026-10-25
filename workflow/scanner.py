"""代码仓库扫描器。

负责：
1. 遍历仓库并过滤无关目录；
2. 只保留感兴趣的文本文件；
3. 读取并截断文件内容；
4. 生成 FileRecord 列表。
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .state import FileRecord

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__",
    "node_modules", "venv", ".venv", "env", "dist", "build",
    "target", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".next", ".nuxt", "coverage", "htmlcov",
}

INTERESTING_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".c", ".cpp",
    ".rs", ".rb", ".php", ".sh", ".ps1", ".md", ".txt", ".json",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sql", ".css", ".html",
    ".xml", ".properties", ".cmd", ".bat",
}

LANGUAGE_BY_EXT = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".jsx": "JavaScript/JSX", ".tsx": "TypeScript/TSX", ".go": "Go",
    ".java": "Java", ".c": "C", ".cpp": "C++", ".rs": "Rust",
    ".rb": "Ruby", ".php": "PHP", ".sh": "Shell", ".ps1": "PowerShell",
    ".md": "Markdown", ".txt": "Text", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".ini": "INI",
    ".cfg": "Config", ".sql": "SQL", ".css": "CSS", ".html": "HTML",
    ".xml": "XML", ".properties": "Properties", ".cmd": "Batch", ".bat": "Batch",
}


def guess_language(path: Path) -> str:
    return LANGUAGE_BY_EXT.get(path.suffix.lower(), "Unknown")


def _read_text(path: Path, max_bytes: int) -> str:
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""


def scan_repository(
    repo_path: str,
    max_files: int = 60,
    max_file_bytes: int = 8000,
) -> List[FileRecord]:
    root = Path(repo_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"仓库路径不存在: {repo_path}")

    records: List[FileRecord] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue

        rel = path.relative_to(root)
        parts = rel.parts

        if any(part in SKIP_DIRS or part.startswith(".git") for part in parts):
            continue
        if any(part.startswith(".") and part not in {".gitignore", ".env.example", ".editorconfig"} for part in parts):
            continue
        if path.suffix.lower() not in INTERESTING_EXTENSIONS:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        content = _read_text(path, max_file_bytes)
        if content.strip() == "":
            continue

        records.append(
            FileRecord(
                path=rel.as_posix(),
                size=size,
                language=guess_language(path),
                lines=content.count("\n") + 1,
                content=content,
            )
        )
        if len(records) >= max_files:
            break

    return records
