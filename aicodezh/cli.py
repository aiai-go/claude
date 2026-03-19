"""Main CLI entry point for claudezh — AI 编程助手 (双模式: 订阅/API)."""

import asyncio
import os

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .backend import TOOL_NAME_ZH, Backend, StreamEvent, detect_backend
from .config import get_config_dir, load_config, save_config
from .history import History
from .i18n import get_locale, set_locale, t
from .skills import (
    SKILLS,
    Skill,
    complete_setup,
    get_enabled_skills,
    get_skill_system_prompt,
    has_completed_setup,
    list_skills_by_category,
    toggle_skill,
)
from .templates import TEMPLATES, list_templates
from .version import APP_NAME, APP_NAME_EN, VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HISTORY_FILE = str(get_config_dir() / "history.json")

AVAILABLE_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-35-20241022",
]

# SDK 内置工具名称 → 中文说明 (复用 backend 模块的映射表)
BUILTIN_TOOLS_ZH = TOOL_NAME_ZH

# 默认中文系统提示
DEFAULT_SYSTEM_PROMPT = """\
你是 AI 编程助手，一个全中文的智能编程终端工具。
- 始终用中文回答用户
- 可以读取、编辑、创建文件
- 可以执行命令和分析项目
- 代码注释用中文
- 遇到不确定的操作先询问用户确认
"""

# Command aliases: Chinese -> canonical key
COMMAND_MAP = {
    "/帮助": "help",
    "/help": "help",
    "/清屏": "clear",
    "/clear": "clear",
    "/设置": "settings",
    "/settings": "settings",
    "/模型": "model",
    "/model": "model",
    "/语言": "lang",
    "/lang": "lang",
    "/模板": "template",
    "/template": "template",
    "/退出": "exit",
    "/exit": "exit",
    "/quit": "exit",
    "/历史": "history",
    "/history": "history",
    "/tokens": "tokens",
    "/工具": "tools",
    "/tools": "tools",
    "/自动": "auto_mode",
    "/安全": "safe_mode",
    "/切换": "switch_mode",
    "/switch": "switch_mode",
    "/技能": "skills",
    "/skills": "skills",
    "/思考": "thinking",
    "/think": "thinking",
    "/强度": "effort",
    "/effort": "effort",
    "/审计": "audit",
    "/audit": "audit",
    "/笔记": "notes",
    "/notes": "notes",
    "/会话": "sessions",
    "/sessions": "sessions",
    "/恢复": "resume",
    "/resume": "resume",
    "/分支": "fork",
    "/fork": "fork",
    "/撤销": "undo",
    "/undo": "undo",
    "/检查点": "checkpoints",
    "/checkpoints": "checkpoints",
}

# ---------------------------------------------------------------------------
# CLI state
# ---------------------------------------------------------------------------

console = Console()


class CLIState:
    """Mutable state for the REPL session."""

    def __init__(self):
        self.config = load_config()
        self.history = History(max_size=self.config.get("history_size", 100))
        self.history.load(HISTORY_FILE)
        self.system_prompt: str | None = None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        # 权限模式: "default" (安全) 或 "acceptEdits" (自动)
        self.permission_mode: str = "default"
        # 后端实例
        self.backend: Backend | None = None

    def init_backend(self):
        """初始化后端 — 根据配置自动检测或使用指定模式。"""
        backend_config = {
            "mode": self.config.get("mode", "auto"),
            "model": self.config.get("model", "claude-sonnet-4-6"),
            "permission_mode": self.permission_mode,
            "cwd": os.getcwd(),
            "api_key": self.config.get("api_key", ""),
        }
        self.backend = detect_backend(backend_config)

        # 从配置恢复思考模式和推理强度
        thinking_mode = self.config.get("thinking_mode", "auto")
        if thinking_mode and hasattr(self.backend, "set_thinking"):
            self.backend.set_thinking(thinking_mode)

        effort_level = self.config.get("effort_level")
        if effort_level and hasattr(self.backend, "set_effort"):
            self.backend.set_effort(effort_level)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

def print_banner(state: CLIState):
    """Print the welcome banner."""

    title = Text()
    title.append(f"  {APP_NAME}  ", style="bold white on blue")
    title.append(f"  v{VERSION}", style="dim")

    mode_label = "安全模式" if state.permission_mode == "default" else "自动模式"
    backend_label = state.backend.get_mode_name() if state.backend else "未初始化"

    info_lines = Text()
    info_lines.append(f"  {t('welcome.subtitle')}\n", style="italic cyan")
    info_lines.append(f"  {t('welcome.cwd')}: ", style="dim")
    info_lines.append(f"{os.getcwd()}\n", style="green")
    info_lines.append(f"  {t('welcome.lang')}: ", style="dim")
    info_lines.append(f"{t('welcome.lang_name')}", style="yellow")
    info_lines.append(f"  |  Model: ", style="dim")
    info_lines.append(f"{state.config.get('model', 'claude-sonnet-4-6')}", style="yellow")
    info_lines.append(f"  |  ", style="dim")
    info_lines.append(f"{mode_label}\n", style="bold magenta")
    info_lines.append(f"  模式: ", style="dim")
    info_lines.append(f"{backend_label}", style="bold cyan")

    # 思考模式 & 推理强度
    if state.backend and hasattr(state.backend, "thinking_mode"):
        thinking_label = t(f"thinking.{state.backend.thinking_mode}")
        effort_label = t(f"effort.{state.backend.effort_level}")
        info_lines.append(f"  |  ", style="dim")
        info_lines.append(f"{t('thinking.title')}: ", style="dim")
        info_lines.append(f"{thinking_label}", style="yellow")
        info_lines.append(f"  |  ", style="dim")
        info_lines.append(f"{t('effort.title')}: ", style="dim")
        info_lines.append(f"{effort_label}", style="yellow")

    info_lines.append(f"\n  {t('welcome.tip')}", style="dim italic")
    info_lines.append(f"\n  提示: /自动 切换自动模式 | /安全 切换安全模式 | /切换 切换后端模式", style="dim")

    panel = Panel(
        info_lines,
        title=title,
        border_style="blue",
        padding=(0, 1),
    )
    console.print(panel)
    console.print()


