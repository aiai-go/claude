"""Main CLI entry point for @aiai-go/claude — AI coding assistant (dual mode: subscription/API)."""

import asyncio
import os
import time

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .backend import Backend, StreamEvent, detect_backend
from .config import get_config_dir, load_config, save_config
from .history import History
from .i18n import get_locale, set_locale, t
from .skills import (
    CATEGORIES,
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
from .quota import (
    QuotaTracker, format_tokens, format_number, get_real_usage_summary,
    get_cached_usage, make_usage_bar, format_time_remaining,
)
from .version import APP_NAME, APP_NAME_EN, BRAND_NAME, VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HISTORY_FILE = str(get_config_dir() / "history.json")

AVAILABLE_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-35-20241022",
]

def _default_system_prompt() -> str:
    """Default system prompt (i18n-aware)."""
    return t("system_prompt.default")

# Command aliases: Chinese -> canonical key
COMMAND_MAP = {
    "/帮助": "help", "/help": "help",
    "/清屏": "clear", "/clear": "clear",
    "/设置": "settings", "/settings": "settings",
    "/模型": "model", "/model": "model",
    "/语言": "lang", "/lang": "lang",
    "/模板": "template", "/template": "template",
    "/退出": "exit", "/exit": "exit", "/quit": "exit",
    "/历史": "history", "/history": "history",
    "/tokens": "tokens",
    "/工具": "tools", "/tools": "tools",
    "/自动": "auto_mode", "/auto": "auto_mode", "/安全": "safe_mode", "/safe": "safe_mode",
    "/切换": "switch_mode", "/switch": "switch_mode",
    "/技能": "skills", "/skills": "skills",
    "/思考": "thinking", "/think": "thinking",
    "/强度": "effort", "/effort": "effort",
    "/审计": "audit", "/audit": "audit",
    "/笔记": "notes", "/notes": "notes",
    "/会话": "sessions", "/sessions": "sessions",
    "/恢复": "resume", "/resume": "resume",
    "/分支": "fork", "/fork": "fork",
    "/撤销": "undo", "/undo": "undo",
    "/检查点": "checkpoints", "/checkpoints": "checkpoints",
    "/额度": "quota", "/quota": "quota",
}

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
        self.permission_mode: str = "default"
        self.backend: Backend | None = None
        self.quota = QuotaTracker()

    def init_backend(self):
        backend_config = {
            "mode": self.config.get("mode", "auto"),
            "model": self.config.get("model", "claude-sonnet-4-6"),
            "permission_mode": self.permission_mode,
            "cwd": os.getcwd(),
            "api_key": self.config.get("api_key", ""),
        }
        self.backend = detect_backend(backend_config)
        thinking_mode = self.config.get("thinking_mode", "auto")
        if thinking_mode and hasattr(self.backend, "set_thinking"):
            self.backend.set_thinking(thinking_mode)
        effort_level = self.config.get("effort_level")
        if effort_level and hasattr(self.backend, "set_effort"):
            self.backend.set_effort(effort_level)


# ---------------------------------------------------------------------------
# Banner — Claude Code inspired modern UI
# ---------------------------------------------------------------------------

