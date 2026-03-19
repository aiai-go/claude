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
    "cmd.skills": {
        "zh-CN": "管理 AI 技能",
        "zh-TW": "管理 AI 技能",
        "en": "Manage AI skills",
    },
    # Skills
    "skills.welcome_title": {
        "zh-CN": "欢迎使用 claudezh!",
        "zh-TW": "歡迎使用 claudezh!",
        "en": "Welcome to claudezh!",
    },
    "skills.welcome_subtitle": {
        "zh-CN": "让我们选择你需要的技能",
        "zh-TW": "讓我們選擇你需要的技能",
        "en": "Let's pick the skills you need",
    },
    "skills.enable_prompt": {
        "zh-CN": "启用?",
        "zh-TW": "啟用?",
        "en": "Enable?",
    },
    "skills.recommended": {
        "zh-CN": "推荐",
        "zh-TW": "推薦",
        "en": "recommended",
    },
    "skills.enabled_summary": {
        "zh-CN": "已启用 {count} 个技能",
        "zh-TW": "已啟用 {count} 個技能",
        "en": "{count} skills enabled",
    },
    "skills.manage_tip": {
        "zh-CN": "你可以随时用 /技能 命令管理技能",
        "zh-TW": "你可以隨時用 /技能 命令管理技能",
        "en": "You can manage skills anytime with /skills",
    },
    "skills.title": {
        "zh-CN": "技能管理",
        "zh-TW": "技能管理",
        "en": "Skill Management",
    },
    "skills.toggle_prompt": {
        "zh-CN": "输入编号切换技能 (0 返回)",
        "zh-TW": "輸入編號切換技能 (0 返回)",
        "en": "Enter number to toggle (0 to go back)",
    },
    "skills.toggled_on": {
        "zh-CN": "已启用",
        "zh-TW": "已啟用",
        "en": "Enabled",
    },
    "skills.toggled_off": {
        "zh-CN": "已禁用",
        "zh-TW": "已停用",
        "en": "Disabled",
    },
    # Sessions
    "sessions.title": {
        "zh-CN": "最近的会话",
        "zh-TW": "最近的會話",
        "en": "Recent Sessions",
    },
    "sessions.empty": {
        "zh-CN": "暂无历史会话",
        "zh-TW": "暫無歷史會話",
        "en": "No past sessions found",
    },
    "sessions.pick_prompt": {
        "zh-CN": "输入编号恢复会话，按回车返回",
        "zh-TW": "輸入編號恢復會話，按回車返回",
        "en": "Enter number to resume, press Enter to go back",
    },
    "sessions.resumed": {
        "zh-CN": "已恢复会话",
        "zh-TW": "已恢復會話",
        "en": "Session resumed",
    },
    "sessions.forked": {
        "zh-CN": "已从会话分支",
        "zh-TW": "已從會話分支",
        "en": "Session forked",
    },
    "sessions.not_available": {
        "zh-CN": "会话恢复仅在订阅模式下可用",
        "zh-TW": "會話恢復僅在訂閱模式下可用",
        "en": "Session resume is only available in SDK mode",
    },
    "cmd.sessions": {
        "zh-CN": "列出/恢复历史会话",
        "zh-TW": "列出/恢復歷史會話",
        "en": "List/resume past sessions",
    },
    "cmd.resume": {
        "zh-CN": "恢复历史会话",
        "zh-TW": "恢復歷史會話",
        "en": "Resume a past session",
    },
    "cmd.fork": {
        "zh-CN": "从历史会话分支",
        "zh-TW": "從歷史會話分支",
        "en": "Fork from a past session",
    },
    # Thinking
    "thinking.title": {
        "zh-CN": "思考模式",
        "zh-TW": "思考模式",
        "en": "Thinking Mode",
    },
    "thinking.auto": {
        "zh-CN": "自适应",
        "zh-TW": "自適應",
        "en": "Adaptive",
    },
    "thinking.deep": {
        "zh-CN": "深度思考",
        "zh-TW": "深度思考",
        "en": "Deep Thinking",
    },
    "thinking.off": {
        "zh-CN": "关闭",
        "zh-TW": "關閉",
        "en": "Off",
    },
    "thinking.current": {
        "zh-CN": "当前思考模式: {mode}",
        "zh-TW": "當前思考模式: {mode}",
        "en": "Current thinking mode: {mode}",
    },
    "thinking.switched": {
        "zh-CN": "已切换思考模式: {mode}",
        "zh-TW": "已切換思考模式: {mode}",
        "en": "Thinking mode switched: {mode}",
    },
    "thinking.usage": {
        "zh-CN": "用法: /思考 [深度|自动|关闭]",
        "zh-TW": "用法: /思考 [深度|自動|關閉]",
        "en": "Usage: /think [deep|auto|off]",
    },
    "thinking.deep_indicator": {
        "zh-CN": "深度思考中...",
        "zh-TW": "深度思考中...",
        "en": "Deep thinking...",
    },
    # Effort
    "effort.title": {
        "zh-CN": "推理强度",
        "zh-TW": "推理強度",
        "en": "Effort Level",
    },
    "effort.low": {
        "zh-CN": "低",
        "zh-TW": "低",
        "en": "Low",
    },
    "effort.medium": {
        "zh-CN": "中",
        "zh-TW": "中",
        "en": "Medium",
    },
    "effort.high": {
        "zh-CN": "高",
        "zh-TW": "高",
        "en": "High",
    },
    "effort.max": {
        "zh-CN": "最大",
        "zh-TW": "最大",
        "en": "Max",
    },
    "effort.current": {
        "zh-CN": "当前推理强度: {level}",
        "zh-TW": "當前推理強度: {level}",
        "en": "Current effort level: {level}",
    },
    "effort.switched": {
        "zh-CN": "已切换推理强度: {level}",
        "zh-TW": "已切換推理強度: {level}",
        "en": "Effort level switched: {level}",
    },
    "effort.usage": {
        "zh-CN": "用法: /强度 [低|中|高|最大]",
        "zh-TW": "用法: /強度 [低|中|高|最大]",
        "en": "Usage: /effort [low|medium|high|max]",
    },
    # Commands
    "cmd.thinking": {
        "zh-CN": "控制思考模式 (深度/自动/关闭)",
        "zh-TW": "控制思考模式 (深度/自動/關閉)",
        "en": "Control thinking mode (deep/auto/off)",
    },
    "cmd.effort": {
        "zh-CN": "控制推理强度 (低/中/高/最大)",
        "zh-TW": "控制推理強度 (低/中/高/最大)",
        "en": "Control effort level (low/medium/high/max)",
    },
    # 审计日志
    "cmd.audit": {
        "zh-CN": "查看操作审计日志",
        "zh-TW": "查看操作審計日誌",
        "en": "View audit log",
    },
    "audit.title": {
        "zh-CN": "操作审计日志",
        "zh-TW": "操作審計日誌",
        "en": "Audit Log",
    },
    "audit.empty": {
        "zh-CN": "暂无审计记录",
        "zh-TW": "暫無審計記錄",
        "en": "No audit entries",
    },
    # 安全钩子
    "hooks.blocked": {
        "zh-CN": "危险命令已被安全系统拦截",
        "zh-TW": "危險命令已被安全系統攔截",
        "en": "Dangerous command blocked by safety system",
    },
    "hooks.warning": {
        "zh-CN": "安全警告",
        "zh-TW": "安全警告",
        "en": "Safety Warning",
    },
    # Undo / Checkpoints
    "cmd.undo": {
        "zh-CN": "撤销上次 AI 的文件修改",
        "zh-TW": "撤銷上次 AI 的文件修改",
        "en": "Undo last AI file changes",
    },
    "cmd.checkpoints": {
        "zh-CN": "查看可用的文件检查点",
        "zh-TW": "查看可用的文件檢查點",
        "en": "View available file checkpoints",
    },
    "undo.no_checkpoints": {
        "zh-CN": "没有可用的检查点",
        "zh-TW": "沒有可用的檢查點",
        "en": "No checkpoints available",
    },
    "undo.confirm_title": {
        "zh-CN": "即将撤销以下修改:",
        "zh-TW": "即將撤銷以下修改:",
        "en": "About to undo the following changes:",
    },
    "undo.time": {
        "zh-CN": "时间",
        "zh-TW": "時間",
        "en": "Time",
    },
    "undo.prompt": {
        "zh-CN": "提示词",
        "zh-TW": "提示詞",
        "en": "Prompt",
    },
    "undo.files": {
        "zh-CN": "涉及文件数",
        "zh-TW": "涉及文件數",
        "en": "Files affected",
    },
    "undo.confirm_prompt": {
        "zh-CN": "确认撤销?",
        "zh-TW": "確認撤銷?",
        "en": "Confirm undo?",
    },
    "undo.cancelled": {
        "zh-CN": "已取消",
        "zh-TW": "已取消",
        "en": "Cancelled",
    },
    "checkpoints.title": {
        "zh-CN": "文件检查点",
        "zh-TW": "文件檢查點",
        "en": "File Checkpoints",
    },
    "checkpoints.time": {
        "zh-CN": "时间",
        "zh-TW": "時間",
        "en": "Time",
    },
    "checkpoints.prompt": {
        "zh-CN": "提示词",
        "zh-TW": "提示詞",
        "en": "Prompt",
    },
    "checkpoints.files": {
        "zh-CN": "文件数",
        "zh-TW": "文件數",
        "en": "Files",
    },
    "checkpoints.undo_tip": {
        "zh-CN": "输入编号撤销到该检查点 (0 返回)",
        "zh-TW": "輸入編號撤銷到該檢查點 (0 返回)",
        "en": "Enter number to undo to that checkpoint (0 to go back)",
    },
    "checkpoints.select_prompt": {
        "zh-CN": "选择检查点:",
        "zh-TW": "選擇檢查點:",
        "en": "Select checkpoint:",
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
