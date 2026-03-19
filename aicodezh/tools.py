"""工具模块 — 提供文件操作、代码执行、项目分析等实用工具。"""

import os
import re
import shutil
import subprocess
import tempfile
from fnmatch import fnmatch
from pathlib import Path

# ---------------------------------------------------------------------------
# 安全 — 危险命令黑名单
# ---------------------------------------------------------------------------

_DANGEROUS_PATTERNS = [
    r"\brm\s+(-\w*r\w*f|--force|--recursive)\b",
    r"\brm\s+-rf\b",
    r"\bmkfs\b",
    r"\bdd\s+",
    r":.*>\s*/dev/sd",
    r"\bchmod\s+-R\s+777\b",
    r"\bformat\b",
    r">\s*/etc/",
]


def _is_dangerous(cmd: str) -> bool:
    """检查命令是否匹配危险模式。"""
    for pat in _DANGEROUS_PATTERNS:
        if re.search(pat, cmd):
            return True
    return False


# ---------------------------------------------------------------------------
# 1. 文件操作
# ---------------------------------------------------------------------------


def read_file(path: str) -> str:
    """读取文件内容，自动检测编码。

    依次尝试 utf-8 → gbk → latin-1（latin-1 不会失败）。
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")

    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    # latin-1 理论上不会失败，但以防万一
    return p.read_bytes().decode("latin-1")


def write_file(path: str, content: str) -> None:
    """写入文件，若文件已存在则先创建 .bak 备份。"""
    p = Path(path).expanduser().resolve()

    # 创建父目录
    p.parent.mkdir(parents=True, exist_ok=True)

    # 备份
    if p.exists():
        bak = p.with_suffix(p.suffix + ".bak")
        shutil.copy2(str(p), str(bak))

    p.write_text(content, encoding="utf-8")


def list_files(path: str = ".", pattern: str = "**/*") -> list[str]:
    """递归列出匹配 glob 模式的文件路径。

    自动跳过 .git / __pycache__ / node_modules 等目录。
    """
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory not found: {root}")

    skip_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox", ".mypy_cache"}
    results: list[str] = []

    for item in root.glob(pattern):
        # 跳过隐含在黑名单目录中的文件
        parts = item.relative_to(root).parts
        if any(part in skip_dirs for part in parts):
            continue
        if item.is_file():
            results.append(str(item))

    results.sort()
    return results


def search_in_files(
    pattern: str,
    path: str = ".",
    glob: str = "**/*",
) -> list[dict]:
    """在文件中搜索正则表达式，返回匹配行列表。

    每个匹配项: {"file": str, "line_num": int, "line": str}
    """
    regex = re.compile(pattern)
    files = list_files(path, glob)
    matches: list[dict] = []

    for fpath in files:
        try:
            content = read_file(fpath)
        except (OSError, PermissionError):
            continue

        for i, line in enumerate(content.splitlines(), start=1):
            if regex.search(line):
                matches.append({
                    "file": fpath,
                    "line_num": i,
                    "line": line,
                })

    return matches


# ---------------------------------------------------------------------------
# 2. 代码执行
# ---------------------------------------------------------------------------


def run_command(cmd: str, timeout: int = 30, allow_dangerous: bool = False) -> dict:
    """执行 Shell 命令，返回 {stdout, stderr, returncode}。

    危险命令默认被拦截，设 allow_dangerous=True 可强制执行。
    """
    if not allow_dangerous and _is_dangerous(cmd):
        return {
            "stdout": "",
            "stderr": f"Command blocked by safety policy (suspected dangerous operation): {cmd}",
            "returncode": -1,
        }

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out ({timeout}s): {cmd}",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Command execution failed: {e}",
            "returncode": -1,
        }


def run_python(code: str, timeout: int = 30) -> dict:
    """执行 Python 代码片段，返回 {stdout, stderr, returncode}。

    在独立子进程中执行以隔离副作用。
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        proc = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Python code execution timed out ({timeout}s)",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Python code execution failed: {e}",
            "returncode": -1,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass


# ---------------------------------------------------------------------------
# 3. 项目分析
# ---------------------------------------------------------------------------

# 框架 / 项目类型检测规则: (标志文件, 类型, 语言, 框架)
_PROJECT_SIGNATURES = [
    ("package.json", "node", "JavaScript/TypeScript", None),
    ("pyproject.toml", "python", "Python", None),
    ("setup.py", "python", "Python", None),
    ("requirements.txt", "python", "Python", None),
    ("Cargo.toml", "rust", "Rust", "Cargo"),
    ("go.mod", "go", "Go", None),
    ("pom.xml", "java", "Java", "Maven"),
    ("build.gradle", "java", "Java/Kotlin", "Gradle"),
    ("Gemfile", "ruby", "Ruby", None),
    ("composer.json", "php", "PHP", "Composer"),
]