def print_banner(state: CLIState):
    """Print the welcome banner with Claude Code-inspired styling."""

    # --- Title ---
    title = Text()
    title.append(f" {BRAND_NAME}", style="bold bright_cyan")
    title.append(f" v{VERSION} ", style="dim")

    # --- Subtitle ---
    subtitle = Text(f"  {t('welcome.subtitle')}", style="dim italic white")

    # --- Info grid: labels left, values right, perfectly aligned ---
    mode_label = t("mode.safe") if state.permission_mode == "default" else t("mode.auto")
    backend_label = state.backend.get_mode_name() if state.backend else t("mode.not_initialized")

    # Enhance backend label with real plan name if available
    account_info = _get_cached_account(state)
    if account_info:
        acct = account_info.get("account") if isinstance(account_info, dict) else None
        if acct is None and hasattr(account_info, "account"):
            acct = account_info.account
        if acct:
            plan = acct.get("subscriptionType", "") if isinstance(acct, dict) else getattr(acct, "subscriptionType", "")
            if plan:
                from .backend import SDKBackend
                if state.backend and isinstance(state.backend, SDKBackend):
                    backend_label = t("mode.subscription_plan", plan=plan)

    info = Table.grid(padding=(0, 1))
    info.add_column(style="bright_blue")    # label
    info.add_column(style="bright_white", min_width=20)  # value (enough room)
    info.add_column(style="bright_blue")    # label 2
    info.add_column(style="bright_white")   # value 2

    info.add_row(
        t("welcome.cwd"), os.getcwd(),
        t("mode.label"), backend_label,
    )
    info.add_row(
        t("welcome.lang"), t("welcome.lang_name"),
        t("welcome.model"), state.config.get("model", "claude-sonnet-4-6"),
    )

    # Thinking mode + effort level on same row
    thinking_val = ""
    effort_val = ""
    if state.backend and hasattr(state.backend, "thinking_mode"):
        thinking_val = t(f"thinking.{state.backend.thinking_mode}")
        effort_val = t(f"effort.{state.backend.effort_level}")

    info.add_row(
        t("banner.thinking") if thinking_val else "",
        thinking_val,
        t("banner.effort") if effort_val else "",
        effort_val,
    )

    # Permission mode row
    perm_text = Text()
    perm_text.append(mode_label, style="bold bright_magenta")
    info.add_row("", perm_text, "", "")

    # --- Tip ---
    tip = Text(f"  {t('welcome.tip')}", style="dim italic")

    # --- Commands grid: 3 columns, perfectly aligned ---
    cmds_title = Text(f"  {t('guide.commands')}", style="bold bright_blue")

    cmds = Table.grid(padding=(0, 1))
    cmds.add_column(style="bright_magenta", min_width=8)    # cmd 1
    cmds.add_column(style="dim white", min_width=12)        # desc 1
    cmds.add_column(style="bright_magenta", min_width=8)    # cmd 2
    cmds.add_column(style="dim white", min_width=12)        # desc 2
    cmds.add_column(style="bright_magenta", min_width=8)    # cmd 3
    cmds.add_column(style="dim white")                      # desc 3

    cmds.add_row("/help", t("guide.help"), "/skills", t("guide.skills"), "/undo", t("guide.undo"))
    cmds.add_row("/lang", t("guide.lang"), "/think", t("guide.think"), "/quota", t("guide.quota"))
    cmds.add_row("/model", t("guide.model"), "/effort", t("guide.effort"), "/exit", t("guide.exit"))

    # --- Shortcuts grid ---
    shortcuts_title = Text(f"  {t('shortcuts.title')}", style="bold bright_blue")

    shortcuts = Table.grid(padding=(0, 1))
    shortcuts.add_column(style="bright_yellow", min_width=10)  # key
    shortcuts.add_column(style="dim", min_width=12)            # desc
    shortcuts.add_column(style="bright_yellow", min_width=10)  # key 2
    shortcuts.add_column(style="dim", min_width=12)            # desc 2
    shortcuts.add_column(style="bright_yellow", min_width=10)  # key 3
    shortcuts.add_column(style="dim")                          # desc 3

    shortcuts.add_row(
        "Ctrl+C", t("shortcuts.cancel"),
        "Ctrl+C x2", t("shortcuts.exit"),
        "Ctrl+D", t("shortcuts.exit_now"),
    )

    # --- Compose panel ---
    panel = Panel(
        Group(
            subtitle,
            "",
            info,
            tip,
            "",
            cmds_title,
            cmds,
            "",
            shortcuts_title,
            shortcuts,
        ),
        title=title,
        border_style="dim blue",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


# ---------------------------------------------------------------------------
# Slash-command handlers
# ---------------------------------------------------------------------------

def cmd_help(state: CLIState):
    table = Table(title=t("help.title"), border_style="dim blue", show_lines=False)
    table.add_column(t("help.command"), style="bright_magenta", min_width=20, header_style="bright_blue")
    table.add_column(t("help.description"), style="bright_white", header_style="bright_blue")
    cmds = [
        ("/帮助  /help", "cmd.help"), ("/清屏  /clear", "cmd.clear"),
        ("/设置  /settings", "cmd.settings"), ("/模型  /model", "cmd.model"),
        ("/语言  /lang", "cmd.lang"), ("/模板  /template", "cmd.template"),
        ("/历史  /history", "cmd.tokens"), ("/tokens", "cmd.tokens"),
        ("/工具  /tools", "cmd.tools"), ("/自动  /auto", "cmd.auto_mode"),
        ("/安全  /safe", "cmd.safe_mode"), ("/切换  /switch", "cmd.switch_mode"),
        ("/思考  /think", "cmd.thinking"), ("/强度  /effort", "cmd.effort"),
        ("/技能  /skills", "cmd.skills"), ("/会话  /sessions", "cmd.sessions"),
        ("/恢复  /resume", "cmd.resume"), ("/分支  /fork", "cmd.fork"),
        ("/审计  /audit", "cmd.audit"), ("/笔记  /notes", "cmd.notes"),
        ("/撤销  /undo", "cmd.undo"), ("/检查点  /checkpoints", "cmd.checkpoints"),
        ("/额度  /quota", "cmd.quota"), ("/退出  /exit", "cmd.exit"),
    ]
    for names, key in cmds:
        table.add_row(names, t(key))
    console.print(table)


def cmd_clear(state: CLIState):
    state.history.clear()
    state.total_input_tokens = 0
    state.total_output_tokens = 0
    state.system_prompt = None
    state.history.save(HISTORY_FILE)
    console.print(f"[bright_green]>> {t('history.cleared')}[/bright_green]")


def cmd_settings(state: CLIState):
    table = Table(title=t("settings.title"), border_style="dim blue")
    table.add_column(t("settings.key"), style="dim cyan", header_style="bright_blue")
    table.add_column(t("settings.value"), style="bright_white", header_style="bright_blue")
    display_config = dict(state.config)
    if "api_key" in display_config:
        k = display_config["api_key"]
        display_config["api_key"] = k[:8] + "..." + k[-4:] if len(k) > 12 else "***"
    for key, val in display_config.items():
        table.add_row(key, str(val))
    if state.system_prompt:
        table.add_row("system_prompt", state.system_prompt[:60] + "...")
    mode_label = t("mode.safe_detail") if state.permission_mode == "default" else t("mode.auto_detail")
    table.add_row("permission_mode", mode_label)
    backend_label = state.backend.get_mode_name() if state.backend else t("mode.not_initialized")
    table.add_row("backend_mode", backend_label)
    if state.backend and hasattr(state.backend, "thinking_mode"):
        table.add_row(t("thinking.title"), t(f"thinking.{state.backend.thinking_mode}"))
    if state.backend and hasattr(state.backend, "effort_level"):
        table.add_row(t("effort.title"), t(f"effort.{state.backend.effort_level}"))
    console.print(table)


def cmd_model(state: CLIState):
    console.print(f"[bright_blue]{t('model.available')}:[/bright_blue]")
    current_model = state.backend.get_model() if state.backend else state.config.get("model")
    for i, m in enumerate(AVAILABLE_MODELS, 1):
        marker = f" [bright_green]<< {t('model.current')}[/bright_green]" if m == current_model else ""
        console.print(f"  [dim]{i}.[/dim] [bright_cyan]{m}[/bright_cyan]{marker}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print()
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(AVAILABLE_MODELS):
        selected = AVAILABLE_MODELS[int(choice) - 1]
        state.config["model"] = selected
        save_config(state.config)
        if state.backend:
            state.backend.set_model(selected)
        console.print(f"[bright_green]>> {t('model.switched', model=selected)}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_lang(state: CLIState):
    langs = [("zh-CN", "简体中文"), ("zh-TW", "繁體中文"), ("en", "English")]
    for i, (code, name) in enumerate(langs, 1):
        marker = f" [bright_green]<< {t('model.current')}[/bright_green]" if code == get_locale() else ""
        console.print(f"  [dim]{i}.[/dim] [bright_cyan]{name}[/bright_cyan] ({code}){marker}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(langs):
        code = langs[int(choice) - 1][0]
        set_locale(code)
        state.config["language"] = code
        save_config(state.config)
        console.print(f"[bright_green]>> {t('success.prefix')}: {code}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_template(state: CLIState):
    loc = get_locale()
    locale_key = "tw" if loc == "zh-TW" else "zh"
    tpls = list_templates(locale_key)
    console.print(f"[bright_blue]{t('template.available')}:[/bright_blue]")
    for i, tpl in enumerate(tpls, 1):
        console.print(f"  [dim]{i}.[/dim] [bright_cyan]{tpl['name']}[/bright_cyan]")
    console.print(f"  [dim]c.[/dim] {t('template.clear')}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.lower() == "c":
        state.system_prompt = None
        console.print(f"[bright_green]>> {t('template.cleared')}[/bright_green]")
        return
    if choice.isdigit() and 1 <= int(choice) <= len(tpls):
        key = tpls[int(choice) - 1]["key"]
        tpl_data = TEMPLATES[key]
        state.system_prompt = tpl_data["system"]
        console.print(f"[bright_green]>> {t('template.enabled', name=tpls[int(choice) - 1]['name'])}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_history(state: CLIState):
    recent = state.history.get_recent(10)
    if not recent:
        console.print(f"[dim]{t('history.empty')}[/dim]")
        return
    for msg in recent:
        role_style = "bright_cyan" if msg["role"] == "user" else "bright_green"
        label = t("prompt.you") if msg["role"] == "user" else t("prompt.ai")
        content_preview = msg["content"][:120].replace("\n", " ")
        if len(msg["content"]) > 120:
            content_preview += "..."
        console.print(f"  [{role_style}]{label}[/{role_style}]: {content_preview}")


def cmd_tokens(state: CLIState):
    table = Table(title="Token Usage", border_style="dim blue")
    table.add_column("Metric", style="dim cyan", header_style="bright_blue")
    table.add_column("Value", style="bright_green", justify="right", header_style="bright_blue")
    table.add_row("Input tokens", f"{state.total_input_tokens:,}")
    table.add_row("Output tokens", f"{state.total_output_tokens:,}")
    table.add_row("Total tokens", f"{state.total_input_tokens + state.total_output_tokens:,}")
    table.add_row("Messages", str(len(state.history)))
    console.print(table)


def _get_tool_display_name(name: str) -> str:
    key = f"tool.{name}"
    translated = t(key)
    return translated if translated != key else name


def cmd_tools(state: CLIState):
    if state.backend:
        tools = state.backend.available_tools
        backend_name = state.backend.get_mode_name()
    else:
        from .backend import TOOL_NAME_ZH
        tools = list(TOOL_NAME_ZH.keys())
        backend_name = t("mode.not_initialized")
    table = Table(title=f"{t('tools.available')} ({backend_name})", border_style="dim blue", show_lines=True)
    table.add_column(t("tools.name"), style="bright_cyan", min_width=12, header_style="bright_blue")
    table.add_column(t("tools.desc"), style="bright_white", min_width=30, header_style="bright_blue")
    for name in tools:
        table.add_row(name, _get_tool_display_name(name))
    console.print(table)
    console.print(f"[dim]{t('tools.backend')}: {backend_name}[/dim]")


def cmd_auto_mode(state: CLIState):
    state.permission_mode = "acceptEdits"
    if state.backend:
        state.backend.set_permission("acceptEdits")
    console.print(f"[bright_green]>> {t('mode.switched_auto')}[/bright_green]")


def cmd_safe_mode(state: CLIState):
    state.permission_mode = "default"
    if state.backend:
        state.backend.set_permission("default")
    console.print(f"[bright_yellow]>> {t('mode.switched_safe')}[/bright_yellow]")


def first_run_setup():
    welcome_box = Panel(
        f"     {t('skills.welcome_title')} \U0001f389\n"
        f"     {t('skills.welcome_subtitle')}",
        border_style="dim blue", padding=(0, 2),
    )
    console.print(welcome_box)
    console.print()
    recommended = {"fullstack_dev", "code_reviewer", "git_wizard"}
    categories = list_skills_by_category()
    all_keys: list[str] = []
    selected: set[str] = set()
    idx = 0
    skip_remaining = False
    for cat_key, skills in categories.items():
        if skip_remaining:
            for skill in skills:
                all_keys.append(skill.key)
            continue
        cat_label = t(f"category.{cat_key}") if t(f"category.{cat_key}") != f"category.{cat_key}" else CATEGORIES.get(cat_key, cat_key)
        console.print(f"[bright_blue]{cat_label}:[/bright_blue]")
        for skill in skills:
            idx += 1
            all_keys.append(skill.key)
            if skip_remaining:
                continue
            rec_tag = f" [bright_green]({t('skills.recommended')})[/bright_green]" if skill.key in recommended else ""
            console.print(f"  [dim]{idx}.[/dim] {skill.icon} [bright_cyan]{skill.name}[/bright_cyan] - {skill.description}{rec_tag}")
            default = "y" if skill.key in recommended else "n"
            try:
                answer = input(f"         {t('skills.enable_prompt')} (y/n/0={t('skills.skip_remaining')}) [{default}]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer == "0":
                skip_remaining = True
                continue
            if not answer:
                answer = default
            if answer in ("y", "yes"):
                selected.add(skill.key)
        console.print()
    complete_setup(list(selected))
    enabled_names = [SKILLS[k].name for k in all_keys if k in selected]
    if enabled_names:
        console.print(f"[bright_green]{t('skills.enabled_summary', count=len(enabled_names))}: {', '.join(enabled_names)}[/bright_green]")
    else:
        console.print(f"[dim]{t('skills.none_enabled')}[/dim]")
    console.print(f"[dim]{t('skills.manage_tip')}[/dim]")
    console.print()


def cmd_skills(state: CLIState):
    categories = list_skills_by_category()
    all_keys: list[str] = []
    table = Table(title=t("skills.title"), border_style="dim blue", show_lines=False)
    table.add_column("#", style="dim", width=4, header_style="bright_blue")
    table.add_column(t("skills.status"), width=4, header_style="bright_blue")
    table.add_column(t("skills.skill"), style="bright_cyan", min_width=16, header_style="bright_blue")
    table.add_column(t("skills.description"), style="bright_white", header_style="bright_blue")
    idx = 0
    for cat_key, skills in categories.items():
        cat_label = t(f"category.{cat_key}") if t(f"category.{cat_key}") != f"category.{cat_key}" else CATEGORIES.get(cat_key, cat_key)
        table.add_row("", "", f"[bold bright_blue]{cat_label}[/bold bright_blue]", "")
        for skill in skills:
            idx += 1
            all_keys.append(skill.key)
            status = "[bright_green]yes[/bright_green]" if skill.enabled else "[dim]no[/dim]"
            table.add_row(str(idx), status, f"{skill.icon} {skill.name}", skill.description)
    console.print(table)
    console.print()
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print(f"[dim]{t('skills.toggle_prompt')}[/dim]")
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(all_keys):
        key = all_keys[int(choice) - 1]
        new_state = toggle_skill(key)
        skill = SKILLS[key]
        if new_state:
            console.print(f"[bright_green]>> {t('skills.toggled_on')}: {skill.icon} {skill.name}[/bright_green]")
        else:
            console.print(f"[bright_yellow]>> {t('skills.toggled_off')}: {skill.icon} {skill.name}[/bright_yellow]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_thinking(state: CLIState, user_input: str = ""):
    if not state.backend or not hasattr(state.backend, "set_thinking"):
        console.print(f"[bright_yellow]>> {t('backend.no_thinking')}[/bright_yellow]")
        return
    parts = user_input.split()
    arg = parts[1] if len(parts) > 1 else ""
    mode_map = {"深度": "deep", "deep": "deep", "自动": "auto", "auto": "auto", "关闭": "off", "off": "off"}
    # Inline shortcut: /think deep
    if arg:
        mode = mode_map.get(arg)
        if not mode:
            console.print(f"[bright_yellow]>> {t('input.invalid_arg', arg=arg)}[/bright_yellow]")
            console.print(f"[dim]{t('thinking.usage')}[/dim]")
            return
        state.backend.set_thinking(mode)
        state.config["thinking_mode"] = mode
        save_config(state.config)
        console.print(f"[bright_green]>> {t('thinking.switched', mode=t(f'thinking.{mode}'))}[/bright_green]")
        return
    # Interactive menu
    current = state.backend.thinking_mode
    current_label = t(f"thinking.{current}")
    console.print(f"[bright_blue]{t('thinking.current', mode=current_label)}[/bright_blue]")
    console.print()
    options = [
        ("auto", t("thinking.auto"), t("thinking.auto_desc")),
        ("deep", t("thinking.deep"), t("thinking.deep_desc")),
        ("off", t("thinking.off"), t("thinking.off_desc")),
    ]
    for i, (key, label, desc) in enumerate(options, 1):
        marker = f" [bright_green]<< {t('model.current')}[/bright_green]" if key == current else ""
        console.print(f"  [dim]{i}.[/dim] [bright_cyan]{label:<6}[/bright_cyan] [dim]— {desc}[/dim]{marker}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print()
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        mode = options[int(choice) - 1][0]
        state.backend.set_thinking(mode)
        state.config["thinking_mode"] = mode
        save_config(state.config)
        console.print(f"[bright_green]>> {t('thinking.switched', mode=t(f'thinking.{mode}'))}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_effort(state: CLIState, user_input: str = ""):
    if not state.backend or not hasattr(state.backend, "set_effort"):
        console.print(f"[bright_yellow]>> {t('backend.no_effort')}[/bright_yellow]")
        return
    parts = user_input.split()
    arg = parts[1] if len(parts) > 1 else ""
    level_map = {"低": "low", "low": "low", "中": "medium", "medium": "medium", "高": "high", "high": "high", "最大": "max", "max": "max"}
    # Inline shortcut: /effort max
    if arg:
        level = level_map.get(arg)
        if not level:
            console.print(f"[bright_yellow]>> {t('input.invalid_arg', arg=arg)}[/bright_yellow]")
            console.print(f"[dim]{t('effort.usage')}[/dim]")
            return
        state.backend.set_effort(level)
        state.config["effort_level"] = level
        save_config(state.config)
        console.print(f"[bright_green]>> {t('effort.switched', level=t(f'effort.{level}'))}[/bright_green]")
        return
    # Interactive menu
    current = state.backend.effort_level
    current_label = t(f"effort.{current}")
    console.print(f"[bright_blue]{t('effort.current', level=current_label)}[/bright_blue]")
    console.print()
    options = [
        ("low", t("effort.low"), t("effort.low_desc")),
        ("medium", t("effort.medium"), t("effort.medium_desc")),
        ("high", t("effort.high"), t("effort.high_desc")),
        ("max", t("effort.max"), t("effort.max_desc")),
    ]
    for i, (key, label, desc) in enumerate(options, 1):
        marker = f" [bright_green]<< {t('model.current')}[/bright_green]" if key == current else ""
        console.print(f"  [dim]{i}.[/dim] [bright_cyan]{label:<4}[/bright_cyan] [dim]— {desc}[/dim]{marker}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print()
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        level = options[int(choice) - 1][0]
        state.backend.set_effort(level)
        state.config["effort_level"] = level
        save_config(state.config)
        console.print(f"[bright_green]>> {t('effort.switched', level=t(f'effort.{level}'))}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_switch_mode(state: CLIState):
    if not state.backend:
        console.print(f"[bright_red]>> {t('backend.not_initialized')}[/bright_red]")
        return
    current_name = state.backend.get_mode_name()
    from .backend import SDKBackend, APIBackend, _check_claude_cli, _resolve_api_key
    if isinstance(state.backend, SDKBackend):
        api_key = _resolve_api_key(state.config)
        if not api_key:
            console.print(f"[bright_yellow]>> {t('switch.no_api_key')}[/bright_yellow]")
            console.print(f"[dim]   {t('switch.api_key_hint')}[/dim]")
            return
        state.config["mode"] = "api"
        save_config(state.config)
        state.init_backend()
        console.print(f"[bright_green]>> {t('switch.switched', from_mode=current_name, to_mode=state.backend.get_mode_name())}[/bright_green]")
    elif isinstance(state.backend, APIBackend):
        if not _check_claude_cli():
            console.print(f"[bright_yellow]>> {t('switch.no_cli')}[/bright_yellow]")
            return
        state.config["mode"] = "sdk"
        save_config(state.config)
        state.init_backend()
        console.print(f"[bright_green]>> {t('switch.switched', from_mode=current_name, to_mode=state.backend.get_mode_name())}[/bright_green]")
    else:
        console.print(f"[bright_yellow]>> {t('switch.not_supported')}[/bright_yellow]")


def cmd_audit(state: CLIState):
    from .hooks import get_audit_entries, AUDIT_LOG_PATH
    entries = get_audit_entries(count=20)
    if not entries:
        console.print(f"[dim]{t('audit.empty')}[/dim]")
        console.print(f"[dim]{t('audit.log_path')}: {AUDIT_LOG_PATH}[/dim]")
        return
    table = Table(title=t("audit.title"), border_style="dim blue", show_lines=False)
    table.add_column(t("audit.time"), style="dim", min_width=19, header_style="bright_blue")
    table.add_column(t("audit.tool"), style="bright_cyan", min_width=10, header_style="bright_blue")
    table.add_column(t("audit.action"), style="bright_white", min_width=30, header_style="bright_blue")
    table.add_column(t("audit.status"), style="bright_green", min_width=7, header_style="bright_blue")
    for entry in entries:
        try:
            parts = entry.split(" | ")
            ts = parts[0][1:20]
            tool = parts[0].split("TOOL: ")[1] if "TOOL: " in parts[0] else "?"
            inp = parts[1].replace("INPUT: ", "") if len(parts) > 1 else ""
            status = parts[2].replace("STATUS: ", "") if len(parts) > 2 else ""
            status_style = "bright_green" if status == "success" else "bright_red" if status == "blocked" else "bright_yellow"
            table.add_row(ts, tool, inp[:50], f"[{status_style}]{status}[/{status_style}]")
        except Exception:
            table.add_row("", "", entry[:60], "")
    console.print(table)
    console.print(f"[dim]{t('audit.log_path')}: {AUDIT_LOG_PATH}[/dim]")
    console.print(f"[dim]{t('audit.count', count=len(entries))}[/dim]")


def _format_session_time(timestamp_ms: int) -> str:
    from datetime import datetime
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "???"


def _get_session_title(session) -> str:
    title = session.custom_title or session.summary or session.first_prompt or ""
    title = title.replace("\n", " ").strip()
    if len(title) > 50:
        title = title[:47] + "..."
    return title or t("sessions.no_title")


def _show_sessions(state: CLIState, limit: int = 20) -> list:
    from .backend import SDKBackend
    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print(f"[bright_yellow]>> {t('sessions.not_available')}[/bright_yellow]")
        return []
    sessions = state.backend.list_sessions(limit=limit)
    if not sessions:
        console.print(f"[dim]{t('sessions.empty')}[/dim]")
        return []
    console.print(f"[bright_blue]{t('sessions.title')}:[/bright_blue]")
    console.print()
    for i, s in enumerate(sessions, 1):
        time_str = _format_session_time(s.last_modified)
        title = _get_session_title(s)
        cwd_str = f"  [dim]({s.cwd})[/dim]" if s.cwd else ""
        console.print(f"  [dim][{i:>2}][/dim] [dim]{time_str}[/dim]  [bright_cyan]\u201c{title}\u201d[/bright_cyan]{cwd_str}")
    console.print()
    return sessions


def _pick_session(state: CLIState, arg: str = "", sessions: list | None = None) -> str | None:
    if arg.strip().isdigit():
        idx = int(arg.strip())
        if idx == 0:
            return None
        if sessions is None:
            sessions = _show_sessions(state)
        if 1 <= idx <= len(sessions):
            return sessions[idx - 1].session_id
        console.print(f"[bright_yellow]>> {t('input.invalid_number')}[/bright_yellow]")
        return None
    if sessions is None:
        sessions = _show_sessions(state)
    if not sessions:
        return None
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print(f"[dim]{t('sessions.pick_prompt')}[/dim]")
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if choice in ("0", ""):
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(sessions):
        return sessions[int(choice) - 1].session_id
    console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")
    return None


def cmd_sessions(state: CLIState, arg: str = ""):
    sessions = _show_sessions(state)
    if not sessions:
        return
    session_id = _pick_session(state, sessions=sessions)
    if session_id:
        _do_resume(state, session_id, fork=False)

def cmd_resume(state: CLIState, arg: str = ""):
    session_id = _pick_session(state, arg=arg)
    if session_id:
        _do_resume(state, session_id, fork=False)

def cmd_fork(state: CLIState, arg: str = ""):
    session_id = _pick_session(state, arg=arg)
    if session_id:
        _do_resume(state, session_id, fork=True)

def _do_resume(state: CLIState, session_id: str, fork: bool = False):
    from .backend import SDKBackend
    if not state.backend or not isinstance(state.backend, SDKBackend):
        console.print(f"[bright_yellow]>> {t('sessions.not_available')}[/bright_yellow]")
        return
    state.backend.resume_session(session_id, fork=fork)
    action = t('sessions.forked') if fork else t('sessions.resumed')
    console.print(f"[bright_green]>> {action}: {session_id[:12]}...[/bright_green]")
    console.print(f"[dim]{t('sessions.continue_tip')}[/dim]")


def cmd_undo(state: CLIState):
    if not state.backend:
        console.print(f"[bright_red]>> {t('backend.not_initialized')}[/bright_red]")
        return
    mgr = state.backend.checkpoint_mgr
    checkpoints = mgr.list_checkpoints()
    if not checkpoints:
        console.print(f"[bright_yellow]>> {t('undo.no_checkpoints')}[/bright_yellow]")
        return
    latest = checkpoints[0]
    file_count = len(latest.files_backed_up) + len(latest.files_created)
    console.print()
    console.print(f"[bold bright_yellow]{t('undo.confirm_title')}[/bold bright_yellow]")
    console.print(f"  {t('undo.time')}: [bright_cyan]{latest.time_str}[/bright_cyan]")
    console.print(f"  {t('undo.prompt')}: [dim]{latest.prompt_preview}[/dim]")
    console.print(f"  {t('undo.files')}: [bright_cyan]{file_count}[/bright_cyan]")
    if latest.files_backed_up:
        for f in latest.files_backed_up:
            console.print(f"    [dim][{t('undo.restored')}] {f}[/dim]")
    if latest.files_created:
        for f in latest.files_created:
            console.print(f"    [dim][{t('undo.removed')}] {f}[/dim]")
    console.print()
    try:
        answer = input(f"{t('undo.confirm_prompt')} (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
        return
    if answer not in ('y', 'yes'):
        console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
        return
    success, msg, reverted = mgr.undo()
    if success:
        console.print(f"[bright_green]>> {msg}[/bright_green]")
        for f in reverted:
            console.print(f"  [bright_green]{f}[/bright_green]")
    else:
        console.print(f"[bright_red]>> {msg}[/bright_red]")


def cmd_checkpoints(state: CLIState):
    if not state.backend:
        console.print(f"[bright_red]>> {t('backend.not_initialized')}[/bright_red]")
        return
    mgr = state.backend.checkpoint_mgr
    checkpoints = mgr.list_checkpoints()
    if not checkpoints:
        console.print(f"[dim]{t('undo.no_checkpoints')}[/dim]")
        return
    table = Table(title=t('checkpoints.title'), border_style='dim blue', show_lines=False)
    table.add_column('#', style='dim', width=4, header_style='bright_blue')
    table.add_column(t('checkpoints.time'), style='bright_cyan', min_width=20, header_style='bright_blue')
    table.add_column(t('checkpoints.prompt'), style='bright_white', min_width=30, header_style='bright_blue')
    table.add_column(t('checkpoints.files'), style='bright_yellow', justify='right', width=8, header_style='bright_blue')
    for i, ckpt in enumerate(checkpoints, 1):
        file_count = len(ckpt.files_backed_up) + len(ckpt.files_created)
        table.add_row(str(i), ckpt.time_str, ckpt.prompt_preview, str(file_count))
    console.print(table)
    console.print()
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print(f"[dim]{t('checkpoints.undo_tip')}[/dim]")
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice.isdigit() and 1 <= int(choice) <= len(checkpoints):
        target = checkpoints[int(choice) - 1]
        file_count = len(target.files_backed_up) + len(target.files_created)
        console.print()
        console.print(f"[bold bright_yellow]{t('undo.confirm_title')}[/bold bright_yellow]")
        console.print(f"  {t('undo.time')}: [bright_cyan]{target.time_str}[/bright_cyan]")
        console.print(f"  {t('undo.prompt')}: [dim]{target.prompt_preview}[/dim]")
        console.print(f"  {t('undo.files')}: [bright_cyan]{file_count}[/bright_cyan]")
        console.print()
        try:
            answer = input(f"{t('undo.confirm_prompt')} (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if answer not in ('y', 'yes'):
            console.print(f"[dim]>> {t('undo.cancelled')}[/dim]")
            return
        success, msg, reverted = mgr.undo(target.checkpoint_id)
        if success:
            console.print(f"[bright_green]>> {msg}[/bright_green]")
            for f in reverted:
                console.print(f"  [bright_green]{f}[/bright_green]")
        else:
            console.print(f"[bright_red]>> {msg}[/bright_red]")
    else:
        console.print(f"[bright_yellow]>> {t('input.invalid')}[/bright_yellow]")


def cmd_notes(state: CLIState):
    import asyncio as _asyncio
    from .mcp_tools import _note_add, _note_list, _note_search
    console.print(f"[bright_blue]{t('notes.title')}[/bright_blue]")
    console.print(f"  [dim]1.[/dim] {t('notes.add')}")
    console.print(f"  [dim]2.[/dim] {t('notes.recent')}")
    console.print(f"  [dim]3.[/dim] {t('notes.search')}")
    console.print(f"  [dim]0.[/dim] [dim]{t('menu.back')}[/dim]")
    console.print()
    try:
        choice = input(t("menu.choose")).strip()
    except (EOFError, KeyboardInterrupt):
        return
    if choice in ("0", ""):
        return
    if choice == "1":
        try:
            text = input(f"{t('notes.content_prompt')}: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if text:
            result = _asyncio.run(_note_add({"text": text}))
            console.print(f"[bright_green]>> {result['content'][0]['text']}[/bright_green]")
        else:
            console.print(f"[bright_yellow]>> {t('notes.empty_cancelled')}[/bright_yellow]")
    elif choice == "2":
        result = _asyncio.run(_note_list({"days": 7}))
        console.print(result["content"][0]["text"])
    elif choice == "3":
        try:
            keyword = input(f"{t('notes.keyword_prompt')}: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if keyword:
            result = _asyncio.run(_note_search({"keyword": keyword}))
            console.print(result["content"][0]["text"])
        else:
            console.print(f"[bright_yellow]>> {t('notes.keyword_empty')}[/bright_yellow]")


_account_cache: dict | None = None


def _get_cached_account(state: CLIState) -> dict | None:
    """Get account info with caching. Fetches once from SDK, then reuses."""
    global _account_cache
    if _account_cache is not None:
        return _account_cache
    from .backend import SDKBackend
    if state.backend and isinstance(state.backend, SDKBackend):
        try:
            _account_cache = asyncio.run(state.backend.get_account_info())
        except Exception:
            _account_cache = None
    return _account_cache


def cmd_quota(state: CLIState, user_input: str = ""):
    parts = user_input.split()
    arg = parts[1] if len(parts) > 1 else ""
    if arg in ("开", "on"):
        state.config["show_quota"] = True
        save_config(state.config)
        console.print(f"[bright_green]>> {t('quota.enabled')}[/bright_green]")
        return
    if arg in ("关", "off"):
        state.config["show_quota"] = False
        save_config(state.config)
        console.print(f"[bright_yellow]>> {t('quota.disabled')}[/bright_yellow]")
        return

    lines = Text()

    # --- Account info from SDK ---
    account_info = _get_cached_account(state)
    if account_info:
        acct = account_info.get("account") if isinstance(account_info, dict) else None
        if acct is None and hasattr(account_info, "account"):
            acct = account_info.account
        if acct:
            email = acct.get("email", "") if isinstance(acct, dict) else getattr(acct, "email", "")
            plan = acct.get("subscriptionType", "") if isinstance(acct, dict) else getattr(acct, "subscriptionType", "")
            org = acct.get("organization", "") if isinstance(acct, dict) else getattr(acct, "organization", "")

            lines.append(f"\n  {t('account.title')}:\n", style="bold bright_blue")
            if email:
                lines.append(f"  {t('account.email')}: ", style="bright_blue")
                lines.append(f"{email}", style="bright_white")
                if plan:
                    lines.append(f" | ", style="dim")
                    lines.append(f"{plan}", style="bold bright_cyan")
                lines.append("\n")
            elif plan:
                lines.append(f"  {t('account.plan')}: ", style="bright_blue")
                lines.append(f"{plan}\n", style="bold bright_cyan")
            if org:
                lines.append(f"  {t('account.org')}: ", style="bright_blue")
                lines.append(f"{org}\n", style="bright_white")

    # --- Real usage from Claude API (utilization percentages) ---
    usage = get_cached_usage()
    if usage:
        five_hour = usage.get("five_hour", {})
        seven_day = usage.get("seven_day", {})

        five_pct = five_hour.get("utilization", 0)
        seven_pct = seven_day.get("utilization", 0)
        five_resets = five_hour.get("resets_at", "")
        seven_resets = seven_day.get("resets_at", "")

        # 5-hour window
        lines.append(f"\n  {t('quota.5h_window')}:\n", style="bold bright_blue")
        bar_5h = make_usage_bar(five_pct)
        bar_style = "bright_green" if five_pct < 50 else "bright_yellow" if five_pct < 80 else "bright_red"
        lines.append(f"  {bar_5h}", style=bar_style)
        lines.append(f"  {five_pct}%", style=bar_style)
        if five_resets:
            lines.append(f"  {t('quota.resets_in')}: {format_time_remaining(five_resets)}", style="dim")
        lines.append("\n")

        # Weekly
        lines.append(f"\n  {t('quota.weekly')}:\n", style="bold bright_blue")
        bar_7d = make_usage_bar(seven_pct)
        bar_style_7d = "bright_green" if seven_pct < 50 else "bright_yellow" if seven_pct < 80 else "bright_red"
        lines.append(f"  {bar_7d}", style=bar_style_7d)
        lines.append(f"  {seven_pct}%", style=bar_style_7d)
        if seven_resets:
            lines.append(f"  {t('quota.resets_in')}: {format_time_remaining(seven_resets)}", style="dim")
        lines.append("\n")

    # --- Session stats (always available) ---
    sess = state.quota.get_session_stats()
    today_local = state.quota.get_today_stats()

    lines.append(f"\n  {t('quota.session')}:\n", style="bold bright_blue")
    lines.append(f"  {sess['requests']} {t('quota.requests')}", style="bright_cyan")
    lines.append(f"  |  {format_tokens(sess['total_tokens'])} tokens", style="bright_cyan")
    if sess['input_tokens'] or sess['output_tokens']:
        lines.append(f"  ({t('quota.input')}: {format_tokens(sess['input_tokens'])}, {t('quota.output')}: {format_tokens(sess['output_tokens'])})", style="dim")
    lines.append("\n")

    if today_local["requests"] > 0:
        lines.append(f"\n  {t('quota.local_today')}:\n", style="bold bright_blue")
        lines.append(f"  {today_local['requests']} {t('quota.requests')}", style="bright_cyan")
        lines.append(f"  |  {format_tokens(today_local['total_tokens'])} tokens\n", style="bright_cyan")

    # --- Real Claude stats from stats-cache.json ---
    real = get_real_usage_summary()
    if real:
        lines.append(f"\n  Claude Stats:\n", style="bold bright_blue")
        lines.append(f"  {t('quota.total_sessions')}: ", style="bright_white")
        lines.append(f"{format_number(real['total_sessions'])}", style="bright_cyan")
        lines.append(f"  |  {t('quota.total_messages')}: ", style="bright_white")
        lines.append(f"{format_number(real['total_messages'])}\n", style="bright_cyan")

        if real.get("first_session_date"):
            date_str = real["first_session_date"][:10]
            lines.append(f"  {t('quota.since')}: {date_str}\n", style="dim")

        if real.get("today"):
            td = real["today"]
            lines.append(f"\n  {t('quota.today')} ({td.get('date', '')}):\n", style="bright_blue")
            lines.append(f"  {t('quota.messages')}: {format_number(td.get('messageCount', 0))}", style="bright_white")
            lines.append(f"  |  {t('quota.sessions')}: {td.get('sessionCount', 0)}", style="bright_white")
            lines.append(f"  |  {t('quota.tool_calls')}: {format_number(td.get('toolCallCount', 0))}\n", style="bright_white")
        else:
            lines.append(f"\n  {t('quota.no_today_data')}\n", style="dim")

        # Recent days
        if real.get("recent_days"):
            lines.append(f"\n  {t('quota.recent_days')}:\n", style="bright_blue")
            for day in real["recent_days"][:5]:
                lines.append(f"  {day.get('date', '?'):>10}  ", style="dim")
                lines.append(f"{format_number(day.get('messageCount', 0)):>8} msgs", style="bright_white")
                lines.append(f"  {day.get('sessionCount', 0)} sessions\n", style="dim")

        # Model usage
        if real.get("models"):
            lines.append(f"\n  {t('quota.model_usage')}:\n", style="bright_blue")
            for model_name, model_usage in real["models"].items():
                inp = model_usage.get("inputTokens", 0)
                out = model_usage.get("outputTokens", 0)
                cache_r = model_usage.get("cacheReadInputTokens", 0)
                lines.append(f"  {model_name}:\n", style="bright_cyan")
                lines.append(f"    {t('quota.input')}: {format_tokens(inp)}  {t('quota.output')}: {format_tokens(out)}", style="dim")
                if cache_r:
                    lines.append(f"  {t('quota.cache_read')}: {format_tokens(cache_r)}", style="dim")
                lines.append("\n")
    elif not usage:
        lines.append(f"\n  {t('quota.no_real_data')}\n", style="dim")

    panel = Panel(lines, title=t("quota.title"), border_style="dim blue", padding=(0, 1))
    console.print(panel)
    console.print()
    show_quota = state.config.get("show_quota", True)
    toggle_label = f"[bright_green]{t('quota.on')}[/bright_green]" if show_quota else f"[bright_yellow]{t('quota.off')}[/bright_yellow]"
    console.print(f"[dim]  {t('quota.mini_label')}: {toggle_label}  ({t('quota.toggle_tip')})[/dim]")


# ---------------------------------------------------------------------------
# Command dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "help": cmd_help, "clear": cmd_clear, "settings": cmd_settings,
    "model": cmd_model, "lang": cmd_lang, "template": cmd_template,
    "history": cmd_history, "tokens": cmd_tokens, "tools": cmd_tools,
    "auto_mode": cmd_auto_mode, "safe_mode": cmd_safe_mode,
    "switch_mode": cmd_switch_mode, "skills": cmd_skills,
    "thinking": cmd_thinking, "effort": cmd_effort, "audit": cmd_audit,
    "notes": cmd_notes, "sessions": cmd_sessions, "resume": cmd_resume,
    "fork": cmd_fork, "undo": cmd_undo, "checkpoints": cmd_checkpoints,
    "quota": cmd_quota,
}


# ---------------------------------------------------------------------------
# Chat via Backend abstraction
# ---------------------------------------------------------------------------

async def chat_async(user_input: str, state: CLIState):
    if not state.backend:
        console.print(f"[bright_red]>> {t('backend.not_initialized_restart')}[/bright_red]")
        return
    state.history.add("user", user_input)
    system_prompt = state.system_prompt or _default_system_prompt()
    skill_prompt = get_skill_system_prompt()
    if skill_prompt:
        system_prompt = system_prompt.rstrip() + "\n\n" + skill_prompt
    history_messages = []
    recent = state.history.get_recent(state.config.get("history_size", 100))
    for msg in recent[:-1]:
        history_messages.append({"role": msg["role"], "content": msg["content"]})
    ai_label = t("prompt.ai")
    response_text_parts = []
    console.print()
    try:
        async for event in state.backend.ask(
            prompt=user_input, system_prompt=system_prompt,
            history=history_messages if history_messages else None,
        ):
            if event.type == "text":
                response_text_parts.append(event.text)
                console.print(f"[bright_green]{ai_label}[/bright_green]:", end=" ")
                console.print(event.text, highlight=False, style="bright_white")
                console.print()
            elif event.type == "tool_use" and event.tool:
                console.print(f"  [bright_cyan]>>> {t('chat.tool_call')}: {event.tool.name}[/bright_cyan] [dim]- {event.tool.name_zh}[/dim]")
            elif event.type == "tool_result" and event.tool:
                result_preview = event.tool.result[:200] if event.tool.result else ""
                if result_preview:
                    console.print(Panel(result_preview, title=f"{t('chat.tool_result')}: {event.tool.name_zh or event.tool.name}", border_style="dim green", expand=False))
            elif event.type == "thinking":
                thinking_mode = getattr(state.backend, "thinking_mode", "auto")
                if thinking_mode == "deep":
                    console.print(f"  [dim italic bright_magenta]>>> {t('thinking.deep_indicator')}[/dim italic bright_magenta]")
                    if event.text and len(event.text) > 0:
                        preview = event.text[:100].replace("\n", " ")
                        if len(event.text) > 100:
                            preview += "..."
                        console.print(f"  [dim]   {preview}[/dim]")
                else:
                    console.print(f"  [dim italic bright_magenta]>>> {t('thinking')}[/dim italic bright_magenta]")
            elif event.type == "done":
                input_t = event.usage.get("input_tokens", 0) if event.usage else 0
                output_t = event.usage.get("output_tokens", 0) if event.usage else 0
                cost_usd = event.usage.get("total_cost_usd", 0.0) if event.usage else 0.0
                num_turns = event.usage.get("num_turns", 1) if event.usage else 1
                duration_ms = event.usage.get("duration_ms", 0) if event.usage else 0
                state.total_input_tokens += input_t
                state.total_output_tokens += output_t
                model = state.backend.get_model() if state.backend else ""
                state.quota.record_usage(input_tokens=input_t, output_tokens=output_t, model=model, cost_usd=cost_usd, prompt=user_input[:80] if user_input else "", num_turns=num_turns, duration_ms=duration_ms)
                if state.config.get("show_token_usage") and event.usage:
                    console.print(f"  [dim]{t('chat.usage', input=f'{input_t:,}', output=f'{output_t:,}')}[/dim]")
                if state.config.get("show_quota", True):
                    sess = state.quota.get_session_stats()
                    mini_parts = []
                    # Show real utilization if available
                    real_usage = get_cached_usage()
                    if real_usage:
                        five_h = real_usage.get("five_hour", {})
                        seven_d = real_usage.get("seven_day", {})
                        five_pct = five_h.get("utilization", 0)
                        seven_pct = seven_d.get("utilization", 0)
                        five_resets = five_h.get("resets_at", "")
                        bar_5 = make_usage_bar(five_pct, 10)
                        bar_7 = make_usage_bar(seven_pct, 10)
                        mini_parts.append(f"5h: {five_pct}% {bar_5}")
                        mini_parts.append(f"{t('quota.weekly')}: {seven_pct}% {bar_7}")
                        if five_resets:
                            mini_parts.append(f"{t('quota.resets_in')}: {format_time_remaining(five_resets)}")
                    mini_parts.append(f"Session: {sess['requests']} {t('quota.requests')} | {format_tokens(sess['total_tokens'])} tokens")
                    console.print(f"  [dim]{' | '.join(mini_parts)}[/dim]")
            elif event.type == "error":
                console.print(f"\n[bright_red]>> {event.text}[/bright_red]")
                if state.history.messages and state.history.messages[-1]["role"] == "user":
                    state.history.messages.pop()
                return
    except KeyboardInterrupt:
        console.print(f"\n[bright_yellow]>> {t('chat.interrupted')}[/bright_yellow]")
    except Exception as e:
        console.print(f"\n[bright_red]>> {t('chat.error', error=str(e))}[/bright_red]")
        if state.history.messages and state.history.messages[-1]["role"] == "user":
            state.history.messages.pop()
        return
    full_response = "\n".join(response_text_parts)
    if full_response:
        state.history.add("assistant", full_response)
        state.history.save(HISTORY_FILE)
    console.print()


def chat(user_input: str, state: CLIState):
    asyncio.run(chat_async(user_input, state))


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def run():
    state = CLIState()
    lang = state.config.get("language", "auto")
    if lang != "auto":
        set_locale(lang)
    if not has_completed_setup():
        first_run_setup()
    try:
        state.init_backend()
    except RuntimeError as e:
        console.print(f"[bright_red]{e}[/bright_red]")
        raise SystemExit(1)
    print_banner(state)
    _last_ctrl_c = 0.0

    def _cleanup():
        """断开持久连接并保存历史。"""
        state.history.save(HISTORY_FILE)
        if state.backend and hasattr(state.backend, 'disconnect'):
            try:
                asyncio.run(state.backend.disconnect())
            except Exception:
                pass

    while True:
        try:
            prompt_label = t("prompt.you")
            user_input = input(f"[{prompt_label}] > ").strip()
        except EOFError:
            console.print()
            console.print(t("goodbye"))
            _cleanup()
            break
        except KeyboardInterrupt:
            now = time.time()
            if now - _last_ctrl_c < 2.0:
                console.print()
                console.print(t("goodbye"))
                _cleanup()
                break
            else:
                _last_ctrl_c = now
                console.print(f"\n[bright_yellow]{t('ctrl_c.hint')}[/bright_yellow]")
                continue
        if not user_input:
            continue
        first_word = user_input.split()[0] if user_input.startswith("/") else None
        if first_word and first_word in COMMAND_MAP:
            cmd_key = COMMAND_MAP[first_word]
            if cmd_key == "exit":
                console.print(t("goodbye"))
                _cleanup()
                break
            handler = COMMANDS.get(cmd_key)
            if handler:
                if cmd_key in ("thinking", "effort", "quota"):
                    handler(state, user_input)
                elif cmd_key in ("resume", "fork"):
                    parts = user_input.split(maxsplit=1)
                    arg = parts[1] if len(parts) > 1 else ""
                    handler(state, arg=arg)
                else:
                    handler(state)
            continue
        if user_input.startswith("/"):
            console.print(f"[bright_yellow]>> {t('cmd.unknown')}[/bright_yellow]")
            continue
        chat(user_input, state)


if __name__ == "__main__":
    run()
