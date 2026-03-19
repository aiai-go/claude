"""安全钩子系统 — 拦截危险操作 + 审计日志 + 中文上下文注入。

架构:
    PreToolUse  hooks → 危险命令拦截 (Bash)
    PostToolUse hooks → 审计日志 (所有工具)
    UserPromptSubmit hooks → 中文上下文注入
    Notification hooks → 中文通知
"""

from __future__ import annotations

import logging
import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("claudezh.hooks")

# ---------------------------------------------------------------------------
# 危险命令模式
# ---------------------------------------------------------------------------

DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"rm\s+-rf\s+/", re.IGNORECASE), "递归删除根目录"),
    (re.compile(r"rm\s+-rf\s+~", re.IGNORECASE), "递归删除用户目录"),
    (re.compile(r"rm\s+-rf\s+\*", re.IGNORECASE), "递归删除所有文件"),
    (re.compile(r"mkfs\.", re.IGNORECASE), "格式化磁盘"),
    (re.compile(r"dd\s+if=", re.IGNORECASE), "磁盘直写"),
    (re.compile(r">\s*/dev/sd", re.IGNORECASE), "覆写磁盘设备"),
    (re.compile(r"git\s+push\s+--force", re.IGNORECASE), "强制推送"),
    (re.compile(r"git\s+reset\s+--hard", re.IGNORECASE), "硬重置"),
    (re.compile(r"DROP\s+TABLE", re.IGNORECASE), "删除数据表"),
    (re.compile(r"DROP\s+DATABASE", re.IGNORECASE), "删除数据库"),
    (re.compile(r"chmod\s+777", re.IGNORECASE), "设置全局可写权限"),
    (re.compile(r"curl.*\|\s*sh", re.IGNORECASE), "管道执行远程脚本"),
    (re.compile(r"wget.*\|\s*sh", re.IGNORECASE), "管道执行远程脚本"),
]

# ---------------------------------------------------------------------------
# 审计日志
# ---------------------------------------------------------------------------

AUDIT_LOG_PATH = Path.home() / ".claudezh" / "audit.log"
MAX_AUDIT_ENTRIES = 1000


def _ensure_audit_dir():
    """确保审计日志目录存在。"""
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _write_audit(tool_name: str, input_summary: str, status: str):
    """写入一条审计日志。"""
    try:
        _ensure_audit_dir()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] TOOL: {tool_name} | INPUT: {input_summary} | STATUS: {status}\n"

        # 追加写入
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)

        # 裁剪到最大条数
        _trim_audit_log()
    except Exception as e:
        logger.debug(f"审计日志写入失败: {e}")


def _trim_audit_log():
    """保留最近 MAX_AUDIT_ENTRIES 条记录。"""
    try:
        if not AUDIT_LOG_PATH.exists():
            return
        lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_AUDIT_ENTRIES:
            trimmed = lines[-MAX_AUDIT_ENTRIES:]
            AUDIT_LOG_PATH.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
    except Exception:
        pass


def get_audit_entries(
    count: int = 20,
    tool_filter: str | None = None,
    hours: int | None = None,
) -> list[str]:
    """读取审计日志条目。

    参数:
        count: 返回条目数量 (默认 20)
        tool_filter: 按工具名过滤 (不区分大小写)
        hours: 只返回最近 N 小时内的条目

    返回:
        日志条目列表 (最新的在后)
    """
    try:
        if not AUDIT_LOG_PATH.exists():
            return []

        lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()

        # 工具名过滤
        if tool_filter:
            tool_lower = tool_filter.lower()
            lines = [l for l in lines if f"TOOL: {tool_filter}" in l or tool_lower in l.lower()]

        # 时间范围过滤
        if hours:
            now = datetime.now()
            filtered = []
            for line in lines:
                try:
                    # 提取时间戳 [YYYY-MM-DD HH:MM:SS]
                    ts_str = line[1:20]
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    diff = (now - ts).total_seconds() / 3600
                    if diff <= hours:
                        filtered.append(line)
                except (ValueError, IndexError):
                    pass
            lines = filtered

        # 返回最近 count 条
        return lines[-count:]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# 输入摘要提取
# ---------------------------------------------------------------------------


def _summarize_input(tool_name: str, tool_input: dict[str, Any]) -> str:
    """从工具输入中提取摘要，用于审计日志。"""
    try:
        if tool_name == "Bash":
            cmd = tool_input.get("command", "")
            return cmd[:120] + ("..." if len(cmd) > 120 else "")
        elif tool_name in ("Write", "Edit"):
            path = tool_input.get("file_path", "")
            return f"file={path}"
        elif tool_name == "Read":
            path = tool_input.get("file_path", "")
            return f"file={path}"
        elif tool_name in ("Glob", "Grep"):
            pattern = tool_input.get("pattern", "")
            return f"pattern={pattern}"
        else:
            # 通用: 截取前 100 字符
            s = str(tool_input)
            return s[:100] + ("..." if len(s) > 100 else "")
    except Exception:
        return "<unknown>"