# ---------------------------------------------------------------------------
# Slash-command handlers
# ---------------------------------------------------------------------------

def cmd_help(state: CLIState):
    """Show help table."""
    table = Table(title=t("help.title"), border_style="blue", show_lines=False)
    table.add_column(t("help.command"), style="cyan", min_width=20)
    table.add_column(t("help.description"), style="white")

    cmds = [
        ("/帮助  /help", "cmd.help"),
        ("/清屏  /clear", "cmd.clear"),
        ("/设置  /settings", "cmd.settings"),
        ("/模型  /model", "cmd.model"),
        ("/语言  /lang", "cmd.lang"),
        ("/模板  /template", "cmd.template"),
        ("/历史  /history", "cmd.tokens"),
        ("/tokens", "cmd.tokens"),
        ("/工具  /tools", "cmd.tools"),
        ("/自动", "自动模式 — AI 可自动执行编辑操作"),
        ("/安全", "安全模式 — 危险操作前需确认（默认）"),
        ("/切换  /switch", "切换后端模式 (订阅/API)"),
        ("/思考  /think", "cmd.thinking"),
        ("/强度  /effort", "cmd.effort"),
        ("/技能  /skills", "cmd.skills"),
        ("/会话  /sessions", "cmd.sessions"),
        ("/恢复  /resume", "cmd.resume"),
        ("/分支  /fork", "cmd.fork"),
        ("/审计  /audit", "cmd.audit"),
        ("/笔记  /notes", "快速笔记 — 添加/查看/搜索笔记"),
        ("/撤销  /undo", "cmd.undo"),
        ("/检查点  /checkpoints", "cmd.checkpoints"),
        ("/退出  /exit", "cmd.exit"),
    ]
    for names, key in cmds:
        desc = t(key) if not any(key.startswith(p) for p in ("自动", "安全", "切换")) else key
        table.add_row(names, desc)

    console.print(table)


def cmd_clear(state: CLIState):
    """Clear conversation history."""
    state.history.clear()
    state.total_input_tokens = 0
    state.total_output_tokens = 0
    state.system_prompt = None
    state.history.save(HISTORY_FILE)
    console.print("[green]>> 对话历史已清空[/green]" if get_locale().startswith("zh") else "[green]>> History cleared[/green]")


def cmd_settings(state: CLIState):
    """Display current settings."""
    table = Table(title=t("settings.title"), border_style="cyan")
    table.add_column(t("settings.key"), style="cyan")
    table.add_column(t("settings.value"), style="white")

    display_config = dict(state.config)
    # Mask API key
    if "api_key" in display_config:
        k = display_config["api_key"]
        display_config["api_key"] = k[:8] + "..." + k[-4:] if len(k) > 12 else "***"

    for key, val in display_config.items():
        table.add_row(key, str(val))

    if state.system_prompt:
        table.add_row("system_prompt", state.system_prompt[:60] + "...")

    mode_label = "安全模式 (default)" if state.permission_mode == "default" else "自动模式 (acceptEdits)"
    table.add_row("permission_mode", mode_label)

    backend_label = state.backend.get_mode_name() if state.backend else "未初始化"
    table.add_row("backend_mode", backend_label)

    # 思考模式 & 推理强度
    if state.backend and hasattr(state.backend, "thinking_mode"):
        thinking_label = t(f"thinking.{state.backend.thinking_mode}")
        table.add_row(t("thinking.title"), thinking_label)
    if state.backend and hasattr(state.backend, "effort_level"):
        effort_label = t(f"effort.{state.backend.effort_level}")
        table.add_row(t("effort.title"), effort_label)

    console.print(table)


