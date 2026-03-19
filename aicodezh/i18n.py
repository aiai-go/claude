"""Internationalization support for claudezh."""

import locale as _locale
import os

# Translation table: key -> {locale -> text}
_STRINGS = {
    # Welcome & banner
    "welcome.subtitle": {
        "zh-CN": "基于 Claude 大模型的智能编程终端",
        "zh-TW": "基於 Claude 大模型的智慧編程終端",
        "en": "Intelligent coding terminal powered by Claude",
    },
    "welcome.cwd": {
        "zh-CN": "当前目录",
        "zh-TW": "當前目錄",
        "en": "Directory",
    },
    "welcome.lang": {
        "zh-CN": "语言",
        "zh-TW": "語言",
        "en": "Language",
    },
    "welcome.lang_name": {
        "zh-CN": "简体中文",
        "zh-TW": "繁體中文",
        "en": "English",
    },
    "welcome.tip": {
        "zh-CN": "输入 /帮助 查看所有命令",
        "zh-TW": "輸入 /幫助 查看所有命令",
        "en": "Type /help to see all commands",
    },
    # Prompt
    "prompt.you": {
        "zh-CN": "你",
        "zh-TW": "你",
        "en": "You",
    },
    "prompt.ai": {
        "zh-CN": "助手",
        "zh-TW": "助手",
        "en": "AI",
    },
    # Thinking
    "thinking": {
        "zh-CN": "思考中...",
        "zh-TW": "思考中...",
        "en": "Thinking...",
    },
    # Help
    "help.title": {
        "zh-CN": "命令帮助",
        "zh-TW": "命令幫助",
        "en": "Command Help",
    },
    "help.command": {
        "zh-CN": "命令",
        "zh-TW": "命令",
        "en": "Command",
    },
    "help.description": {
        "zh-CN": "说明",
        "zh-TW": "說明",
        "en": "Description",
    },
    # Settings
    "settings.title": {
        "zh-CN": "当前设置",
        "zh-TW": "當前設定",
        "en": "Current Settings",
    },
    "settings.key": {
        "zh-CN": "配置项",
        "zh-TW": "配置項",
        "en": "Setting",
    },
    "settings.value": {
        "zh-CN": "值",
        "zh-TW": "值",
        "en": "Value",
    },
    # File operations
    "file.created": {
        "zh-CN": "已创建",
        "zh-TW": "已創建",
        "en": "Created",
    },
    "file.modified": {
        "zh-CN": "已修改",
        "zh-TW": "已修改",
        "en": "Modified",
    },
    "file.deleted": {
        "zh-CN": "已删除",
        "zh-TW": "已刪除",
        "en": "Deleted",
    },
    "file.read": {
        "zh-CN": "已读取",
        "zh-TW": "已讀取",
        "en": "Read",
    },
    # Goodbye
    "goodbye": {
        "zh-CN": "再见！祝编程愉快 🎉",
        "zh-TW": "再見！祝編程愉快 🎉",
        "en": "Goodbye! Happy coding 🎉",
    },
    # Errors
    "error.prefix": {
        "zh-CN": "错误",
        "zh-TW": "錯誤",
        "en": "Error",
    },
    "success.prefix": {
        "zh-CN": "成功",
        "zh-TW": "成功",
        "en": "Success",
    },
    # Commands
    "cmd.help": {
        "zh-CN": "显示帮助信息",
        "zh-TW": "顯示幫助信息",
        "en": "Show help",
    },
    "cmd.clear": {
        "zh-CN": "清空对话历史",
        "zh-TW": "清空對話歷史",
        "en": "Clear conversation history",
    },
    "cmd.settings": {
        "zh-CN": "显示当前设置",
        "zh-TW": "顯示當前設定",
        "en": "Show current settings",
    },
    "cmd.model": {
        "zh-CN": "切换模型",
        "zh-TW": "切換模型",
        "en": "Switch model",
    },
    "cmd.lang": {
        "zh-CN": "切换语言",
        "zh-TW": "切換語言",
        "en": "Switch language",
    },
    "cmd.exit": {
        "zh-CN": "退出程序",
        "zh-TW": "退出程序",
        "en": "Exit",
    },
    "cmd.template": {
        "zh-CN": "使用预设模板",
        "zh-TW": "使用預設模板",
        "en": "Use a preset template",
    },
    "cmd.tokens": {
        "zh-CN": "显示 token 用量",
        "zh-TW": "顯示 token 用量",
        "en": "Show token usage",
    },
    "cmd.compact": {
        "zh-CN": "压缩对话历史",
        "zh-TW": "壓縮對話歷史",
        "en": "Compact conversation history",
    },
    "cmd.tools": {
        "zh-CN": "列出可用工具",
        "zh-TW": "列出可用工具",
        "en": "List available tools",
    },
}

_current_locale: str | None = None


def get_locale() -> str:
    """Detect or return the current locale.

    Resolution order:
      1. Cached value (set by set_locale)
      2. CLAUDEZH_LANG env var
      3. System locale detection
      4. Default: zh-CN
    """
    global _current_locale
    if _current_locale:
        return _current_locale

    # Env override
    env_lang = os.environ.get("CLAUDEZH_LANG", "").strip()
    if env_lang in ("zh-CN", "zh-TW", "en"):
        _current_locale = env_lang
        return _current_locale

    # System locale detection (getdefaultlocale removed in Python 3.13)
    try:
        sys_locale = _locale.getlocale()[0] or ""
    except Exception:
        sys_locale = os.environ.get("LANG", "")

    if "zh_TW" in sys_locale or "zh_HK" in sys_locale:
        _current_locale = "zh-TW"
    elif sys_locale.startswith("en"):
        _current_locale = "en"
    else:
        _current_locale = "zh-CN"

    return _current_locale


def set_locale(loc: str):
    """Override the current locale."""
    global _current_locale
    if loc in ("zh-CN", "zh-TW", "en"):
        _current_locale = loc


def t(key: str, **kwargs) -> str:
    """Translate a key to the current locale.

    Supports ``str.format()`` placeholders via **kwargs.
    Falls back to zh-CN, then to the key itself.
    """
    loc = get_locale()
    entry = _STRINGS.get(key)
    if entry is None:
        return key

    text = entry.get(loc) or entry.get("zh-CN") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
