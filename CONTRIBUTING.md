# Contributing to @aiai-go/claude

> **Every contribution makes AI coding more accessible to Chinese developers worldwide!**

We're thrilled that you're interested in contributing to @aiai-go/claude! Whether you're fixing a typo, adding a translation, or building an entire VS Code extension — **your contribution matters**, and we're here to help you succeed.

---

## Why Contribute?

- **You're shaping the future** — @aiai-go/claude is the first Chinese-native AI coding CLI. Your code directly impacts how millions of Chinese-speaking developers interact with AI.
- **Learn Claude Agent SDK internals** — contributing here is one of the best ways to deeply understand how Claude's agent architecture works under the hood.
- **Build your portfolio** — open-source contributions to a growing AI project look great and teach real-world skills.
- **ALL skill levels welcome** — from typo fixes to architectural redesigns, every PR is celebrated.
- **Bilingual community** — practice your English or Chinese in a supportive, international environment.

---

## Quick Start

Get up and running in under 5 minutes:

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/<your-username>/claude.git
cd claude

# 2. Install in development mode (editable)
pip install -e .

# 3. Verify it works
claudezh --help

# 4. Create your feature branch
git checkout -b feature/my-awesome-change

# 5. (Optional) Install Claude Code for SDK backend testing
npm install -g @anthropic-ai/claude-code
```

That's it! You're ready to start coding.

---

## What We Need Help With

### Good First Issues (beginner-friendly)

Perfect for your first contribution. No deep knowledge of the codebase required!

- **Add i18n translations** — help us support zh-TW, en, ja, ko locales
- **Write unit tests** — increase test coverage for existing modules
- **Improve error messages** — make errors more helpful and user-friendly
- **Fix typos in docs** — spot a typo? Fix it! Even one-character PRs are welcome
- **Add preset templates** — create new prompt templates for common tasks

### Medium Difficulty

Some familiarity with the codebase helps, but we'll guide you through reviews.

- **New skill personas** — create specialized personas (security expert, mobile dev, data engineer, etc.)
- **New MCP tools** — Docker management, API testing, database helpers, and more
- **Terminal UI improvements** — enhance the CLI experience with the `textual` library
- **Better streaming** — optimize token streaming and response rendering
- **Plugin system design** — help architect an extensible plugin framework

### Advanced

For experienced contributors who want to take on bigger challenges.

- **VS Code extension** — build a sidebar integration for @aiai-go/claude in VS Code
- **Vim/Neovim plugin** — bring @aiai-go/claude to the terminal editor ecosystem
- **Web dashboard** — create a browser-based interface for @aiai-go/claude
- **Plugin marketplace** — design and build a plugin discovery/install system
- **Multi-language support** — expand beyond Chinese to Japanese, Korean, and more
- **Multi-model backends** — add support for OpenAI, Gemini, local models

Look for issues labeled [`good first issue`](https://github.com/aiai-go/claude/labels/good%20first%20issue) to get started!

---

## Development Setup

### Prerequisites

| Requirement | Minimum Version |
|:---|:---|
| Python | >= 3.10 |
| Node.js | >= 16 (for npm packaging) |
| Git | any recent version |

### Project Structure

```
aicodezh/
├── aicodezh/           # Main package
│   ├── cli.py          # CLI entry point
│   ├── i18n/           # Translations
│   ├── skills/         # Skill modules
│   └── ...
├── tests/              # Test suite
├── docs/               # Documentation
└── setup.py            # Package config
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_i18n.py -v

# Run with coverage
python -m pytest tests/ --cov=aicodezh
```

---

## Code Style

### Python

- Follow **PEP 8** style guidelines
- Use **type hints** wherever possible
- `snake_case` for functions and variables, `PascalCase` for classes
- Write docstrings in English; inline comments may be in Chinese or English
- Group imports: stdlib, then third-party, then local (use absolute imports)

### i18n (Internationalization)

- **All user-facing strings** must go through the i18n system (`i18n.t()`)
- Never hardcode UI text — always use translation keys
- When adding new strings, add entries to all locale files

### Commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Japanese locale support
fix: resolve streaming timeout on slow connections
docs: update installation guide for Windows
refactor: simplify skill loading logic
test: add unit tests for i18n module
chore: update dependencies
```

### Pull Requests

- **One feature per PR** — keep changes focused and reviewable
- Include tests if you're adding functionality
- Update docs if your change affects user-facing behavior
- Write a clear PR description explaining *what* and *why*

---

## How to Submit a Pull Request

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   # or: git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**. Keep commits focused and atomic.

3. **Test your changes** locally:
   ```bash
   claudezh --help          # Verify CLI still works
   python -m pytest tests/ -v   # Run tests
   ```

4. **Commit with a clear message**:
   ```bash
   git commit -m "feat: add Japanese locale support"
   ```

5. **Push and create a PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a Pull Request on GitHub. Fill out the PR template — it only takes a minute!

---

## Reporting Bugs

Found a bug? **Thank you!** Bug reports are incredibly valuable.

Use the [Bug Report template](https://github.com/aiai-go/claude/issues/new?template=bug_report.md) on GitHub Issues. The template will guide you through providing the information we need to fix it quickly.

---

## Recognition

We believe in celebrating every contribution:

- **All contributors** are listed in the README — your name and avatar will be there for everyone to see
- **Significant contributors** are invited to become maintainers with write access
- **Every merged PR** gets a thank-you comment from the maintainers

Your work matters. We see it, and we appreciate it.

---

## Code of Conduct

Please read our [Code of Conduct](CODE_OF_CONDUCT.md) before participating. We're committed to providing a welcoming and inclusive experience for everyone.

---

## Questions?

- Open a [Discussion](https://github.com/aiai-go/claude/discussions) on GitHub
- File an [Issue](https://github.com/aiai-go/claude/issues) if you're stuck
- Check existing issues — someone might have had the same question

Don't be shy — there are no stupid questions here!

---

**Thank you for helping make AI coding more accessible to developers everywhere!**