def cmd_model(state: CLIState):
    """Switch the current model."""
    console.print("[bold cyan]可用模型 / Available Models:[/bold cyan]")
    current_model = state.backend.get_model() if state.backend else state.config.get("model")
    for i, m in enumerate(AVAILABLE_MODELS, 1):
        marker = " [green]<< 当前[/green]" if m == current_model else ""
        console.print(f"  {i}. {m}{marker}")

    console.print()
    try:
        choice = input("选择编号 / Pick number: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.isdigit() and 1 <= int(choice) <= len(AVAILABLE_MODELS):
        selected = AVAILABLE_MODELS[int(choice) - 1]
        state.config["model"] = selected
        save_config(state.config)
        if state.backend:
            state.backend.set_model(selected)
        console.print(f"[green]>> 已切换到 {selected}[/green]")
    else:
        console.print("[yellow]>> 无效选择[/yellow]")


def cmd_lang(state: CLIState):
    """Switch UI language."""
    langs = [("zh-CN", "简体中文"), ("zh-TW", "繁體中文"), ("en", "English")]
    for i, (code, name) in enumerate(langs, 1):
        marker = " [green]<< 当前[/green]" if code == get_locale() else ""
        console.print(f"  {i}. {name} ({code}){marker}")

    try:
        choice = input("选择 / Pick: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.isdigit() and 1 <= int(choice) <= len(langs):
        code = langs[int(choice) - 1][0]
        set_locale(code)
        state.config["language"] = code
        save_config(state.config)
        console.print(f"[green]>> {t('success.prefix')}: {code}[/green]")
    else:
        console.print("[yellow]>> 无效选择[/yellow]")


def cmd_template(state: CLIState):
    """Select a system prompt template."""
    loc = get_locale()
    locale_key = "tw" if loc == "zh-TW" else "zh"
    tpls = list_templates(locale_key)

    console.print("[bold cyan]预设模板 / Prompt Templates:[/bold cyan]")
    for i, tpl in enumerate(tpls, 1):
        console.print(f"  {i}. {tpl['name']}")
    console.print(f"  0. 清除模板 / Clear template")

    try:
        choice = input("选择编号 / Pick number: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "0":
        state.system_prompt = None
        console.print("[green]>> 已清除系统模板[/green]")
        return

    if choice.isdigit() and 1 <= int(choice) <= len(tpls):
        key = tpls[int(choice) - 1]["key"]
        tpl_data = TEMPLATES[key]
        state.system_prompt = tpl_data["system"]
        console.print(f"[green]>> 已启用模板: {tpls[int(choice) - 1]['name']}[/green]")
    else:
        console.print("[yellow]>> 无效选择[/yellow]")


def cmd_history(state: CLIState):
    """Show recent history entries."""
    recent = state.history.get_recent(10)
    if not recent:
        console.print("[dim]暂无历史 / No history yet[/dim]")
        return
    for msg in recent:
        role_style = "bold cyan" if msg["role"] == "user" else "bold green"
        label = t("prompt.you") if msg["role"] == "user" else t("prompt.ai")
        content_preview = msg["content"][:120].replace("\n", " ")
        if len(msg["content"]) > 120:
            content_preview += "..."
        console.print(f"  [{role_style}]{label}[/{role_style}]: {content_preview}")


def cmd_tokens(state: CLIState):
    """Show token usage stats."""
    table = Table(title="Token Usage", border_style="magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white", justify="right")

    table.add_row("Input tokens", f"{state.total_input_tokens:,}")
    table.add_row("Output tokens", f"{state.total_output_tokens:,}")
    table.add_row("Total tokens", f"{state.total_input_tokens + state.total_output_tokens:,}")
    table.add_row("Messages", str(len(state.history)))

    console.print(table)


def cmd_tools(state: CLIState):
    """List available tools for the current backend."""
    if state.backend:
        tools = state.backend.available_tools
        backend_name = state.backend.get_mode_name()
    else:
        tools = list(BUILTIN_TOOLS_ZH.keys())
        backend_name = "未初始化"

    table = Table(title=f"可用工具 / Available Tools ({backend_name})", border_style="cyan", show_lines=True)
    table.add_column("工具名称", style="cyan", min_width=12)
    table.add_column("说明", style="white", min_width=30)

    for name in tools:
        desc = BUILTIN_TOOLS_ZH.get(name, name)
        table.add_row(name, desc)

    console.print(table)
    console.print(f"[dim]当前后端: {backend_name}[/dim]")


def cmd_auto_mode(state: CLIState):
    """Switch to auto (acceptEdits) permission mode."""
    state.permission_mode = "acceptEdits"
    if state.backend:
        state.backend.set_permission("acceptEdits")
    console.print("[bold green]>> 已切换到自动模式[/bold green] — AI 可自动执行编辑和命令操作")


def cmd_safe_mode(state: CLIState):
    """Switch to safe (default) permission mode."""
    state.permission_mode = "default"
    if state.backend:
        state.backend.set_permission("default")
    console.print("[bold yellow]>> 已切换到安全模式[/bold yellow] — 危险操作前需要确认")


def first_run_setup():
    """Interactive first-run skill selection. Runs when skills.json doesn't exist."""
    # Header
    welcome_box = Panel(
        f"     {t('skills.welcome_title')} \U0001f389\n"
        f"     {t('skills.welcome_subtitle')}",
        border_style="cyan",
        padding=(0, 2),
    )
    console.print(welcome_box)
    console.print()

    recommended = {"fullstack", "git"}
    categories = list_skills_by_category()
    all_keys: list[str] = []  # ordered list for numbering
    selected: set[str] = set()

    idx = 0
    for cat_name, skills in categories.items():
        console.print(f"[bold cyan]{cat_name}:[/bold cyan]")
        for skill in skills:
            idx += 1
            all_keys.append(skill.key)
            rec_tag = f" [green]({t('skills.recommended')})[/green]" if skill.key in recommended else ""
            console.print(f"  [{idx}] {skill.icon} {skill.name} — {skill.description}{rec_tag}")

            # Default for recommended skills
            default = "y" if skill.key in recommended else "n"
            try:
                answer = input(f"         {t('skills.enable_prompt')} (y/n) [{default}]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""

            if not answer:
                answer = default
            if answer in ("y", "yes", "是"):
                selected.add(skill.key)
        console.print()

    # Save and finish
    complete_setup(list(selected))

    # Summary
    enabled_names = [SKILLS[k].name for k in all_keys if k in selected]
    if enabled_names:
        console.print(
            f"[bold green]{t('skills.enabled_summary', count=len(enabled_names))}: "
            f"{', '.join(enabled_names)}[/bold green]"
        )
    else:
        console.print("[dim]未启用任何技能[/dim]")

    console.print(f"[dim]{t('skills.manage_tip')}[/dim]")
    console.print()


def cmd_skills(state: CLIState):
    """Show and manage AI skills."""
    categories = list_skills_by_category()
    all_keys: list[str] = []

    table = Table(title=t("skills.title"), border_style="cyan", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("状态", width=4)
    table.add_column("技能", style="cyan", min_width=16)
    table.add_column("说明", style="white")

    idx = 0
    for cat_name, skills in categories.items():
        # Category header row
        table.add_row("", "", f"[bold]{cat_name}[/bold]", "")
        for skill in skills:
            idx += 1
            all_keys.append(skill.key)
            status = "[green]✅[/green]" if skill.enabled else "[dim]❌[/dim]"
            table.add_row(str(idx), status, f"{skill.icon} {skill.name}", skill.description)

    console.print(table)
    console.print()

    # Toggle prompt
    console.print(f"[dim]{t('skills.toggle_prompt')}[/dim]")
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not choice or choice == "0":
        return

    if choice.isdigit() and 1 <= int(choice) <= len(all_keys):
        key = all_keys[int(choice) - 1]
        new_state = toggle_skill(key)
        skill = SKILLS[key]
        if new_state:
            console.print(f"[bold green]>> {t('skills.toggled_on')}: {skill.icon} {skill.name}[/bold green]")
        else:
            console.print(f"[yellow]>> {t('skills.toggled_off')}: {skill.icon} {skill.name}[/yellow]")
    else:
        console.print("[yellow]>> 无效选择[/yellow]")


def cmd_thinking(state: CLIState, user_input: str = ""):
    """Control thinking mode: auto / deep / off."""
    if not state.backend or not hasattr(state.backend, "set_thinking"):
        console.print("[yellow]>> 当前后端不支持思考模式控制[/yellow]")
        return

    # 解析参数
    parts = user_input.split()
    arg = parts[1] if len(parts) > 1 else ""

    # 中文 → 英文映射
    mode_map = {
        "深度": "deep", "deep": "deep",
        "自动": "auto", "auto": "auto",
        "关闭": "off", "off": "off",
    }

    if not arg:
        # 显示当前状态
        current = state.backend.thinking_mode
        label = t(f"thinking.{current}")
        console.print(f"[bold cyan]{t('thinking.current', mode=label)}[/bold cyan]")
        console.print(f"[dim]{t('thinking.usage')}[/dim]")
        return

    mode = mode_map.get(arg)
    if not mode:
        console.print(f"[yellow]>> 无效参数: {arg}[/yellow]")
        console.print(f"[dim]{t('thinking.usage')}[/dim]")
        return

    state.backend.set_thinking(mode)
    state.config["thinking_mode"] = mode
    save_config(state.config)

    label = t(f"thinking.{mode}")
    console.print(f"[bold green]>> {t('thinking.switched', mode=label)}[/bold green]")


def cmd_effort(state: CLIState, user_input: str = ""):
    """Control effort level: low / medium / high / max."""
    if not state.backend or not hasattr(state.backend, "set_effort"):
        console.print("[yellow]>> 当前后端不支持推理强度控制[/yellow]")
        return

    # 解析参数
    parts = user_input.split()
    arg = parts[1] if len(parts) > 1 else ""

    # 中文 → 英文映射
    level_map = {
        "低": "low", "low": "low",
        "中": "medium", "medium": "medium",
        "高": "high", "high": "high",
        "最大": "max", "max": "max",
    }

    if not arg:
        # 显示当前状态
        current = state.backend.effort_level
        label = t(f"effort.{current}")
        console.print(f"[bold cyan]{t('effort.current', level=label)}[/bold cyan]")
        console.print(f"[dim]{t('effort.usage')}[/dim]")
        return

    level = level_map.get(arg)
    if not level:
        console.print(f"[yellow]>> 无效参数: {arg}[/yellow]")
        console.print(f"[dim]{t('effort.usage')}[/dim]")
        return

    state.backend.set_effort(level)
    state.config["effort_level"] = level
    save_config(state.config)

    label = t(f"effort.{level}")
    console.print(f"[bold green]>> {t('effort.switched', level=label)}[/bold green]")


def cmd_switch_mode(state: CLIState):
    """Toggle between SDK and API backend modes."""
    if not state.backend:
        console.print("[red]>> 后端未初始化[/red]")
        return

    current_mode = state.config.get("mode", "auto")
    current_name = state.backend.get_mode_name()

    # Determine which mode to switch to
    from .backend import SDKBackend, APIBackend, _check_claude_cli, _resolve_api_key

    if isinstance(state.backend, SDKBackend):
        # Try switching to API
        api_key = _resolve_api_key(state.config)
        if not api_key:
            console.print("[yellow]>> 无法切换到 API 模式 — 未找到 API Key[/yellow]")
            console.print("[dim]   请设置 ANTHROPIC_API_KEY 环境变量或在配置中提供 api_key[/dim]")
            return
        state.config["mode"] = "api"
        save_config(state.config)
        state.init_backend()
        console.print(f"[bold green]>> 已从 {current_name} 切换到 {state.backend.get_mode_name()}[/bold green]")

    elif isinstance(state.backend, APIBackend):
        # Try switching to SDK
        if not _check_claude_cli():
            console.print("[yellow]>> 无法切换到订阅模式 — 未安装 Claude CLI[/yellow]")
            return
        state.config["mode"] = "sdk"
        save_config(state.config)
        state.init_backend()
        console.print(f"[bold green]>> 已从 {current_name} 切换到 {state.backend.get_mode_name()}[/bold green]")

    else:
        console.print("[yellow]>> 当前后端不支持切换[/yellow]")



def cmd_audit(state: CLIState):
    """显示审计日志 -- 最近的工具操作记录。"""
    from .hooks import get_audit_entries, AUDIT_LOG_PATH

    entries = get_audit_entries(count=20)

    if not entries:
        console.print("[dim]暂无审计记录[/dim]")
        console.print(f"[dim]日志路径: {AUDIT_LOG_PATH}[/dim]")
        return

    table = Table(
        title=t("audit.title"),
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("时间", style="dim", min_width=19)
    table.add_column("工具", style="cyan", min_width=10)
    table.add_column("操作", style="white", min_width=30)
    table.add_column("状态", style="green", min_width=7)

    for entry in entries:
        try:
            parts = entry.split(" | ")
            ts = parts[0][1:20]
            tool = parts[0].split("TOOL: ")[1] if "TOOL: " in parts[0] else "?"
            inp = parts[1].replace("INPUT: ", "") if len(parts) > 1 else ""
            status = parts[2].replace("STATUS: ", "") if len(parts) > 2 else ""
            status_style = "green" if status == "success" else "red" if status == "blocked" else "yellow"
            table.add_row(ts, tool, inp[:50], f"[{status_style}]{status}[/{status_style}]")
        except Exception:
            table.add_row("", "", entry[:60], "")

    console.print(table)
    console.print(f"[dim]日志路径: {AUDIT_LOG_PATH}[/dim]")
    console.print(f"[dim]共 {len(entries)} 条记录 (最近)[/dim]")



def _format_session_time(timestamp_ms: int) -> str:
    """Format millisecond timestamp to readable date/time."""
    from datetime import datetime
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "???"


def _get_session_title(session) -> str:
    """Extract a display title from a session object."""
    title = session.custom_title or session.summary or session.first_prompt or ""
    # Truncate long titles
    title = title.replace("\n", " ").strip()
    if len(title) > 50:
        title = title[:47] + "..."
    return title or "(无标题)"


def _show_sessions(state: CLIState, limit: int = 20) -> list:
    """Display session list and return sessions. Returns empty list if not available."""
    from .backend import SDKBackend

    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print(f"[yellow]>> {t('sessions.not_available')}[/yellow]")
        return []

    sessions = state.backend.list_sessions(limit=limit)
    if not sessions:
        console.print(f"[dim]{t('sessions.empty')}[/dim]")
        return []

    console.print(f"[bold cyan]{t('sessions.title')}:[/bold cyan]")
    console.print()
    for i, s in enumerate(sessions, 1):
        time_str = _format_session_time(s.last_modified)
        title = _get_session_title(s)
        cwd_str = f"  ({s.cwd})" if s.cwd else ""
        console.print(f"  [dim][{i:>2}][/dim] {time_str}  [cyan]\u201c{title}\u201d[/cyan]{cwd_str}")

    console.print()
    return sessions


def _pick_session(state: CLIState, arg: str = "", sessions: list | None = None) -> str | None:
    """Let user pick a session. Returns session_id or None."""
    # If arg is a number, use it directly
    if arg.strip().isdigit():
        idx = int(arg.strip())
        if sessions is None:
            sessions = _show_sessions(state)
        if 1 <= idx <= len(sessions):
            return sessions[idx - 1].session_id
        else:
            console.print("[yellow]>> 无效编号[/yellow]")
            return None

    # Show list and prompt
    if sessions is None:
        sessions = _show_sessions(state)
    if not sessions:
        return None

    console.print(f"[dim]{t('sessions.pick_prompt')}[/dim]")
    try:
        choice = input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice:
        return None

    if choice.isdigit() and 1 <= int(choice) <= len(sessions):
        return sessions[int(choice) - 1].session_id
    else:
        console.print("[yellow]>> 无效选择[/yellow]")
        return None


def cmd_sessions(state: CLIState, arg: str = ""):
    """List recent sessions and optionally resume one."""
    sessions = _show_sessions(state)
    if not sessions:
        return

    session_id = _pick_session(state, sessions=sessions)
    if session_id:
        _do_resume(state, session_id, fork=False)


def cmd_resume(state: CLIState, arg: str = ""):
    """Resume a past session."""
    session_id = _pick_session(state, arg=arg)
    if session_id:
        _do_resume(state, session_id, fork=False)


def cmd_fork(state: CLIState, arg: str = ""):
    """Fork from a past session (non-destructive)."""
    session_id = _pick_session(state, arg=arg)
    if session_id:
        _do_resume(state, session_id, fork=True)


def _do_resume(state: CLIState, session_id: str, fork: bool = False):
    """Actually resume/fork a session and send initial prompt."""
    from .backend import SDKBackend

    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print(f"[yellow]>> {t('sessions.not_available')}[/yellow]")
        return

    state.backend.resume_session(session_id, fork=fork)

    action = t('sessions.forked') if fork else t('sessions.resumed')
    console.print(f"[bold green]>> {action}: {session_id[:12]}...[/bold green]")
    console.print("[dim]输入你的下一条消息继续对话[/dim]")


def cmd_undo(state: CLIState):
    """Undo the last AI file modification using checkpoints."""
    from .backend import SDKBackend
    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print("[yellow]>> 撤销仅在 SDK 模式下可用[/yellow]")
        return
    cp = state.backend.checkpoint_mgr
    checkpoints = cp.list_checkpoints()
    if not checkpoints:
        console.print("[dim]没有可用的检查点[/dim]")
        return
    latest = checkpoints[0]
    try:
        cp.undo(latest.checkpoint_id)
        console.print(f"[bold green]>> 已撤销到检查点: {latest.checkpoint_id}[/bold green]")
    except Exception as e:
        console.print(f"[red]>> 撤销失败: {e}[/red]")


def cmd_checkpoints(state: CLIState):
    """List available file checkpoints."""
    from .backend import SDKBackend
    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print("[yellow]>> 检查点仅在 SDK 模式下可用[/yellow]")
        return
    cp = state.backend.checkpoint_mgr
    checkpoints = cp.list_checkpoints()
    if not checkpoints:
        console.print("[dim]没有可用的检查点[/dim]")
        return
    table = Table(title="文件检查点", border_style="cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="cyan")
    table.add_column("时间", style="white")
    table.add_column("文件数", style="yellow", justify="right")
    for i, cp_info in enumerate(checkpoints, 1):
        created = getattr(cp_info, 'created_at', '?')
        files = str(len(getattr(cp_info, 'modified_files', [])))
        table.add_row(str(i), cp_info.checkpoint_id[:12], str(created), files)
    console.print(table)


def cmd_notes(state: CLIState):
    """Quick notes management -- add, list, or search notes."""
    import asyncio as _asyncio
    from .mcp_tools import _note_add, _note_list, _note_search

    console.print("[bold cyan]快速笔记 / Quick Notes[/bold cyan]")
    console.print("  1. 添加笔记")
    console.print("  2. 查看近期笔记")
    console.print("  3. 搜索笔记")
    console.print("  0. 返回")
    console.print()

    try:
        choice = input("选择 / Pick: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        try:
            text = input("笔记内容: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if text:
            result = _asyncio.run(_note_add({"text": text}))
            msg = result["content"][0]["text"]
            console.print(f"[green]>> {msg}[/green]")
        else:
            console.print("[yellow]>> 内容为空，已取消[/yellow]")

    elif choice == "2":
        result = _asyncio.run(_note_list({"days": 7}))
        msg = result["content"][0]["text"]
        console.print(msg)

    elif choice == "3":
        try:
            keyword = input("搜索关键词: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if keyword:
            result = _asyncio.run(_note_search({"keyword": keyword}))
            msg = result["content"][0]["text"]
            console.print(msg)
        else:
            console.print("[yellow]>> 关键词为空，已取消[/yellow]")




def cmd_undo(state: CLIState):
    """Undo the last file changes made by AI."""
    if not state.backend:
        console.print("[red]>> 后端未初始化[/red]")
        return

    mgr = state.backend.checkpoint_mgr
    checkpoints = mgr.list_checkpoints()

    if not checkpoints:
        console.print(f"[yellow]>> {t('undo.no_checkpoints')}[/yellow]")
        return

    latest = checkpoints[0]
    file_count = len(latest.files_backed_up) + len(latest.files_created)

    console.print()
    console.print(f"[bold yellow]{t('undo.confirm_title')}[/bold yellow]")
    console.print(f"  {t('undo.time')}: [cyan]{latest.time_str}[/cyan]")
    console.print(f"  {t('undo.prompt')}: [dim]{latest.prompt_preview}[/dim]")
    console.print(f"  {t('undo.files')}: [cyan]{file_count}[/cyan]")

    if latest.files_backed_up:
        for f in latest.files_backed_up:
            console.print(f"    [dim][恢复] {f}[/dim]")
    if latest.files_created:
        for f in latest.files_created:
            console.print(f"    [dim][删除] {f}[/dim]")

    console.print()
    try:
        answer = input(f"{t('undo.confirm_prompt')} (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
        return

    if answer not in ('y', 'yes', '是'):
        console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
        return

    success, msg, reverted = mgr.undo()
    if success:
        console.print(f"[bold green]>> {msg}[/bold green]")
        for f in reverted:
            console.print(f"  [green]{f}[/green]")
    else:
        console.print(f"[red]>> {msg}[/red]")


def cmd_checkpoints(state: CLIState):
    """Show available file checkpoints."""
    if not state.backend:
        console.print("[red]>> 后端未初始化[/red]")
        return

    mgr = state.backend.checkpoint_mgr
    checkpoints = mgr.list_checkpoints()

    if not checkpoints:
        console.print(f"[dim]{t('undo.no_checkpoints')}[/dim]")
        return

    table = Table(title=t('checkpoints.title'), border_style='cyan', show_lines=False)
    table.add_column('#', style='dim', width=4)
    table.add_column(t('checkpoints.time'), style='cyan', min_width=20)
    table.add_column(t('checkpoints.prompt'), style='white', min_width=30)
    table.add_column(t('checkpoints.files'), style='yellow', justify='right', width=8)

    for i, ckpt in enumerate(checkpoints, 1):
        file_count = len(ckpt.files_backed_up) + len(ckpt.files_created)
        table.add_row(str(i), ckpt.time_str, ckpt.prompt_preview, str(file_count))

    console.print(table)
    console.print()
    console.print(f"[dim]{t('checkpoints.undo_tip')}[/dim]")

    try:
        choice = input(f"{t('checkpoints.select_prompt')} ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if not choice or choice == '0':
        return

    if choice.isdigit() and 1 <= int(choice) <= len(checkpoints):
        target = checkpoints[int(choice) - 1]
        file_count = len(target.files_backed_up) + len(target.files_created)

        console.print()
        console.print(f"[bold yellow]{t('undo.confirm_title')}[/bold yellow]")
        console.print(f"  {t('undo.time')}: [cyan]{target.time_str}[/cyan]")
        console.print(f"  {t('undo.prompt')}: [dim]{target.prompt_preview}[/dim]")
        console.print(f"  {t('undo.files')}: [cyan]{file_count}[/cyan]")
        console.print()

        try:
            answer = input(f"{t('undo.confirm_prompt')} (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return

        if answer not in ('y', 'yes', '是'):
            console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
            return

        success, msg, reverted = mgr.undo(target.checkpoint_id)
        if success:
            console.print(f"[bold green]>> {msg}[/bold green]")
            for f in reverted:
                console.print(f"  [green]{f}[/green]")
        else:
            console.print(f"[red]>> {msg}[/red]")
    else:
        console.print("[yellow]>> 无效选择[/yellow]")


# Command dispatch table
COMMANDS = {
    "help": cmd_help,
    "clear": cmd_clear,
    "settings": cmd_settings,
    "model": cmd_model,
    "lang": cmd_lang,
    "template": cmd_template,
    "history": cmd_history,
    "tokens": cmd_tokens,
    "tools": cmd_tools,
    "auto_mode": cmd_auto_mode,
    "safe_mode": cmd_safe_mode,
    "switch_mode": cmd_switch_mode,
    "skills": cmd_skills,
    "thinking": cmd_thinking,
    "effort": cmd_effort,
    "audit": cmd_audit,
    "notes": cmd_notes,
    "sessions": cmd_sessions,
    "resume": cmd_resume,
    "fork": cmd_fork,
    "undo": cmd_undo,
    "checkpoints": cmd_checkpoints,
}


# ---------------------------------------------------------------------------
# Chat via Backend abstraction
# ---------------------------------------------------------------------------

async def chat_async(user_input: str, state: CLIState):
    """Send user input to Claude via the backend abstraction and handle the response."""
    if not state.backend:
        console.print("[red]>> 后端未初始化，请重启程序[/red]")
        return

    # 添加用户消息到历史
    state.history.add("user", user_input)

    # 构建系统提示: 用户选的模板优先，否则用默认中文提示
    system_prompt = state.system_prompt or DEFAULT_SYSTEM_PROMPT

    # 追加启用的技能系统提示
    skill_prompt = get_skill_system_prompt()
    if skill_prompt:
        system_prompt = system_prompt.rstrip() + "\n\n" + skill_prompt

    # 构建历史消息列表
    history_messages = []
    recent = state.history.get_recent(state.config.get("history_size", 100))
    # 排除最后一条 (刚添加的 user_input)
    for msg in recent[:-1]:
        history_messages.append({"role": msg["role"], "content": msg["content"]})

    ai_label = t("prompt.ai")
    response_text_parts = []

    console.print()

    try:
        async for event in state.backend.ask(
            prompt=user_input,
            system_prompt=system_prompt,
            history=history_messages if history_messages else None,
        ):
            if event.type == "text":
                response_text_parts.append(event.text)
                console.print(f"[bold green]{ai_label}[/bold green]:", end=" ")
                console.print(event.text, highlight=False)
                console.print()

            elif event.type == "tool_use" and event.tool:
                tool_name = event.tool.name
                tool_desc = event.tool.name_zh
                console.print(f"  [dim]>> 调用工具: {tool_name} — {tool_desc}[/dim]")

            elif event.type == "tool_result" and event.tool:
                result_preview = event.tool.result[:200] if event.tool.result else ""
                if result_preview:
                    result_panel = Panel(
                        result_preview,
                        title=f"工具结果: {event.tool.name_zh or event.tool.name}",
                        border_style="dim",
                        expand=False,
                    )
                    console.print(result_panel)

            elif event.type == "thinking":
                # 深度思考模式下显示增强指示器
                thinking_mode = getattr(state.backend, "thinking_mode", "auto")
                if thinking_mode == "deep":
                    console.print(f"  [dim italic]>> {t('thinking.deep_indicator')}[/dim italic]")
                    if event.text and len(event.text) > 0:
                        # 显示思考内容摘要（前100字）
                        preview = event.text[:100].replace("\n", " ")
                        if len(event.text) > 100:
                            preview += "..."
                        console.print(f"  [dim]   {preview}[/dim]")
                else:
                    console.print(f"  [dim italic]>> {t('thinking')}[/dim italic]")

            elif event.type == "done":
                if state.config.get("show_token_usage") and event.usage:
                    input_t = event.usage.get("input_tokens", 0)
                    output_t = event.usage.get("output_tokens", 0)
                    state.total_input_tokens += input_t
                    state.total_output_tokens += output_t
                    console.print(f"  [dim]用量: 输入 {input_t:,} / 输出 {output_t:,} tokens[/dim]")

            elif event.type == "error":
                console.print(f"\n[red]>> {event.text}[/red]")
                # 移除失败的用户消息
                if state.history.messages and state.history.messages[-1]["role"] == "user":
                    state.history.messages.pop()
                return

    except KeyboardInterrupt:
        console.print(
            "\n[yellow]>> 已中断生成[/yellow]"
            if get_locale().startswith("zh")
            else "\n[yellow]>> Generation interrupted[/yellow]"
        )
    except Exception as e:
        console.print(f"\n[red]>> 错误: {e}[/red]")
        # 移除失败的用户消息
        if state.history.messages and state.history.messages[-1]["role"] == "user":
            state.history.messages.pop()
        return

    # 保存助手回复到历史
    full_response = "\n".join(response_text_parts)
    if full_response:
        state.history.add("assistant", full_response)
        state.history.save(HISTORY_FILE)

    console.print()


def chat(user_input: str, state: CLIState):
    """Synchronous wrapper for chat_async."""
    asyncio.run(chat_async(user_input, state))


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def run():
    """Main entry point — starts the interactive REPL."""
    state = CLIState()

    # Apply saved language preference
    lang = state.config.get("language", "auto")
    if lang != "auto":
        set_locale(lang)

    # 首次运行: 技能选择
    if not has_completed_setup():
        first_run_setup()

    # 初始化后端
    try:
        state.init_backend()
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)

    print_banner(state)

    prompt_label = t("prompt.you")

    while True:
        try:
            user_input = input(f"[{prompt_label}] > ").strip()
        except EOFError:
            # Ctrl+D
            console.print()
            console.print(t("goodbye"))
            state.history.save(HISTORY_FILE)
            break
        except KeyboardInterrupt:
            # Ctrl+C at prompt — just print a new line, don't exit
            console.print()
            continue

        if not user_input:
            continue

        # Check for slash commands
        first_word = user_input.split()[0] if user_input.startswith("/") else None
        if first_word and first_word in COMMAND_MAP:
            cmd_key = COMMAND_MAP[first_word]
            if cmd_key == "exit":
                console.print(t("goodbye"))
                state.history.save(HISTORY_FILE)
                break
            handler = COMMANDS.get(cmd_key)
            if handler:
                # 部分命令需要完整输入（含参数）
                if cmd_key in ("thinking", "effort"):
                    handler(state, user_input)
                elif cmd_key in ("resume", "fork"):
                    # Extract optional argument (e.g. /resume 3)
                    parts = user_input.split(maxsplit=1)
                    arg = parts[1] if len(parts) > 1 else ""
                    handler(state, arg=arg)
                else:
                    handler(state)
            continue

        # Unknown slash command
        if user_input.startswith("/"):
            console.print(
                "[yellow]>> 未知命令，输入 /帮助 查看可用命令[/yellow]"
                if get_locale().startswith("zh")
                else "[yellow]>> Unknown command. Type /help for available commands[/yellow]"
            )
            continue

        # Send to Claude via backend
        chat(user_input, state)


if __name__ == "__main__":
    run()
