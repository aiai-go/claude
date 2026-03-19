# Contributing to claudezh / 贡献指南

Thank you for your interest in contributing to claudezh! This guide will help you get started.

感谢你对 claudezh 项目的关注！本指南将帮助你快速上手参与贡献。

---

## Development Setup / 开发环境搭建

### Prerequisites / 前置条件

- Python >= 3.10
- Node.js >= 16 (for npm packaging)
- Git

### Setup Steps / 搭建步骤

```bash
# 1. Fork and clone / Fork 并克隆仓库
git clone https://github.com/<your-username>/claudezh.git
cd claudezh

# 2. Install in development mode / 以开发模式安装
pip install -e .

# 3. Verify installation / 验证安装
claudezh --help

# 4. (Optional) Install Claude Code for SDK backend testing
# （可选）安装 Claude Code 以测试订阅模式后端
npm install -g @anthropic-ai/claude-code
```

---

## Code Style Guidelines / 代码风格规范

- **Python**: Follow PEP 8. Use type hints where possible.
- **Naming**: Use `snake_case` for functions/variables, `PascalCase` for classes.
- **Docstrings**: Write docstrings in English. Inline comments may be in Chinese or English.
- **Imports**: Group by stdlib, third-party, local. Use absolute imports.
- **i18n**: All user-facing strings must go through the i18n system (`i18n.t()`). Never hardcode UI text.

**Python 规范**: 遵循 PEP 8，尽量使用类型注解。函数/变量用 `snake_case`，类名用 `PascalCase`。所有面向用户的字符串必须通过 i18n 系统（`i18n.t()`），不要硬编码界面文本。

---

## How to Submit a Pull Request / 如何提交 PR

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or: git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**. Keep commits focused and atomic.

3. **Test your changes** locally:
   ```bash
   # Run the CLI to verify
   claudezh

   # Run tests if available
   python -m pytest tests/ -v
   ```

4. **Commit with a clear message**:
   ```bash
   git commit -m "feat: add Japanese locale support"
   # Prefixes: feat, fix, docs, refactor, test, chore
   ```

5. **Push and create a PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub with:
   - A clear title (under 70 characters)
   - A description of what changed and why
   - Screenshots if UI-related

**提交步骤**: 从 `main` 创建分支 -> 开发 -> 本地测试 -> 用清晰的 commit message 提交 -> 推送并在 GitHub 创建 PR。Commit 前缀使用 `feat` / `fix` / `docs` / `refactor` / `test` / `chore`。

---

## How to Report Bugs / 如何报告 Bug

Use the [Bug Report template](https://github.com/whaleaicode/claudezh/issues/new?template=bug_report.md) on GitHub Issues.

请使用 GitHub Issues 的 [Bug 报告模板](https://github.com/whaleaicode/claudezh/issues/new?template=bug_report.md) 提交 bug。

Please include:
- Your OS and Python/Node.js version
- The command or action that triggered the bug
- Expected vs actual behavior
- Error messages or screenshots

请包含：操作系统、Python/Node.js 版本、触发 bug 的操作、预期行为 vs 实际行为、错误信息或截图。

---

## Areas Needing Help / 需要帮助的方向

| Area / 方向 | Description / 说明 | Difficulty / 难度 |
|:---|:---|:---:|
| Translations / 翻译 | Add or improve zh-TW, en, ja, ko locales | Beginner / 入门 |
| Templates / 模板 | Add new preset prompt templates | Beginner / 入门 |
| Documentation / 文档 | Tutorials, usage guides, API docs | Beginner / 入门 |
| Testing / 测试 | Unit tests, integration tests, CI/CD | Beginner / 入门 |
| Plugin System / 插件系统 | Design extensible plugin architecture | Intermediate / 进阶 |
| VS Code Extension | Build a VS Code sidebar integration | Intermediate / 进阶 |
| Multi-model Backend / 多模型 | Support OpenAI, Gemini, local models | Intermediate / 进阶 |
| Performance / 性能 | Streaming optimization, token compression | Intermediate / 进阶 |

Look for issues labeled [`good first issue`](https://github.com/whaleaicode/claudezh/labels/good%20first%20issue) to get started.

入门贡献者可以查看带有 [`good first issue`](https://github.com/whaleaicode/claudezh/labels/good%20first%20issue) 标签的 Issue。

---

## Code of Conduct / 行为准则

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

参与贡献前请阅读我们的[行为准则](CODE_OF_CONDUCT.md)。

---

Thank you for helping make AI coding more accessible to Chinese developers!

感谢你帮助让 AI 编程对中文开发者更加友好！
