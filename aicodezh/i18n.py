"""Internationalization support for @aiai-go/claude."""

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
        "zh-CN": "目录",
        "zh-TW": "目錄",
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
    "welcome.model": {
        "zh-CN": "模型",
        "zh-TW": "模型",
        "en": "Model",
    },
    "welcome.mode": {
        "zh-CN": "模式",
        "zh-TW": "模式",
        "en": "Mode",
    },
    "welcome.hints": {
        "zh-CN": "提示: /自动 切换自动模式 | /安全 切换安全模式 | /切换 切换后端模式",
        "zh-TW": "提示: /自動 切換自動模式 | /安全 切換安全模式 | /切換 切換後端模式",
        "en": "Tip: /auto for auto mode | /safe for safe mode | /switch to toggle backend",
    },
    "banner.safe_mode": {
        "zh-CN": "安全模式",
        "zh-TW": "安全模式",
        "en": "Safe Mode",
    },
    "banner.auto_mode": {
        "zh-CN": "自动模式",
        "zh-TW": "自動模式",
        "en": "Auto Mode",
    },
    "banner.thinking": {
        "zh-CN": "思考",
        "zh-TW": "思考",
        "en": "Thinking",
    },
    "banner.effort": {
        "zh-CN": "强度",
        "zh-TW": "強度",
        "en": "Effort",
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
    "tool.Read": {"zh-CN": "读取文件内容", "zh-TW": "讀取檔案內容", "en": "Read file contents"},
    "tool.Edit": {"zh-CN": "编辑修改文件", "zh-TW": "編輯修改檔案", "en": "Edit and modify files"},
    "tool.Write": {"zh-CN": "创建/写入文件", "zh-TW": "建立/寫入檔案", "en": "Create or write files"},
    "tool.Bash": {"zh-CN": "执行终端命令", "zh-TW": "執行終端命令", "en": "Execute shell commands"},
    "tool.Glob": {"zh-CN": "按模式搜索文件", "zh-TW": "按模式搜尋檔案", "en": "Search files by pattern"},
    "tool.Grep": {"zh-CN": "搜索文件内容", "zh-TW": "搜尋檔案內容", "en": "Search file contents"},
    "tool.project_memory_read": {"zh-CN": "读取项目记忆", "zh-TW": "讀取專案記憶", "en": "Read project memory"},
    "tool.project_memory_write": {"zh-CN": "写入项目记忆", "zh-TW": "寫入專案記憶", "en": "Write project memory"},
    "tool.project_memory_list": {"zh-CN": "列出项目记忆", "zh-TW": "列出專案記憶", "en": "List project memory"},
    "tool.code_stats": {"zh-CN": "代码统计分析", "zh-TW": "程式碼統計分析", "en": "Code statistics"},
    "tool.check_dependencies": {"zh-CN": "检查依赖状态", "zh-TW": "檢查依賴狀態", "en": "Check dependencies"},
    "tool.git_summary": {"zh-CN": "Git 历史摘要", "zh-TW": "Git 歷史摘要", "en": "Git history summary"},
    "tool.git_blame_summary": {"zh-CN": "Git 作者分析", "zh-TW": "Git 作者分析", "en": "Git blame summary"},
    "tool.git_changes_since": {"zh-CN": "Git 最近变更", "zh-TW": "Git 最近變更", "en": "Git recent changes"},
    "tool.detect_environment": {"zh-CN": "检测运行环境", "zh-TW": "偵測執行環境", "en": "Detect environment"},
    "tool.note_add": {"zh-CN": "添加快速笔记", "zh-TW": "新增快速筆記", "en": "Add quick note"},
    "tool.note_list": {"zh-CN": "查看最近笔记", "zh-TW": "查看最近筆記", "en": "List recent notes"},
    "tool.note_search": {"zh-CN": "搜索笔记", "zh-TW": "搜尋筆記", "en": "Search notes"},
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
        "zh-CN": "欢迎使用 @aiai-go/claude!",
        "zh-TW": "歡迎使用 @aiai-go/claude!",
        "en": "Welcome to @aiai-go/claude!",
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
    "thinking.auto_desc": {
        "zh-CN": "AI 自动决定思考深度",
        "zh-TW": "AI 自動決定思考深度",
        "en": "AI decides thinking depth",
    },
    "thinking.deep_desc": {
        "zh-CN": "开启深度思考 (复杂问题)",
        "zh-TW": "開啟深度思考 (複雜問題)",
        "en": "Deep thinking (complex problems)",
    },
    "thinking.off_desc": {
        "zh-CN": "不思考 (快速回答)",
        "zh-TW": "不思考 (快速回答)",
        "en": "No thinking (quick answers)",
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
    "effort.low_desc": {
        "zh-CN": "快速简单回答",
        "zh-TW": "快速簡單回答",
        "en": "Quick simple answers",
    },
    "effort.medium_desc": {
        "zh-CN": "标准回答",
        "zh-TW": "標準回答",
        "en": "Standard responses",
    },
    "effort.high_desc": {
        "zh-CN": "详细深入回答",
        "zh-TW": "詳細深入回答",
        "en": "Detailed thorough answers",
    },
    "effort.max_desc": {
        "zh-CN": "全力以赴",
        "zh-TW": "全力以赴",
        "en": "Maximum effort",
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
    # Account info
    "account.title": {
        "zh-CN": "账户",
        "zh-TW": "帳戶",
        "en": "Account",
    },
    "account.email": {
        "zh-CN": "邮箱",
        "zh-TW": "郵箱",
        "en": "Email",
    },
    "account.plan": {
        "zh-CN": "套餐",
        "zh-TW": "方案",
        "en": "Plan",
    },
    "account.org": {
        "zh-CN": "组织",
        "zh-TW": "組織",
        "en": "Org",
    },
    # Usage stats
    "cmd.quota": {
        "zh-CN": "查看用量统计",
        "zh-TW": "查看用量統計",
        "en": "View usage stats",
    },
    "quota.title": {
        "zh-CN": "用量统计",
        "zh-TW": "用量統計",
        "en": "Usage Stats",
    },
    "quota.real_title": {
        "zh-CN": "Claude Code 真实用量 (来自 stats-cache.json)",
        "zh-TW": "Claude Code 真實用量 (來自 stats-cache.json)",
        "en": "Claude Code Real Usage (from stats-cache.json)",
    },
    "quota.local_title": {
        "zh-CN": "本地会话统计",
        "zh-TW": "本地會話統計",
        "en": "Local Session Stats",
    },
    "quota.total_sessions": {
        "zh-CN": "总会话数",
        "zh-TW": "總會話數",
        "en": "Total Sessions",
    },
    "quota.total_messages": {
        "zh-CN": "总消息数",
        "zh-TW": "總消息數",
        "en": "Total Messages",
    },
    "quota.since": {
        "zh-CN": "使用起始",
        "zh-TW": "使用起始",
        "en": "Since",
    },
    "quota.session": {
        "zh-CN": "本次会话",
        "zh-TW": "本次會話",
        "en": "This Session",
    },
    "quota.today": {
        "zh-CN": "今日",
        "zh-TW": "今日",
        "en": "Today",
    },
    "quota.recent_days": {
        "zh-CN": "最近7天",
        "zh-TW": "最近7天",
        "en": "Last 7 Days",
    },
    "quota.date": {
        "zh-CN": "日期",
        "zh-TW": "日期",
        "en": "Date",
    },
    "quota.messages": {
        "zh-CN": "消息",
        "zh-TW": "消息",
        "en": "Messages",
    },
    "quota.sessions": {
        "zh-CN": "会话",
        "zh-TW": "會話",
        "en": "Sessions",
    },
    "quota.tool_calls": {
        "zh-CN": "工具调用",
        "zh-TW": "工具調用",
        "en": "Tool Calls",
    },
    "quota.model_usage": {
        "zh-CN": "模型用量",
        "zh-TW": "模型用量",
        "en": "Model Usage",
    },
    "quota.input": {
        "zh-CN": "输入",
        "zh-TW": "輸入",
        "en": "Input",
    },
    "quota.output": {
        "zh-CN": "输出",
        "zh-TW": "輸出",
        "en": "Output",
    },
    "quota.cache_read": {
        "zh-CN": "缓存读取",
        "zh-TW": "快取讀取",
        "en": "Cache Read",
    },
    "quota.cache_create": {
        "zh-CN": "缓存创建",
        "zh-TW": "快取建立",
        "en": "Cache Create",
    },
    "quota.requests": {
        "zh-CN": "次请求",
        "zh-TW": "次請求",
        "en": "requests",
    },
    "quota.no_real_data": {
        "zh-CN": "未检测到 Claude Code stats-cache.json，仅显示本地统计",
        "zh-TW": "未偵測到 Claude Code stats-cache.json，僅顯示本地統計",
        "en": "Claude Code stats-cache.json not found, showing local stats only",
    },
    "quota.no_today_data": {
        "zh-CN": "今日暂无数据",
        "zh-TW": "今日暫無數據",
        "en": "No data for today yet",
    },
    "quota.local_5h": {
        "zh-CN": "最近5小时 (本地)",
        "zh-TW": "最近5小時 (本地)",
        "en": "Last 5 Hours (local)",
    },
    "quota.local_today": {
        "zh-CN": "今日 (本地)",
        "zh-TW": "今日 (本地)",
        "en": "Today (local)",
    },
    "quota.enabled": {
        "zh-CN": "已开启用量提示",
        "zh-TW": "已開啟用量提示",
        "en": "Usage indicator enabled",
    },
    "quota.disabled": {
        "zh-CN": "已关闭用量提示",
        "zh-TW": "已關閉用量提示",
        "en": "Usage indicator disabled",
    },
    "quota.mini_label": {
        "zh-CN": "迷你提示",
        "zh-TW": "迷你提示",
        "en": "Mini indicator",
    },
    "quota.5h_window": {
        "zh-CN": "5小时窗口",
        "zh-TW": "5小時窗口",
        "en": "5-Hour Window",
    },
    "quota.weekly": {
        "zh-CN": "每周",
        "zh-TW": "每週",
        "en": "Weekly",
    },
    "quota.daily": {
        "zh-CN": "今日",
        "zh-TW": "今日",
        "en": "Today",
    },
    "quota.estimate_note": {
        "zh-CN": "用量为估算值，仅供参考",
        "zh-TW": "用量為估算值，僅供參考",
        "en": "Usage is estimated, for reference only",
    },
    "quota.resets_in": {
        "zh-CN": "重置",
        "zh-TW": "重置",
        "en": "Resets",
    },
    "quota.toggle_tip": {
        "zh-CN": "用 /额度 开 或 /额度 关 切换",
        "zh-TW": "用 /額度 開 或 /額度 關 切換",
        "en": "Use /quota on or /quota off to toggle",
    },
    "quota.on": {
        "zh-CN": "开",
        "zh-TW": "開",
        "en": "on",
    },
    "quota.off": {
        "zh-CN": "关",
        "zh-TW": "關",
        "en": "off",
    },
    # Permission modes
    "mode.safe": {
        "zh-CN": "安全模式",
        "zh-TW": "安全模式",
        "en": "Safe Mode",
    },
    "mode.auto": {
        "zh-CN": "自动模式",
        "zh-TW": "自動模式",
        "en": "Auto Mode",
    },
    "mode.safe_detail": {
        "zh-CN": "安全模式 (default)",
        "zh-TW": "安全模式 (default)",
        "en": "Safe Mode (default)",
    },
    "mode.auto_detail": {
        "zh-CN": "自动模式 (acceptEdits)",
        "zh-TW": "自動模式 (acceptEdits)",
        "en": "Auto Mode (acceptEdits)",
    },
    "mode.subscription": {
        "zh-CN": "订阅模式 (Claude Code)",
        "zh-TW": "訂閱模式 (Claude Code)",
        "en": "Subscription (Claude Code)",
    },
    "mode.subscription_plan": {
        "zh-CN": "订阅模式 ({plan})",
        "zh-TW": "訂閱模式 ({plan})",
        "en": "Subscription ({plan})",
    },
    "mode.api": {
        "zh-CN": "API 模式 (独立)",
        "zh-TW": "API 模式 (獨立)",
        "en": "API Mode (Standalone)",
    },
    "mode.not_initialized": {
        "zh-CN": "未初始化",
        "zh-TW": "未初始化",
        "en": "Not initialized",
    },
    "mode.label": {
        "zh-CN": "模式",
        "zh-TW": "模式",
        "en": "Mode",
    },
    # Banner tips
    "banner.tip": {
        "zh-CN": "提示: /自动 切换自动模式 | /安全 切换安全模式 | /切换 切换后端模式",
        "zh-TW": "提示: /自動 切換自動模式 | /安全 切換安全模式 | /切換 切換後端模式",
        "en": "Tip: /auto for auto mode | /safe for safe mode | /switch to toggle backend",
    },
    # History
    "history.cleared": {
        "zh-CN": "对话历史已清空",
        "zh-TW": "對話歷史已清空",
        "en": "History cleared",
    },
    "history.empty": {
        "zh-CN": "暂无历史",
        "zh-TW": "暫無歷史",
        "en": "No history yet",
    },
    # Model switching
    "model.available": {
        "zh-CN": "可用模型",
        "zh-TW": "可用模型",
        "en": "Available Models",
    },
    "model.current": {
        "zh-CN": "当前",
        "zh-TW": "當前",
        "en": "current",
    },
    "model.pick": {
        "zh-CN": "选择编号",
        "zh-TW": "選擇編號",
        "en": "Pick number",
    },
    "model.switched": {
        "zh-CN": "已切换到 {model}",
        "zh-TW": "已切換到 {model}",
        "en": "Switched to {model}",
    },
    "input.invalid": {
        "zh-CN": "无效选择",
        "zh-TW": "無效選擇",
        "en": "Invalid choice",
    },
    "input.invalid_arg": {
        "zh-CN": "无效参数: {arg}",
        "zh-TW": "無效參數: {arg}",
        "en": "Invalid argument: {arg}",
    },
    "input.invalid_number": {
        "zh-CN": "无效编号",
        "zh-TW": "無效編號",
        "en": "Invalid number",
    },
    "input.pick": {
        "zh-CN": "选择",
        "zh-TW": "選擇",
        "en": "Pick",
    },
    # Template
    "template.available": {
        "zh-CN": "预设模板",
        "zh-TW": "預設模板",
        "en": "Prompt Templates",
    },
    "template.clear": {
        "zh-CN": "清除模板",
        "zh-TW": "清除模板",
        "en": "Clear template",
    },
    "template.cleared": {
        "zh-CN": "已清除系统模板",
        "zh-TW": "已清除系統模板",
        "en": "System template cleared",
    },
    "template.enabled": {
        "zh-CN": "已启用模板: {name}",
        "zh-TW": "已啟用模板: {name}",
        "en": "Template enabled: {name}",
    },
    # Tools
    "tools.available": {
        "zh-CN": "可用工具",
        "zh-TW": "可用工具",
        "en": "Available Tools",
    },
    "tools.name": {
        "zh-CN": "工具名称",
        "zh-TW": "工具名稱",
        "en": "Tool Name",
    },
    "tools.desc": {
        "zh-CN": "说明",
        "zh-TW": "說明",
        "en": "Description",
    },
    "tools.backend": {
        "zh-CN": "当前后端",
        "zh-TW": "當前後端",
        "en": "Current backend",
    },
    # Auto/Safe mode switching
    "mode.switched_auto": {
        "zh-CN": "已切换到自动模式 — AI 可自动执行编辑和命令操作",
        "zh-TW": "已切換到自動模式 — AI 可自動執行編輯和命令操作",
        "en": "Switched to Auto Mode — AI can auto-execute edits and commands",
    },
    "mode.switched_safe": {
        "zh-CN": "已切换到安全模式 — 危险操作前需要确认",
        "zh-TW": "已切換到安全模式 — 危險操作前需要確認",
        "en": "Switched to Safe Mode — Confirmation required for dangerous operations",
    },
    # Skills table headers
    "skills.status": {
        "zh-CN": "状态",
        "zh-TW": "狀態",
        "en": "Status",
    },
    "skills.skill": {
        "zh-CN": "技能",
        "zh-TW": "技能",
        "en": "Skill",
    },
    "skills.description": {
        "zh-CN": "说明",
        "zh-TW": "說明",
        "en": "Description",
    },
    "skills.none_enabled": {
        "zh-CN": "未启用任何技能",
        "zh-TW": "未啟用任何技能",
        "en": "No skills enabled",
    },
    # Thinking/Effort backend errors
    "backend.no_thinking": {
        "zh-CN": "当前后端不支持思考模式控制",
        "zh-TW": "當前後端不支持思考模式控制",
        "en": "Current backend does not support thinking mode",
    },
    "backend.no_effort": {
        "zh-CN": "当前后端不支持推理强度控制",
        "zh-TW": "當前後端不支持推理強度控制",
        "en": "Current backend does not support effort control",
    },
    "backend.not_initialized": {
        "zh-CN": "后端未初始化",
        "zh-TW": "後端未初始化",
        "en": "Backend not initialized",
    },
    "backend.not_initialized_restart": {
        "zh-CN": "后端未初始化，请重启程序",
        "zh-TW": "後端未初始化，請重啟程序",
        "en": "Backend not initialized, please restart",
    },
    # Switch mode
    "switch.no_api_key": {
        "zh-CN": "无法切换到 API 模式 — 未找到 API Key",
        "zh-TW": "無法切換到 API 模式 — 未找到 API Key",
        "en": "Cannot switch to API mode — no API key found",
    },
    "switch.api_key_hint": {
        "zh-CN": "请设置 ANTHROPIC_API_KEY 环境变量或在配置中提供 api_key",
        "zh-TW": "請設置 ANTHROPIC_API_KEY 環境變量或在配置中提供 api_key",
        "en": "Please set ANTHROPIC_API_KEY env var or provide api_key in config",
    },
    "switch.no_cli": {
        "zh-CN": "无法切换到订阅模式 — 未安装 Claude CLI",
        "zh-TW": "無法切換到訂閱模式 — 未安裝 Claude CLI",
        "en": "Cannot switch to subscription mode — Claude CLI not installed",
    },
    "switch.not_supported": {
        "zh-CN": "当前后端不支持切换",
        "zh-TW": "當前後端不支持切換",
        "en": "Current backend does not support switching",
    },
    "switch.switched": {
        "zh-CN": "已从 {from_mode} 切换到 {to_mode}",
        "zh-TW": "已從 {from_mode} 切換到 {to_mode}",
        "en": "Switched from {from_mode} to {to_mode}",
    },
    # Audit
    "audit.time": {
        "zh-CN": "时间",
        "zh-TW": "時間",
        "en": "Time",
    },
    "audit.tool": {
        "zh-CN": "工具",
        "zh-TW": "工具",
        "en": "Tool",
    },
    "audit.action": {
        "zh-CN": "操作",
        "zh-TW": "操作",
        "en": "Action",
    },
    "audit.status": {
        "zh-CN": "状态",
        "zh-TW": "狀態",
        "en": "Status",
    },
    "audit.log_path": {
        "zh-CN": "日志路径",
        "zh-TW": "日誌路徑",
        "en": "Log path",
    },
    "audit.count": {
        "zh-CN": "共 {count} 条记录 (最近)",
        "zh-TW": "共 {count} 條記錄 (最近)",
        "en": "{count} entries (recent)",
    },
    # Sessions
    "sessions.no_title": {
        "zh-CN": "(无标题)",
        "zh-TW": "(無標題)",
        "en": "(untitled)",
    },
    "sessions.continue_tip": {
        "zh-CN": "输入你的下一条消息继续对话",
        "zh-TW": "輸入你的下一條消息繼續對話",
        "en": "Enter your next message to continue",
    },
    # Undo
    "undo.sdk_only": {
        "zh-CN": "撤销仅在 SDK 模式下可用",
        "zh-TW": "撤銷僅在 SDK 模式下可用",
        "en": "Undo is only available in SDK mode",
    },
    "undo.restored": {
        "zh-CN": "恢复",
        "zh-TW": "恢復",
        "en": "restore",
    },
    "undo.removed": {
        "zh-CN": "删除",
        "zh-TW": "刪除",
        "en": "delete",
    },
    "undo.success": {
        "zh-CN": "已撤销到检查点: {id}",
        "zh-TW": "已撤銷到檢查點: {id}",
        "en": "Undone to checkpoint: {id}",
    },
    "undo.failed": {
        "zh-CN": "撤销失败: {error}",
        "zh-TW": "撤銷失敗: {error}",
        "en": "Undo failed: {error}",
    },
    "checkpoints.sdk_only": {
        "zh-CN": "检查点仅在 SDK 模式下可用",
        "zh-TW": "檢查點僅在 SDK 模式下可用",
        "en": "Checkpoints are only available in SDK mode",
    },
    # Notes
    "notes.title": {
        "zh-CN": "快速笔记",
        "zh-TW": "快速筆記",
        "en": "Quick Notes",
    },
    "notes.add": {
        "zh-CN": "添加笔记",
        "zh-TW": "添加筆記",
        "en": "Add note",
    },
    "notes.recent": {
        "zh-CN": "查看近期笔记",
        "zh-TW": "查看近期筆記",
        "en": "View recent notes",
    },
    "notes.search": {
        "zh-CN": "搜索笔记",
        "zh-TW": "搜索筆記",
        "en": "Search notes",
    },
    "notes.back": {
        "zh-CN": "返回",
        "zh-TW": "返回",
        "en": "Back",
    },
    "notes.content_prompt": {
        "zh-CN": "笔记内容",
        "zh-TW": "筆記內容",
        "en": "Note content",
    },
    "notes.empty_cancelled": {
        "zh-CN": "内容为空，已取消",
        "zh-TW": "內容為空，已取消",
        "en": "Empty content, cancelled",
    },
    "notes.keyword_prompt": {
        "zh-CN": "搜索关键词",
        "zh-TW": "搜索關鍵詞",
        "en": "Search keyword",
    },
    "notes.keyword_empty": {
        "zh-CN": "关键词为空，已取消",
        "zh-TW": "關鍵詞為空，已取消",
        "en": "Empty keyword, cancelled",
    },
    # Help command descriptions — history
    "cmd.history": {
        "zh-CN": "查看最近对话历史",
        "zh-TW": "查看最近對話歷史",
        "en": "View recent conversation history",
    },
    # Help category headers
    "help.cat.core": {
        "zh-CN": "核心",
        "zh-TW": "核心",
        "en": "Core",
    },
    "help.cat.ai_control": {
        "zh-CN": "AI 控制",
        "zh-TW": "AI 控制",
        "en": "AI Control",
    },
    "help.cat.safety_history": {
        "zh-CN": "安全与历史",
        "zh-TW": "安全與歷史",
        "en": "Safety & History",
    },
    "help.cat.mode_display": {
        "zh-CN": "模式与显示",
        "zh-TW": "模式與顯示",
        "en": "Mode & Display",
    },
    "help.cat.shortcuts": {
        "zh-CN": "快捷键",
        "zh-TW": "快捷鍵",
        "en": "Shortcuts",
    },
    # Help command descriptions (for hardcoded ones)
    "cmd.auto_mode": {
        "zh-CN": "自动模式 — AI 可自动执行编辑操作",
        "zh-TW": "自動模式 — AI 可自動執行編輯操作",
        "en": "Auto mode — AI can auto-execute edit operations",
    },
    "cmd.safe_mode": {
        "zh-CN": "安全模式 — 危险操作前需确认（默认）",
        "zh-TW": "安全模式 — 危險操作前需確認（默認）",
        "en": "Safe mode — Confirmation required (default)",
    },
    "cmd.switch_mode": {
        "zh-CN": "切换后端模式 (订阅/API)",
        "zh-TW": "切換後端模式 (訂閱/API)",
        "en": "Switch backend mode (subscription/API)",
    },
    "cmd.notes": {
        "zh-CN": "快速笔记 — 添加/查看/搜索笔记",
        "zh-TW": "快速筆記 — 添加/查看/搜索筆記",
        "en": "Quick notes — add/view/search notes",
    },
    # Chat events
    "chat.tool_call": {
        "zh-CN": "调用工具",
        "zh-TW": "調用工具",
        "en": "Tool call",
    },
    "chat.tool_result": {
        "zh-CN": "工具结果",
        "zh-TW": "工具結果",
        "en": "Tool result",
    },
    "chat.usage": {
        "zh-CN": "用量: 输入 {input} / 输出 {output} tokens",
        "zh-TW": "用量: 輸入 {input} / 輸出 {output} tokens",
        "en": "Usage: input {input} / output {output} tokens",
    },
    "chat.interrupted": {
        "zh-CN": "已中断生成",
        "zh-TW": "已中斷生成",
        "en": "Generation interrupted",
    },
    "chat.error": {
        "zh-CN": "错误: {error}",
        "zh-TW": "錯誤: {error}",
        "en": "Error: {error}",
    },
    # Unknown command
    "cmd.unknown": {
        "zh-CN": "未知命令，输入 /帮助 查看可用命令",
        "zh-TW": "未知命令，輸入 /幫助 查看可用命令",
        "en": "Unknown command. Type /help for available commands",
    },
    # Ctrl+C hint
    "ctrl_c.hint": {
        "zh-CN": "再按一次 Ctrl+C 退出",
        "zh-TW": "再按一次 Ctrl+C 退出",
        "en": "Press Ctrl+C again to exit",
    },
    # Shortcuts
    "shortcuts.title": {
        "zh-CN": "快捷键",
        "zh-TW": "快捷鍵",
        "en": "Shortcuts",
    },
    "shortcuts.cancel": {
        "zh-CN": "取消当前请求",
        "zh-TW": "取消當前請求",
        "en": "Cancel request",
    },
    "shortcuts.exit": {
        "zh-CN": "退出",
        "zh-TW": "退出",
        "en": "Exit",
    },
    "shortcuts.exit_now": {
        "zh-CN": "立即退出",
        "zh-TW": "立即退出",
        "en": "Exit now",
    },
    # Guide
    "guide.commands": {
        "zh-CN": "常用命令",
        "zh-TW": "常用命令",
        "en": "Commands",
    },
    "guide.help": {
        "zh-CN": "所有命令",
        "zh-TW": "所有命令",
        "en": "All commands",
    },
    "guide.skills": {
        "zh-CN": "AI 技能",
        "zh-TW": "AI 技能",
        "en": "AI skills",
    },
    "guide.undo": {
        "zh-CN": "撤销修改",
        "zh-TW": "撤銷修改",
        "en": "Undo changes",
    },
    "guide.lang": {
        "zh-CN": "切换语言",
        "zh-TW": "切換語言",
        "en": "Language",
    },
    "guide.think": {
        "zh-CN": "思考深度",
        "zh-TW": "思考深度",
        "en": "Thinking depth",
    },
    "guide.quota": {
        "zh-CN": "用量统计",
        "zh-TW": "用量統計",
        "en": "Usage stats",
    },
    "guide.model": {
        "zh-CN": "切换模型",
        "zh-TW": "切換模型",
        "en": "Switch model",
    },
    "guide.effort": {
        "zh-CN": "推理强度",
        "zh-TW": "推理強度",
        "en": "Effort level",
    },
    "guide.exit": {
        "zh-CN": "退出",
        "zh-TW": "退出",
        "en": "Exit",
    },
    # Command guide categories
    "guide.cat_core": {
        "zh-CN": "核心",
        "zh-TW": "核心",
        "en": "Core",
    },
    "guide.cat_ai": {
        "zh-CN": "AI 控制",
        "zh-TW": "AI 控制",
        "en": "AI Control",
    },
    "guide.cat_safety": {
        "zh-CN": "安全与历史",
        "zh-TW": "安全與歷史",
        "en": "Safety & History",
    },
    "guide.cat_mode": {
        "zh-CN": "模式与显示",
        "zh-TW": "模式與顯示",
        "en": "Mode & Display",
    },
    "guide.cat_shortcuts": {
        "zh-CN": "快捷键",
        "zh-TW": "快捷鍵",
        "en": "Shortcuts",
    },
    "guide.switch": {
        "zh-CN": "切换后端",
        "zh-TW": "切換後端",
        "en": "Toggle backend",
    },
    "guide.auto": {
        "zh-CN": "自动模式",
        "zh-TW": "自動模式",
        "en": "Auto mode",
    },
    "guide.safe": {
        "zh-CN": "安全模式",
        "zh-TW": "安全模式",
        "en": "Safe mode",
    },
    "guide.quota_toggle": {
        "zh-CN": "显示开关",
        "zh-TW": "顯示開關",
        "en": "Toggle display",
    },
    "guide.notes": {
        "zh-CN": "快速笔记",
        "zh-TW": "快速筆記",
        "en": "Quick notes",
    },
    "guide.template": {
        "zh-CN": "预设模板",
        "zh-TW": "預設模板",
        "en": "Preset templates",
    },
    "guide.tools": {
        "zh-CN": "工具列表",
        "zh-TW": "工具列表",
        "en": "List tools",
    },
    "guide.settings": {
        "zh-CN": "查看配置",
        "zh-TW": "查看配置",
        "en": "View config",
    },
    "guide.clear": {
        "zh-CN": "清空历史",
        "zh-TW": "清空歷史",
        "en": "Clear history",
    },
    "guide.checkpoints": {
        "zh-CN": "查看检查点",
        "zh-TW": "查看檢查點",
        "en": "View checkpoints",
    },
    "guide.resume": {
        "zh-CN": "恢复会话",
        "zh-TW": "恢復會話",
        "en": "Resume session",
    },
    "guide.fork": {
        "zh-CN": "分支会话",
        "zh-TW": "分支會話",
        "en": "Fork session",
    },
    "guide.sessions": {
        "zh-CN": "浏览会话",
        "zh-TW": "瀏覽會話",
        "en": "Browse sessions",
    },
    "guide.audit": {
        "zh-CN": "操作日志",
        "zh-TW": "操作日誌",
        "en": "Operation log",
    },
    "guide.think_deep": {
        "zh-CN": "深度推理",
        "zh-TW": "深度推理",
        "en": "Deep reasoning",
    },
    "guide.think_off": {
        "zh-CN": "快速回答",
        "zh-TW": "快速回答",
        "en": "Quick answers",
    },
    "guide.effort_max": {
        "zh-CN": "最大强度",
        "zh-TW": "最大強度",
        "en": "Max effort",
    },
    "guide.effort_low": {
        "zh-CN": "速度模式",
        "zh-TW": "速度模式",
        "en": "Speed mode",
    },
    "guide.cancel": {
        "zh-CN": "取消请求",
        "zh-TW": "取消請求",
        "en": "Cancel request",
    },
    "guide.exit_2x": {
        "zh-CN": "退出 (2秒内)",
        "zh-TW": "退出 (2秒內)",
        "en": "Exit (2s)",
    },
    "guide.exit_now": {
        "zh-CN": "立即退出",
        "zh-TW": "立即退出",
        "en": "Exit immediately",
    },
    "guide.help_hint": {
        "zh-CN": "输入 /帮助 查看全部命令",
        "zh-TW": "輸入 /幫助 查看全部命令",
        "en": "Type /help for all commands",
    },
    # Menu navigation
    "menu.back": {
        "zh-CN": "返回",
        "zh-TW": "返回",
        "en": "Back",
    },
    "menu.choose": {
        "zh-CN": "选择编号 (0 返回): ",
        "zh-TW": "選擇編號 (0 返回): ",
        "en": "Choose (0 to go back): ",
    },
    "skills.skip_remaining": {
        "zh-CN": "跳过剩余技能",
        "zh-TW": "跳過剩餘技能",
        "en": "Skip remaining",
    },
    # System prompt
    "system_prompt.default": {
        "zh-CN": "你是 AI 编程助手，一个全中文的智能编程终端工具。\n- 始终用中文回答用户\n- 可以读取、编辑、创建文件\n- 可以执行命令和分析项目\n- 代码注释用中文\n- 遇到不确定的操作先询问用户确认",
        "zh-TW": "你是 AI 編程助手，一個全中文的智慧編程終端工具。\n- 始終用中文回答用戶\n- 可以讀取、編輯、創建文件\n- 可以執行命令和分析項目\n- 代碼注釋用中文\n- 遇到不確定的操作先詢問用戶確認",
        "en": "You are an AI coding assistant, an intelligent programming terminal tool.\n- Respond in clear, concise English\n- Can read, edit, and create files\n- Can execute commands and analyze projects\n- Write code comments in English\n- Ask for confirmation before uncertain operations",
    },
}

_current_locale: str | None = None


def get_locale() -> str:
    """Detect or return the current locale.

    Resolution order:
      1. Cached value (set by set_locale or set_locale_from_config)
      2. CLAUDEZH_LANG env var
      3. Config file ``language`` setting (if not "auto")
      4. System locale detection
      5. Default: en (for international servers)
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

    if "zh_CN" in sys_locale or "zh_SG" in sys_locale:
        _current_locale = "zh-CN"
    elif "zh_TW" in sys_locale or "zh_HK" in sys_locale:
        _current_locale = "zh-TW"
    else:
        # Default to English for non-Chinese locales (including bare "C" or "en_*")
        _current_locale = "en"

    return _current_locale


def set_locale(loc: str):
    """Override the current locale."""
    global _current_locale
    if loc in ("zh-CN", "zh-TW", "en"):
        _current_locale = loc


def set_locale_from_config(config: dict):
    """Set locale from a loaded config dict.

    Called early in CLI startup so that the config ``language`` setting
    takes effect before any ``t()`` calls.  If the config value is
    ``"auto"`` (or missing), this is a no-op and normal detection
    proceeds.
    """
    lang = config.get("language", "auto")
    if lang and lang != "auto":
        set_locale(lang)


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
