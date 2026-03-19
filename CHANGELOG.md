# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-03-19

### Added
- 🎯 **Skills System**: 10 built-in AI personas across 4 categories (Web Dev, DevOps, Data/AI, Tools)
- ↩️ **File Checkpointing**: `/undo` command with automatic backup and restore
- 🛡️ **Safety Hooks**: 13 dangerous command patterns blocked, full audit logging
- 📋 **Session Resume**: `/resume` to continue past conversations, `/fork` to branch off
- 🧠 **Thinking Control**: `/think deep` for complex problems, `/think off` for quick answers
- 💪 **Effort Levels**: `/effort max` for thorough analysis, `/effort low` for speed
- 🔧 **12 Custom MCP Tools**: Project memory, code stats, dependency check, git enhanced, environment detection, quick notes
- 📝 **Quick Notes**: `/notes` for persistent project notes
- 🔍 **Audit Log**: `/audit` to review all AI operations
- 🔄 **Mode Switching**: `/switch` to toggle SDK/API backends

### Changed
- Dual-mode backend: auto-detects Claude Code (free) or falls back to API mode
- Welcome banner shows active mode, skills, thinking level

## [0.1.0] - 2026-03-19

### Added
- Initial release
- Full Chinese CLI interface (Simplified/Traditional/English)
- Claude Agent SDK integration (subscription mode)
- Anthropic API integration (standalone mode)
- 7 preset templates (code gen, review, bug fix, refactor, test, explain, translate)
- 12 slash commands with Chinese + English aliases
- Rich terminal UI with streaming responses
- Conversation history with persistence
- Token usage tracking
- Configuration management (~/.claudezh/)
- npm package with auto Python dependency installation