# ---------------------------------------------------------------------------
# Hook 回调函数 (符合 SDK HookCallback 签名)
# ---------------------------------------------------------------------------
# HookCallback = Callable[[HookInput, str | None, HookContext], Awaitable[HookJSONOutput]]


async def pre_bash_hook(
    hook_input: dict,
    tool_use_id: str | None,
    context: dict,
) -> dict:
    """PreToolUse 钩子: 拦截危险 Bash 命令。

    检查命令是否匹配危险模式，匹配则阻止执行并返回警告。
    """
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")

    for pattern, desc in DANGEROUS_PATTERNS:
        if pattern.search(command):
            warning = f"检测到危险命令: {desc}"
            logger.warning(f"[安全钩子] {warning} — 命令: {command[:80]}")
            _write_audit("Bash", f"BLOCKED: {command[:120]}", "blocked")

            return {
                "decision": "block",
                "reason": f"命令被安全系统拦截。{warning}。请使用更安全的替代方案。",
                "systemMessage": f"[安全警告] {warning}\n命令: {command[:80]}",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": warning,
                },
            }

    # 放行
    return {}


async def pre_write_hook(
    hook_input: dict,
    tool_use_id: str | None,
    context: dict,
) -> dict:
    """PreToolUse 钩子: 对关键路径写入操作发出提醒。"""
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # 检测对系统关键路径的写入
    critical_paths = ["/etc/", "/boot/", "/usr/lib/", "/usr/bin/"]
    for cp in critical_paths:
        if file_path.startswith(cp):
            warning = f"尝试写入系统关键路径: {file_path}"
            logger.warning(f"[安全钩子] {warning}")
            _write_audit("Write/Edit", f"BLOCKED: {file_path}", "blocked")
            return {
                "decision": "block",
                "reason": f"写入系统关键路径被拦截: {file_path}。请确认这是否是预期操作。",
                "systemMessage": f"[安全警告] {warning}",
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": warning,
                },
            }

    return {}


async def post_tool_hook(
    hook_input: dict,
    tool_use_id: str | None,
    context: dict,
) -> dict:
    """PostToolUse 钩子: 记录所有工具操作到审计日志。"""
    tool_name = hook_input.get("tool_name", "unknown")
    tool_input = hook_input.get("tool_input", {})

    summary = _summarize_input(tool_name, tool_input)
    _write_audit(tool_name, summary, "success")

    return {}


async def user_prompt_hook(
    hook_input: dict,
    tool_use_id: str | None,
    context: dict,
) -> dict:
    """UserPromptSubmit 钩子: 为中文环境自动注入上下文。"""
    from .i18n import get_locale

    locale = get_locale()
    if locale.startswith("zh"):
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "请用中文回答。代码注释也请使用中文。",
            },
        }

    return {}


async def notification_hook(
    hook_input: dict,
    tool_use_id: str | None,
    context: dict,
) -> dict:
    """Notification 钩子: 中文通知处理。"""
    message = hook_input.get("message", "")
    notification_type = hook_input.get("notification_type", "")

    # 记录通知到审计日志
    _write_audit(
        "Notification",
        f"type={notification_type} msg={message[:80]}",
        "info",
    )

    return {}


# ---------------------------------------------------------------------------
# 构建 hooks 配置 (用于 ClaudeAgentOptions)
# ---------------------------------------------------------------------------


def build_hook_config() -> dict:
    """构建 SDK hooks 配置字典。

    返回值直接传给 ClaudeAgentOptions(hooks=...)。

    格式: { HookEvent: [HookMatcher(...), ...] }
    """
    from claude_agent_sdk import HookMatcher

    return {
        "PreToolUse": [
            HookMatcher(
                matcher="Bash",
                hooks=[pre_bash_hook],
            ),
            HookMatcher(
                matcher="Write|Edit",
                hooks=[pre_write_hook],
            ),
        ],
        "PostToolUse": [
            HookMatcher(
                matcher=None,  # 匹配所有工具
                hooks=[post_tool_hook],
            ),
        ],
        "UserPromptSubmit": [
            HookMatcher(
                matcher=None,
                hooks=[user_prompt_hook],
            ),
        ],
        "Notification": [
            HookMatcher(
                matcher=None,
                hooks=[notification_hook],
            ),
        ],
    }
