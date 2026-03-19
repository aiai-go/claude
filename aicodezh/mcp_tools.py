"""Custom in-process MCP tools for claudezh.

Provides project-specific tools that run in-process via the claude-agent-sdk
MCP server API, giving Claude enhanced abilities beyond built-in tools.

Tools:
    - Project Memory: persistent key-value store per project
    - Code Stats: lines of code / language breakdown
    - Dependency Check: detect package manager & outdated deps
    - Git Enhanced: rich git history / blame / change summaries
    - Environment Detection: OS, runtimes, disk, memory
    - Quick Notes: timestamped notes with search
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CLAUDEZH_DIR = Path.home() / ".claudezh"
MEMORY_DIR = CLAUDEZH_DIR / "project_memory"
NOTES_DIR = CLAUDEZH_DIR / "notes"

# File extension -> language mapping
EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C", ".h": "C/C++ Header",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".r": "R", ".R": "R",
    ".scala": "Scala",
    ".lua": "Lua",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SASS", ".less": "LESS",
    ".sql": "SQL",
    ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown", ".rst": "reStructuredText",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".ml": "OCaml", ".mli": "OCaml",
    ".nim": "Nim",
    ".zig": "Zig",
}

# Directories to skip during code stats
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "vendor", ".cargo", "coverage",
    ".eggs", "*.egg-info", ".hg", ".svn",
}


# ---------------------------------------------------------------------------
# Helper: text response for MCP
# ---------------------------------------------------------------------------

def _text(content: str) -> dict[str, Any]:
    """Return standard MCP text response."""
    return {"content": [{"type": "text", "text": content}]}


def _json_text(data: Any) -> dict[str, Any]:
    """Return JSON-serialized MCP text response."""
    return _text(json.dumps(data, ensure_ascii=False, indent=2))


def _run(cmd: list[str], cwd: str | None = None, timeout: int = 30) -> str:
    """Run a subprocess and return stdout, or error string."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd
        )
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except FileNotFoundError:
        return f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return f"command timed out after {timeout}s"
    except Exception as e:
        return f"error: {e}"


def _project_hash(path: str = ".") -> str:
    """Generate a stable hash for a project path."""
    real = os.path.realpath(os.path.expanduser(path))
    return hashlib.md5(real.encode()).hexdigest()[:12]