_FRAMEWORK_HINTS = {
    "manage.py": "Django",
    "app.py": "Flask/FastAPI",
    "main.py": "FastAPI",
    "next.config.js": "Next.js",
    "nuxt.config.ts": "Nuxt",
    "angular.json": "Angular",
    "vue.config.js": "Vue",
    "vite.config.ts": "Vite",
    "tsconfig.json": "TypeScript",
}

# 文件扩展名 → 语言
_EXT_LANG = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript (React)",
    ".tsx": "TypeScript (React)",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sh": "Shell",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
}


def analyze_project(path: str = ".") -> dict:
    """分析项目目录，返回项目类型、语言、框架、关键文件等信息。"""
    root = Path(path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Directory not found: {root}")

    result: dict = {
        "path": str(root),
        "type": "unknown",
        "languages": [],
        "framework": None,
        "key_files": [],
        "file_stats": {},
    }

    # 检测项目类型
    for sig_file, proj_type, lang, framework in _PROJECT_SIGNATURES:
        if (root / sig_file).exists():
            result["type"] = proj_type
            if lang and lang not in result["languages"]:
                result["languages"].append(lang)
            if framework:
                result["framework"] = framework
            result["key_files"].append(sig_file)
            break

    # 检测框架
    for hint_file, fw in _FRAMEWORK_HINTS.items():
        if (root / hint_file).exists():
            result["framework"] = result["framework"] or fw
            result["key_files"].append(hint_file)

    # 统计文件扩展名
    ext_counts: dict[str, int] = {}
    try:
        all_files = list_files(str(root))
    except Exception:
        all_files = []

    for fpath in all_files:
        ext = Path(fpath).suffix.lower()
        if ext:
            ext_counts[ext] = ext_counts.get(ext, 0) + 1

    result["file_stats"] = dict(sorted(ext_counts.items(), key=lambda x: -x[1])[:15])

    # 补充语言检测
    for ext, lang in _EXT_LANG.items():
        if ext in ext_counts and lang not in result["languages"]:
            result["languages"].append(lang)

    # 常见关键文件
    common_key = [
        "README.md", "Makefile", "Dockerfile", "docker-compose.yml",
        ".gitignore", ".env.example", "LICENSE",
    ]
    for kf in common_key:
        if (root / kf).exists() and kf not in result["key_files"]:
            result["key_files"].append(kf)

    return result


def get_git_info(path: str = ".") -> dict:
    """获取 Git 仓库信息：分支、状态、最近提交。"""
    root = Path(path).expanduser().resolve()

    info: dict = {
        "is_git_repo": False,
        "branch": None,
        "status": None,
        "recent_commits": [],
    }

    # 检查是否为 git 仓库
    check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if check.returncode != 0:
        return info

    info["is_git_repo"] = True

    # 当前分支
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    info["branch"] = branch.stdout.strip() or None

    # 状态摘要
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    info["status"] = status.stdout.strip() or "clean"

    # 最近 5 条提交
    log = subprocess.run(
        ["git", "log", "--oneline", "-5", "--no-decorate"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if log.returncode == 0 and log.stdout.strip():
        info["recent_commits"] = log.stdout.strip().splitlines()

    return info


# ---------------------------------------------------------------------------
# 5. 工具注册表
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, dict] = {
    "read_file": {
        "function": read_file,
        "description": "Read file content (auto-detect encoding)",
        "params": {"path": "file path"},
    },
    "write_file": {
        "function": write_file,
        "description": "Write file (auto-backup existing files)",
        "params": {"path": "file path", "content": "file content"},
    },
    "list_files": {
        "function": list_files,
        "description": "List files in directory (supports glob patterns)",
        "params": {"path": "directory path", "pattern": "glob pattern"},
    },
    "search_in_files": {
        "function": search_in_files,
        "description": "Search file contents (regex)",
        "params": {"pattern": "search pattern", "path": "directory path", "glob": "file glob pattern"},
    },
    "run_command": {
        "function": run_command,
        "description": "Execute shell command",
        "params": {"cmd": "command string", "timeout": "timeout in seconds"},
    },
    "run_python": {
        "function": run_python,
        "description": "Execute Python code snippet",
        "params": {"code": "Python code", "timeout": "timeout in seconds"},
    },
    "analyze_project": {
        "function": analyze_project,
        "description": "Analyze project structure (languages, frameworks, key files)",
        "params": {"path": "project path"},
    },
    "get_git_info": {
        "function": get_git_info,
        "description": "Get Git repository info (branch, status, recent commits)",
        "params": {"path": "repository path"},
    },
}


def get_tool(name: str) -> dict | None:
    """按名称查找工具，返回工具信息字典或 None。"""
    return TOOL_REGISTRY.get(name)


def list_tools() -> list[dict]:
    """列出所有可用工具及说明。"""
    return [
        {"name": name, "description": info["description"], "params": info["params"]}
        for name, info in TOOL_REGISTRY.items()
    ]
