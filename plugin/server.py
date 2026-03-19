#!/usr/bin/env python3
"""Standalone MCP server for the @aiai-go/claude DXT plugin.

Runs as a stdio JSON-RPC 2.0 server implementing the MCP protocol.
Provides 12 custom tools: project memory, code stats, git analysis,
environment detection, and quick notes.

Usage:
    python3 server.py
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CLAUDEZH_DIR = Path.home() / ".claudezh"
MEMORY_DIR = CLAUDEZH_DIR / "project_memory"
NOTES_DIR = CLAUDEZH_DIR / "notes"

EXT_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".jsx": "JavaScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".go": "Go", ".rs": "Rust",
    ".c": "C", ".h": "C/C++ Header",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++ Header",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".less": "LESS",
    ".sql": "SQL", ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML", ".xml": "XML",
    ".md": "Markdown", ".vue": "Vue", ".svelte": "Svelte", ".dart": "Dart",
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "target", "vendor", ".cargo", "coverage",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd, cwd=None, timeout=30):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except FileNotFoundError:
        return f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return f"command timed out after {timeout}s"
    except Exception as e:
        return f"error: {e}"


def _project_hash(path="."):
    real = os.path.realpath(os.path.expanduser(path))
    return hashlib.md5(real.encode()).hexdigest()[:12]


def _memory_path(project_path="."):
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return MEMORY_DIR / f"{_project_hash(project_path)}.json"


def _load_memory(project_path="."):
    p = _memory_path(project_path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_memory(data, project_path="."):
    p = _memory_path(project_path)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _text(content):
    return [{"type": "text", "text": content}]


def _json_text(data):
    return _text(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_project_memory_read(args):
    key = args.get("key", "")
    project = args.get("project_path", ".")
    if not key:
        return _text("Error: 'key' is required")
    mem = _load_memory(project)
    if key in mem:
        v = mem[key]
        return _text(json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v)
    return _text(f"Key '{key}' not found in project memory.")


def tool_project_memory_write(args):
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


def tool_project_memory_list(args):
    project = args.get("project_path", ".")
    mem = _load_memory(project)
    keys = [k for k in mem if not k.startswith("_")]
    if not keys:
        return _text("Project memory is empty.")
    return _json_text({"keys": keys, "count": len(keys)})


def tool_code_stats(args):
    root = Path(args.get("path", ".")).resolve()
    if not root.exists():
        return _text(f"Path does not exist: {root}")
    lang_lines = Counter()
    lang_files = Counter()
    file_sizes = []
    total_files = total_lines = 0
    for dirpath, dirnames, filenames in os.walk(root):
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
            file_sizes.append((str(filepath.relative_to(root)), lines))
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    breakdown = []
    for lang, lines in lang_lines.most_common():
        breakdown.append({"language": lang, "files": lang_files[lang], "lines": lines,
                          "percent": round(lines / total_lines * 100, 1) if total_lines else 0})
    return _json_text({"root": str(root), "total_files": total_files, "total_lines": total_lines,
                       "languages": breakdown, "largest_files": [{"file": f, "lines": l} for f, l in file_sizes[:10]]})


def tool_check_dependencies(args):
    root = Path(args.get("path", ".")).resolve()
    results = {"root": str(root), "managers": []}
    pkg_json = root / "package.json"
    if pkg_json.exists():
        mgr = {"type": "npm", "file": "package.json"}
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
            mgr["dependencies"] = len(pkg.get("dependencies", {}))
            mgr["devDependencies"] = len(pkg.get("devDependencies", {}))
        except Exception:
            mgr["error"] = "Failed to parse package.json"
        results["managers"].append(mgr)
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        mgr = {"type": "pip", "file": "requirements.txt"}
        try:
            lines = [l.strip() for l in req_txt.read_text().splitlines() if l.strip() and not l.startswith("#")]
            mgr["packages"] = len(lines)
        except Exception:
            mgr["error"] = "Failed to parse"
        results["managers"].append(mgr)
    if not results["managers"]:
        return _text("No recognized package manager files found.")
    return _json_text(results)


def tool_git_summary(args):
    days = args.get("days", 7)
    cwd = args.get("cwd", ".")
    since = f"--since={days} days ago"
    log = _run(["git", "log", since, "--format=%aN", "--no-merges"], cwd=cwd, timeout=15)
    if "not a git repository" in log.lower() or "command not found" in log.lower():
        return _text(f"Not a git repository: {log}")
    author_counts = Counter()
    if log:
        for name in log.splitlines():
            author_counts[name.strip()] += 1
    shortstat = _run(["git", "log", since, "--no-merges", "--shortstat", "--format="], cwd=cwd, timeout=15)
    ins = dels = files_changed = 0
    for line in (shortstat or "").splitlines():
        line = line.strip()
        if not line: continue
        m = re.search(r"(\d+) files? changed", line)
        if m: files_changed += int(m.group(1))
        m = re.search(r"(\d+) insertions?", line)
        if m: ins += int(m.group(1))
        m = re.search(r"(\d+) deletions?", line)
        if m: dels += int(m.group(1))
    recent = _run(["git", "log", since, "--no-merges", "--format=%h|%aN|%ar|%s", "-20"], cwd=cwd, timeout=15)
    commits = []
    for line in (recent or "").splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1], "when": parts[2], "message": parts[3]})
    return _json_text({"period": f"last {days} days", "total_commits": sum(author_counts.values()),
                       "authors": dict(author_counts.most_common()), "files_changed": files_changed,
                       "insertions": ins, "deletions": dels, "recent_commits": commits})


def tool_git_blame_summary(args):
    filepath = args.get("file", "")
    cwd = args.get("cwd", ".")
    if not filepath:
        return _text("Error: 'file' is required")
    blame = _run(["git", "blame", "--line-porcelain", filepath], cwd=cwd, timeout=30)
    if "not a git repository" in blame.lower() or "no such" in blame.lower():
        return _text(f"Error: {blame}")
    author_lines = Counter()
    for line in blame.splitlines():
        if line.startswith("author "):
            author_lines[line[7:].strip()] += 1
    total = sum(author_lines.values())
    breakdown = [{"author": a, "lines": l, "percent": round(l / total * 100, 1) if total else 0}
                 for a, l in author_lines.most_common()]
    return _json_text({"file": filepath, "total_lines": total, "authors": breakdown})


def tool_git_changes_since(args):
    ref = args.get("ref", "HEAD~10")
    cwd = args.get("cwd", ".")
    diffstat = _run(["git", "diff", "--stat", ref], cwd=cwd, timeout=15)
    files = _run(["git", "diff", "--name-only", ref], cwd=cwd, timeout=15)
    log = _run(["git", "log", f"{ref}..HEAD", "--no-merges", "--format=%h|%aN|%ar|%s"], cwd=cwd, timeout=15)
    commits = []
    for line in (log or "").splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1], "when": parts[2], "message": parts[3]})
    changed = [f for f in (files or "").splitlines() if f.strip()]
    return _json_text({"ref": ref, "commits": commits, "files_changed": changed, "diffstat": diffstat or ""})


def tool_detect_environment(args):
    info = {}
    info["os"] = {"system": platform.system(), "release": platform.release(),
                  "version": platform.version(), "machine": platform.machine(), "hostname": platform.node()}
    info["python"] = {"version": platform.python_version(),
                      "executable": shutil.which("python3") or shutil.which("python") or "not found"}
    for name, cmd in [("node", ["node", "--version"]), ("npm", ["npm", "--version"]),
                      ("git", ["git", "--version"]), ("docker", ["docker", "--version"])]:
        ver = _run(cmd, timeout=5)
        info[name] = ver if "not found" not in ver else None
    try:
        usage = shutil.disk_usage("/")
        info["disk"] = {"total_gb": round(usage.total / (1024**3), 1), "used_gb": round(usage.used / (1024**3), 1),
                        "free_gb": round(usage.free / (1024**3), 1), "percent_used": round(usage.used / usage.total * 100, 1)}
    except Exception:
        info["disk"] = "unavailable"
    if platform.system() == "Linux":
        try:
            meminfo = Path("/proc/meminfo").read_text()
            mem = {}
            for line in meminfo.splitlines():
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    if key in ("MemTotal", "MemAvailable", "MemFree"):
                        mem[key] = round(int(val) / (1024 * 1024), 1)
            info["memory_gb"] = mem
        except Exception:
            info["memory_gb"] = "unavailable"
    return _json_text(info)


def tool_note_add(args):
    text = args.get("text", "").strip()
    if not text:
        return _text("Error: 'text' is required")
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    note_file = NOTES_DIR / f"{today}.md"
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(note_file, "a", encoding="utf-8") as f:
        f.write(f"- [{timestamp}] {text}\n")
    return _text(f"Note added to {today}.md")


def tool_note_list(args):
    days = args.get("days", 7)
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    notes = []
    today = datetime.now()
    for i in range(days):
        date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        note_file = NOTES_DIR / f"{date}.md"
        if note_file.exists():
            notes.append({"date": date, "content": note_file.read_text(encoding="utf-8").strip()})
    if not notes:
        return _text(f"No notes found in the last {days} days.")
    return _json_text(notes)


def tool_note_search(args):
    keyword = args.get("keyword", "").strip()
    if not keyword:
        return _text("Error: 'keyword' is required")
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    matches = []
    for note_file in sorted(NOTES_DIR.glob("*.md"), reverse=True):
        content = note_file.read_text(encoding="utf-8")
        if keyword.lower() in content.lower():
            matched_lines = [line.strip() for line in content.splitlines() if keyword.lower() in line.lower()]
            matches.append({"date": note_file.stem, "matches": matched_lines})
    if not matches:
        return _text(f"No notes matching '{keyword}'.")
    return _json_text(matches)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOLS = {
    "project_memory_read": {
        "handler": tool_project_memory_read,
        "description": "Read a value from project-specific persistent memory",
        "inputSchema": {"type": "object", "properties": {
            "key": {"type": "string", "description": "The memory key to read"},
            "project_path": {"type": "string", "description": "Project path (default '.')", "default": "."},
        }, "required": ["key"]},
    },
    "project_memory_write": {
        "handler": tool_project_memory_write,
        "description": "Write a key-value pair to project-specific persistent memory",
        "inputSchema": {"type": "object", "properties": {
            "key": {"type": "string", "description": "The memory key"},
            "value": {"type": "string", "description": "The value to store"},
            "project_path": {"type": "string", "description": "Project path (default '.')", "default": "."},
        }, "required": ["key", "value"]},
    },
    "project_memory_list": {
        "handler": tool_project_memory_list,
        "description": "List all keys stored in project memory",
        "inputSchema": {"type": "object", "properties": {
            "project_path": {"type": "string", "description": "Project path (default '.')", "default": "."},
        }, "required": []},
    },
    "code_stats": {
        "handler": tool_code_stats,
        "description": "Count lines of code by programming language with file breakdown",
        "inputSchema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Directory to analyze (default '.')", "default": "."},
        }, "required": []},
    },
    "check_dependencies": {
        "handler": tool_check_dependencies,
        "description": "Detect package managers and list outdated dependencies",
        "inputSchema": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Project root (default '.')", "default": "."},
        }, "required": []},
    },
    "git_summary": {
        "handler": tool_git_summary,
        "description": "Git history summary: commits per author, insertions, deletions",
        "inputSchema": {"type": "object", "properties": {
            "days": {"type": "integer", "description": "Days to look back (default 7)", "default": 7},
            "cwd": {"type": "string", "description": "Working directory (default '.')", "default": "."},
        }, "required": []},
    },
    "git_blame_summary": {
        "handler": tool_git_blame_summary,
        "description": "File authorship breakdown via git blame",
        "inputSchema": {"type": "object", "properties": {
            "file": {"type": "string", "description": "File path to analyze"},
            "cwd": {"type": "string", "description": "Working directory (default '.')", "default": "."},
        }, "required": ["file"]},
    },
    "git_changes_since": {
        "handler": tool_git_changes_since,
        "description": "Summary of changes since a git ref",
        "inputSchema": {"type": "object", "properties": {
            "ref": {"type": "string", "description": "Git ref (default HEAD~10)", "default": "HEAD~10"},
            "cwd": {"type": "string", "description": "Working directory (default '.')", "default": "."},
        }, "required": []},
    },
    "detect_environment": {
        "handler": tool_detect_environment,
        "description": "Detect OS, runtimes, disk space, and memory",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    "note_add": {
        "handler": tool_note_add,
        "description": "Add a timestamped quick note",
        "inputSchema": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Note text"},
        }, "required": ["text"]},
    },
    "note_list": {
        "handler": tool_note_list,
        "description": "List recent notes",
        "inputSchema": {"type": "object", "properties": {
            "days": {"type": "integer", "description": "Days to look back (default 7)", "default": 7},
        }, "required": []},
    },
    "note_search": {
        "handler": tool_note_search,
        "description": "Search notes by keyword",
        "inputSchema": {"type": "object", "properties": {
            "keyword": {"type": "string", "description": "Search keyword"},
        }, "required": ["keyword"]},
    },
}


# ---------------------------------------------------------------------------
# MCP stdio server
# ---------------------------------------------------------------------------

SERVER_INFO = {"name": "aiai-go-claude", "version": "0.2.0"}
CAPABILITIES = {"tools": {}}


def handle_request(msg):
    method = msg.get("method", "")
    msg_id = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "capabilities": CAPABILITIES, "serverInfo": SERVER_INFO}}

    elif method == "notifications/initialized":
        return None

    elif method == "tools/list":
        tools_list = [{"name": n, "description": s["description"], "inputSchema": s["inputSchema"]}
                      for n, s in TOOLS.items()]
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools_list}}

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        if tool_name not in TOOLS:
            return {"jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": _text(f"Unknown tool: {tool_name}"), "isError": True}}
        try:
            content = TOOLS[tool_name]["handler"](arguments)
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": content}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": msg_id,
                    "result": {"content": _text(f"Error: {e}"), "isError": True}}

    elif method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    else:
        if msg_id is not None:
            return {"jsonrpc": "2.0", "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}}
        return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None,
                                         "error": {"code": -32700, "message": "Parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        response = handle_request(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
