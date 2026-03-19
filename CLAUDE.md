# @aiai-go/claude — Project Handbook

## Project Identity
- **Product**: @aiai-go/claude — Multilingual AI Coding CLI
- **npm**: `@aiai-go/claude` (org: `@aiai-go`, account: `aiaigo`)
- **GitHub**: https://github.com/aiai-go/claude
- **Website**: https://aiaigo.org
- **Telegram**: https://t.me/aiai_go
- **Email**: hi@aiaigo.org
- **License**: MIT
- **Author**: Claudechinese (GitHub: whaleaicode)
- **Git author**: `Claudechinese <239421346+whaleaicode@users.noreply.github.com>`

## Brand Rules
- Product name: `@aiai-go/claude` (NOT claudezh, except as CLI command name)
- Ecosystem: `aiai-go` (claude/gemini/gpt/codex)
- CLI commands: `aiai-claude` (primary), `claudezh` (alias)
- Config directory: `~/.claudezh/`
- Python package: `aicodezh` (internal, don't rename)

## Tech Stack
- **Python 3.10+**: Core logic (aicodezh/ package)
- **Node.js 16+**: npm wrapper (bin/claudezh-wrapper.js)
- **claude-agent-sdk**: SDK mode (subscription, free)
- **anthropic SDK**: API mode (standalone, paid)
- **Rich**: Terminal UI
- **No database, no external services** (all local files)

## Architecture

```
CLI Layer (cli.py)
├── Commands (20+ slash commands, Chinese + English aliases)
├── Banner (print_banner, modern Rich UI)
├── REPL loop (input → dispatch → chat)
└── i18n (i18n.py, 290+ keys, zh-CN/zh-TW/en)

Backend Layer (backend.py)
├── SDKBackend (claude-agent-sdk → Claude CLI process)
│   ├── Persistent connection (ClaudeSDKClient)
│   ├── Built-in tools: Read, Edit, Write, Bash, Glob, Grep
│   └── get_account_info() via get_server_info()
├── APIBackend (anthropic SDK → direct API)
│   └── Custom tools from tools.py
└── detect_backend() auto-selects best available

Feature Modules:
├── skills.py — 10 AI personas, 4 categories
├── hooks.py — 13 safety rules, audit logging
├── checkpoint.py — file undo/rollback
├── mcp_tools.py — 12 custom MCP tools
├── quota.py — real Claude usage API + local tracking
├── agent.py — ChineseAgent wrapper, preset agents
├── tools.py — 8 file/code tools (API mode)
├── templates.py — 7 preset prompts
├── history.py — conversation persistence
└── config.py — ~/.claudezh/config.json

Plugin Layer (plugin/)
├── DXT manifest (manifest.json)
├── MCP server (server.py, 12 tools standalone)
└── Commands (7 Chinese slash commands for Claude Code)
```

## File Map
```
aicodezh/
├── __init__.py      — Package exports
├── __main__.py      — python -m aicodezh entry
├── cli.py           — Main CLI (REPL, commands, banner) ~1200 lines
├── backend.py       — Dual backend abstraction ~800 lines
├── agent.py         — SDK wrapper, ChineseAgent class
├── skills.py        — 10 skill personas with system prompts
├── hooks.py         — Safety hooks (PreToolUse, PostToolUse, etc.)
├── checkpoint.py    — File checkpointing for undo
├── mcp_tools.py     — 12 custom MCP tools
├── quota.py         — Usage tracking (real API + local)
├── tools.py         — File/code tools for API mode
├── templates.py     — 7 preset prompt templates
├── history.py       — Conversation history management
├── config.py        — Config load/save (~/.claudezh/)
├── i18n.py          — 290+ translation keys (zh-CN/zh-TW/en)
└── version.py       — VERSION, APP_NAME, BRAND_NAME

bin/
├── claudezh           — Shell entry point
└── claudezh-wrapper.js — Node.js wrapper for npm

scripts/
└── postinstall.js     — npm postinstall (pip dependencies)

.github/
├── FUNDING.yml
├── PULL_REQUEST_TEMPLATE.md
└── ISSUE_TEMPLATE/
    ├── bug_report.md
    └── feature_request.md

plugin/
├── manifest.json      — DXT plugin manifest
├── server.py          — Standalone MCP server (12 tools)
├── README.md          — Plugin documentation
└── commands/
    ├── zh.md          — /zh 简体中文
    ├── zht.md         — /zht 繁体中文
    ├── en.md          — /en English
    ├── review-zh.md   — /review-zh 中文审查
    ├── explain-zh.md  — /explain-zh 中文解释
    ├── test-zh.md     — /test-zh 中文测试
    └── fix-zh.md      — /fix-zh 中文修复

assets/
└── demo.svg           — Terminal screenshot for README

docs/
└── COMMUNITY_GUIDE.md — Community management handbook
```

## Development Commands
```bash
# Install for development
pip install -e . --break-system-packages

# Run
env CLAUDECODE= claudezh

# Test imports
python3 -c "from aicodezh.cli import run; print('OK')"

# Check all modules
python3 -c "
from aicodezh import VERSION
from aicodezh.skills import SKILLS
from aicodezh.tools import list_tools
from aicodezh.hooks import DANGEROUS_PATTERNS
print(f'v{VERSION} | {len(SKILLS)} skills | {len(list_tools())} tools')
"

# npm pack test
npm pack --dry-run
```

## Git Rules
- Author: `Claudechinese <239421346+whaleaicode@users.noreply.github.com>`
- Always use this author for commits
- Keep commits clean and descriptive
- Squash before release (single commit per version)

## i18n Rules
- Every user-facing string MUST go through `t()` function
- Every key needs 3 locales: zh-CN, zh-TW, en
- Chinese skill/template system prompts are intentionally Chinese (domain expertise)
- CLI command aliases (e.g., /帮助) stay as-is
- Default locale: `en` for non-Chinese systems

## Safety Rules
- NEVER modify ~/.claude/ directory
- NEVER delete user files without confirmation
- NEVER store user credentials in our files
- Credentials are READ-ONLY
- All API calls must have try/except with graceful fallback
- Dangerous commands blocked by hooks.py (13 patterns)

## No E-commerce Content
- No Amazon, Shopify, or e-commerce references anywhere
- Skills are: Web Dev, DevOps, Data/AI, Tools only
- This was a deliberate decision — keep it general purpose

## Handling PRs
When reviewing a PR:
1. Check brand consistency (@aiai-go/claude, not claudezh)
2. Check i18n (all strings through t(), all 3 locales)
3. Check no hardcoded Chinese in non-skill code
4. Check safety (no credential modifications, no dangerous defaults)
5. Check modern Rich colors (bright_blue labels, bright_cyan values, dim blue borders)
6. Run import test after merge

## Handling Issues
- Bug reports: reproduce, fix, add i18n if new strings
- Feature requests: evaluate, discuss in Telegram, implement if aligned
- Language contributions: guide contributor to i18n.py, review translations
- Label issues appropriately (skill, mcp-tool, i18n, etc.)

## Community Responses
Tone: professional, welcoming, grateful. Examples:
- "Thanks for the report! I can reproduce this. Fix coming in the next release."
- "Great idea! This aligns well with our roadmap. Would you like to submit a PR?"
- "Welcome! Your first contribution is merged. Thank you for making AI coding more accessible."

## Release Process
1. Update version in: version.py, package.json, pyproject.toml
2. Update CHANGELOG.md
3. Squash commits: `git checkout --orphan release && git add -A && git commit ...`
4. Force push: `git push --force origin main`
5. Create GitHub release: `gh release create vX.Y.Z ...`
6. Publish npm: `npm publish --access public`
7. Announce on Telegram + Twitter

## Product Line
- @aiai-go/claude (npm) — Full-featured enhanced CLI (this repo)
- claudezh (npm) — Lightweight Chinese-only CLI (separate repo: aiai-go/claudezh)
- DXT Plugin (plugin/) — Claude Code plugin (7 commands + 12 MCP tools)

## npm Accounts & Packages (13 packages)
- Org: `@aiai-go` (npm account: aiaigo)
- Published: @aiai-go/claude (v0.2.0), @aiai-go/gemini, @aiai-go/gpt, @aiai-go/codex (placeholders)
- Also: claudezh (lightweight Chinese CLI, aiaigo account), mygemini (aiaigo account)

## Stats
- 48 files, 11,331 lines

## Key Decisions Log
- 2026-03-19: Rebranded from claudezh to @aiai-go/claude
- 2026-03-19: Removed e-commerce skills (Amazon/Shopify)
- 2026-03-19: Switched to persistent ClaudeSDKClient connection
- 2026-03-19: Real Claude usage API via ~/.claude/.credentials.json
- 2026-03-19: All community files in pure English (except README.zh-CN.md)
- 2026-03-19: Added DXT plugin (manifest.json + MCP server + 7 commands)
- 2026-03-19: Created claudezh-lite (separate lightweight product)
- 2026-03-19: Integrated real Claude usage API via ~/.claude/.credentials.json
- 2026-03-19: Switched to persistent ClaudeSDKClient connection
- 2026-03-19: All interactive menus have 0-to-go-back option