def _memory_path(project_path: str = ".") -> Path:
    """Get the memory JSON file path for a project."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{_project_hash(project_path)}.json"


def _load_memory(project_path: str = ".") -> dict:
    """Load project memory from disk."""
    p = _memory_path(project_path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_memory(data: dict, project_path: str = ".") -> None:
    """Save project memory to disk."""
    p = _memory_path(project_path)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ===================================================================
# Tool implementations (all async, all accept dict args)
# ===================================================================

# --- Project Memory ---

async def _project_memory_read(args: dict) -> dict:
    """Read a value from project-specific memory."""
    key = args.get("key", "")
    project = args.get("project_path", ".")
    if not key:
        return _text("Error: 'key' is required")
    mem = _load_memory(project)
    if key in mem:
        value = mem[key]
        return _text(json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value)
    return _text(f"Key '{key}' not found in project memory.")


async def _project_memory_write(args: dict) -> dict:
    """Write a value to project-specific memory."""
    key = args.get("key", "")
    value = args.get("value", "")
    project = args.get("project_path", ".")
    if not key:
        return _text("Error: 'key' is required")
    mem = _load_memory(project)
    mem[key] = value
    mem["_updated_at"] = datetime.now().isoformat()
    _save_memory(mem, project)
    return _text(f"Saved key '{key}' to project memory.")


async def _project_memory_list(args: dict) -> dict:
    """List all keys in project memory."""
    project = args.get("project_path", ".")
    mem = _load_memory(project)
    keys = [k for k in mem if not k.startswith("_")]
    if not keys:
        return _text("Project memory is empty.")
    result = {"keys": keys, "count": len(keys)}
    return _json_text(result)


# --- Code Stats ---

async def _code_stats(args: dict) -> dict:
    """Count lines of code by language, file count, and largest files."""
    root = Path(args.get("path", ".")).resolve()
    if not root.exists():
        return _text(f"Path does not exist: {root}")

    lang_lines: Counter = Counter()
    lang_files: Counter = Counter()
    file_sizes: list[tuple[str, int]] = []
    total_files = 0
    total_lines = 0

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            ext = Path(fname).suffix.lower()
            lang = EXT_LANG.get(ext)
            if not lang:
                continue

            filepath = Path(dirpath) / fname
            try:
                lines = filepath.read_text(encoding="utf-8", errors="ignore").count("\n")
            except (OSError, PermissionError):
                continue

            lang_lines[lang] += lines
            lang_files[lang] += 1
            total_files += 1
            total_lines += lines
            rel = str(filepath.relative_to(root))
            file_sizes.append((rel, lines))

    # Top 10 largest files
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    top_files = [{"file": f, "lines": l} for f, l in file_sizes[:10]]

    # Language breakdown sorted by lines
    breakdown = []
    for lang, lines in lang_lines.most_common():
        breakdown.append({
            "language": lang,
            "files": lang_files[lang],
            "lines": lines,
            "percent": round(lines / total_lines * 100, 1) if total_lines else 0,
        })

    result = {
        "root": str(root),
        "total_files": total_files,
        "total_lines": total_lines,
        "languages": breakdown,
        "largest_files": top_files,
    }
    return _json_text(result)


# --- Dependency Check ---

async def _check_dependencies(args: dict) -> dict:
    """Detect package manager and list outdated dependencies."""
    root = Path(args.get("path", ".")).resolve()
    results: dict[str, Any] = {"root": str(root), "managers": []}

    # package.json (npm/yarn/pnpm)
    pkg_json = root / "package.json"
    if pkg_json.exists():
        mgr: dict[str, Any] = {"type": "npm", "file": "package.json"}
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            deps = dict(pkg.get("dependencies", {}))
            dev_deps = dict(pkg.get("devDependencies", {}))
            mgr["dependencies"] = len(deps)
            mgr["devDependencies"] = len(dev_deps)
        except Exception:
            mgr["error"] = "Failed to parse package.json"

        # Check outdated
        outdated = _run(["npm", "outdated", "--json"], cwd=str(root), timeout=60)
        if outdated and outdated.startswith("{"):
            try:
                mgr["outdated"] = json.loads(outdated)
            except json.JSONDecodeError:
                mgr["outdated_raw"] = outdated[:500]
        results["managers"].append(mgr)

    # requirements.txt (pip)
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        mgr = {"type": "pip", "file": "requirements.txt"}
        try:
            lines = [l.strip() for l in req_txt.read_text().splitlines() if l.strip() and not l.startswith("#")]
            mgr["packages"] = len(lines)
        except Exception:
            mgr["error"] = "Failed to parse requirements.txt"

        outdated = _run(
            ["pip", "list", "--outdated", "--format", "json"],
            cwd=str(root), timeout=60,
        )
        if outdated and outdated.startswith("["):
            try:
                mgr["outdated"] = json.loads(outdated)
            except json.JSONDecodeError:
                mgr["outdated_raw"] = outdated[:500]
        results["managers"].append(mgr)

    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and not req_txt.exists():
        mgr = {"type": "pip/poetry", "file": "pyproject.toml"}
        results["managers"].append(mgr)

    # Cargo.toml (Rust)
    cargo = root / "Cargo.toml"
    if cargo.exists():
        mgr = {"type": "cargo", "file": "Cargo.toml"}
        outdated = _run(["cargo", "outdated", "--format", "json"], cwd=str(root), timeout=60)
        if outdated and outdated.startswith("{"):
            try:
                mgr["outdated"] = json.loads(outdated)
            except json.JSONDecodeError:
                pass
        results["managers"].append(mgr)

    # go.mod (Go)
    gomod = root / "go.mod"
    if gomod.exists():
        mgr = {"type": "go", "file": "go.mod"}
        results["managers"].append(mgr)

    if not results["managers"]:
        return _text("No recognized package manager files found.")

    return _json_text(results)


# --- Git Enhanced ---

async def _git_summary(args: dict) -> dict:
    """Rich git history summary: commits per author, files changed, insertions/deletions."""
    days = args.get("days", 7)
    cwd = args.get("cwd", ".")

    since = f"--since={days} days ago"

    # Commit count per author
    log = _run(
        ["git", "log", since, "--format=%aN", "--no-merges"],
        cwd=cwd, timeout=15,
    )
    if "not a git repository" in log.lower() or "command not found" in log.lower():
        return _text(f"Not a git repository or git not available: {log}")

    author_counts: Counter = Counter()
    if log:
        for name in log.splitlines():
            author_counts[name.strip()] += 1

    # Total stats
    shortstat = _run(
        ["git", "log", since, "--no-merges", "--shortstat", "--format="],
        cwd=cwd, timeout=15,
    )
    total_insertions = 0
    total_deletions = 0
    total_files_changed = 0
    for line in (shortstat or "").splitlines():
        line = line.strip()
        if not line:
            continue
        # "3 files changed, 10 insertions(+), 2 deletions(-)"
        import re
        m_files = re.search(r"(\d+) files? changed", line)
        m_ins = re.search(r"(\d+) insertions?", line)
        m_del = re.search(r"(\d+) deletions?", line)
        if m_files:
            total_files_changed += int(m_files.group(1))
        if m_ins:
            total_insertions += int(m_ins.group(1))
        if m_del:
            total_deletions += int(m_del.group(1))

    # Recent commits (last 20)
    recent = _run(
        ["git", "log", since, "--no-merges", "--format=%h|%aN|%ar|%s", "-20"],
        cwd=cwd, timeout=15,
    )
    commits = []
    for line in (recent or "").splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "when": parts[2],
                "message": parts[3],
            })

    result = {
        "period": f"last {days} days",
        "total_commits": sum(author_counts.values()),
        "authors": dict(author_counts.most_common()),
        "files_changed": total_files_changed,
        "insertions": total_insertions,
        "deletions": total_deletions,
        "recent_commits": commits,
    }
    return _json_text(result)


async def _git_blame_summary(args: dict) -> dict:
    """Who wrote which parts of a file."""
    filepath = args.get("file", "")
    cwd = args.get("cwd", ".")
    if not filepath:
        return _text("Error: 'file' is required")

    blame = _run(
        ["git", "blame", "--line-porcelain", filepath],
        cwd=cwd, timeout=30,
    )
    if "not a git repository" in blame.lower() or "no such" in blame.lower():
        return _text(f"Error: {blame}")

    author_lines: Counter = Counter()
    for line in blame.splitlines():
        if line.startswith("author "):
            author_lines[line[7:].strip()] += 1

    total = sum(author_lines.values())
    breakdown = []
    for author, lines in author_lines.most_common():
        breakdown.append({
            "author": author,
            "lines": lines,
            "percent": round(lines / total * 100, 1) if total else 0,
        })

    return _json_text({"file": filepath, "total_lines": total, "authors": breakdown})


async def _git_changes_since(args: dict) -> dict:
    """Summary of recent changes since a given ref."""
    ref = args.get("ref", "HEAD~10")
    cwd = args.get("cwd", ".")

    # Diffstat
    diffstat = _run(["git", "diff", "--stat", ref], cwd=cwd, timeout=15)
    # Changed files
    files = _run(["git", "diff", "--name-only", ref], cwd=cwd, timeout=15)
    # Log
    log = _run(
        ["git", "log", f"{ref}..HEAD", "--no-merges", "--format=%h|%aN|%ar|%s"],
        cwd=cwd, timeout=15,
    )

    commits = []
    for line in (log or "").splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({
                "hash": parts[0], "author": parts[1],
                "when": parts[2], "message": parts[3],
            })

    changed = [f for f in (files or "").splitlines() if f.strip()]
    return _json_text({
        "ref": ref,
        "commits": commits,
        "files_changed": changed,
        "diffstat": diffstat or "",
    })


# --- Environment Detection ---

async def _detect_environment(args: dict) -> dict:
    """Detect OS, runtimes, installed tools, disk space, memory."""
    info: dict[str, Any] = {}

    # OS
    info["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "hostname": platform.node(),
    }

    # Python
    info["python"] = {
        "version": platform.python_version(),
        "executable": shutil.which("python3") or shutil.which("python") or "not found",
    }

    # Node
    node_ver = _run(["node", "--version"], timeout=5)
    info["node"] = node_ver if "not found" not in node_ver else None

    # npm
    npm_ver = _run(["npm", "--version"], timeout=5)
    info["npm"] = npm_ver if "not found" not in npm_ver else None

    # Git
    git_ver = _run(["git", "--version"], timeout=5)
    info["git"] = git_ver if "not found" not in git_ver else None

    # Docker
    docker_ver = _run(["docker", "--version"], timeout=5)
    info["docker"] = docker_ver if "not found" not in docker_ver else None

    # Rust
    rustc_ver = _run(["rustc", "--version"], timeout=5)
    info["rust"] = rustc_ver if "not found" not in rustc_ver else None

    # Go
    go_ver = _run(["go", "version"], timeout=5)
    info["go"] = go_ver if "not found" not in go_ver else None

    # Disk space
    try:
        usage = shutil.disk_usage("/")
        info["disk"] = {
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "percent_used": round(usage.used / usage.total * 100, 1),
        }
    except Exception:
        info["disk"] = "unavailable"

    # Memory (Linux)
    if platform.system() == "Linux":
        try:
            meminfo = Path("/proc/meminfo").read_text()
            mem = {}
            for line in meminfo.splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]  # kB value
                    if key in ("MemTotal", "MemAvailable", "MemFree"):
                        mem[key] = round(int(val) / (1024 * 1024), 1)  # GB
            info["memory_gb"] = mem
        except Exception:
            info["memory_gb"] = "unavailable"

    return _json_text(info)


# --- Quick Notes ---

async def _note_add(args: dict) -> dict:
    """Add a timestamped note."""
    text = args.get("text", "").strip()
    if not text:
        return _text("Error: 'text' is required")

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    note_file = NOTES_DIR / f"{today}.md"

    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"- [{timestamp}] {text}\n"

    with open(note_file, "a", encoding="utf-8") as f:
        f.write(entry)

    return _text(f"Note added to {today}.md")


async def _note_list(args: dict) -> dict:
    """List recent notes."""
    days = args.get("days", 7)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)

    notes: list[dict] = []
    today = datetime.now()
    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        note_file = NOTES_DIR / f"{date}.md"
        if note_file.exists():
            content = note_file.read_text(encoding="utf-8").strip()
            notes.append({"date": date, "content": content})

    if not notes:
        return _text(f"No notes found in the last {days} days.")
    return _json_text(notes)


async def _note_search(args: dict) -> dict:
    """Search notes by keyword."""
    keyword = args.get("keyword", "").strip()
    if not keyword:
        return _text("Error: 'keyword' is required")

    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    matches: list[dict] = []

    for note_file in sorted(NOTES_DIR.glob("*.md"), reverse=True):
        content = note_file.read_text(encoding="utf-8")
        if keyword.lower() in content.lower():
            # Extract matching lines
            matched_lines = [
                line.strip() for line in content.splitlines()
                if keyword.lower() in line.lower()
            ]
            matches.append({
                "date": note_file.stem,
                "matches": matched_lines,
            })

    if not matches:
        return _text(f"No notes matching '{keyword}'.")
    return _json_text(matches)


# ===================================================================
# MCP Server factory
# ===================================================================

def create_claudezh_mcp_server():
    """Create and return an MCP server config with all claudezh custom tools.

    Returns:
        McpSdkServerConfig ready to pass to ClaudeAgentOptions.mcp_servers
    """
    from claude_agent_sdk import create_sdk_mcp_server, tool

    # --- Project Memory tools ---

    @tool("project_memory_read", "Read a value from project-specific persistent memory. Use this to recall things about the current project across sessions.", {"key": str, "project_path": str})
    async def t_memory_read(args):
        return await _project_memory_read(args)

    @tool("project_memory_write", "Write a key-value pair to project-specific persistent memory. Use this to remember important facts about the project for future sessions.", {"key": str, "value": str, "project_path": str})
    async def t_memory_write(args):
        return await _project_memory_write(args)

    @tool("project_memory_list", "List all keys stored in project memory.", {"project_path": str})
    async def t_memory_list(args):
        return await _project_memory_list(args)

    # --- Code Stats ---

    @tool("code_stats", "Count lines of code by programming language, file count, and list largest files in a project.", {"path": str})
    async def t_code_stats(args):
        return await _code_stats(args)

    # --- Dependency Check ---

    @tool("check_dependencies", "Detect package managers (npm, pip, cargo, go) and list outdated dependencies.", {"path": str})
    async def t_deps(args):
        return await _check_dependencies(args)

    # --- Git Enhanced ---

    @tool(
        "git_summary",
        "Rich git history summary: commits per author, files changed, insertions/deletions over a period.",
        {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 7)"},
                "cwd": {"type": "string", "description": "Working directory (default '.')"},
            },
            "required": [],
        },
    )
    async def t_git_summary(args):
        return await _git_summary(args)

    @tool("git_blame_summary", "Show who wrote which parts of a file (authorship breakdown).", {"file": str, "cwd": str})
    async def t_git_blame(args):
        return await _git_blame_summary(args)

    @tool(
        "git_changes_since",
        "Summary of changes since a given git ref (default HEAD~10): commits, files changed, diffstat.",
        {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Git ref to compare from (default HEAD~10)"},
                "cwd": {"type": "string", "description": "Working directory (default '.')"},
            },
            "required": [],
        },
    )
    async def t_git_changes(args):
        return await _git_changes_since(args)

    # --- Environment Detection ---

    @tool(
        "detect_environment",
        "Detect system environment: OS, Python/Node/Git/Docker/Rust/Go versions, disk space, memory.",
        {
            "type": "object",
            "properties": {},
            "required": [],
        },
    )
    async def t_env(args):
        return await _detect_environment(args)

    # --- Quick Notes ---

    @tool("note_add", "Add a timestamped note to the daily notes file. Notes persist in ~/.claudezh/notes/.", {"text": str})
    async def t_note_add(args):
        return await _note_add(args)

    @tool(
        "note_list",
        "List recent notes from the last N days.",
        {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back (default 7)"},
            },
            "required": [],
        },
    )
    async def t_note_list(args):
        return await _note_list(args)

    @tool("note_search", "Search all notes by keyword.", {"keyword": str})
    async def t_note_search(args):
        return await _note_search(args)

    # --- Create server ---

    all_tools = [
        t_memory_read, t_memory_write, t_memory_list,
        t_code_stats,
        t_deps,
        t_git_summary, t_git_blame, t_git_changes,
        t_env,
        t_note_add, t_note_list, t_note_search,
    ]

    server_config = create_sdk_mcp_server(
        name="claudezh-tools",
        version="1.0.0",
        tools=all_tools,
    )

    return server_config


# ===================================================================
# Tool name -> Chinese name mapping (for CLI display)
# ===================================================================

MCP_TOOL_NAMES_ZH = {
    "project_memory_read": "读取项目记忆",
    "project_memory_write": "写入项目记忆",
    "project_memory_list": "列出项目记忆",
    "code_stats": "代码统计",
    "check_dependencies": "依赖检查",
    "git_summary": "Git 概览",
    "git_blame_summary": "Git 归属分析",
    "git_changes_since": "Git 变更摘要",
    "detect_environment": "环境检测",
    "note_add": "添加笔记",
    "note_list": "列出笔记",
    "note_search": "搜索笔记",
}
