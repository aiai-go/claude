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
    info_lines.append(f"{backend_label}\n", style="bold cyan")
    info_lines.append(f"  {t('welcome.tip')}", style="dim italic")
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
                console.print(f"  [dim italic]>> 思考中...[/dim italic]")

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
