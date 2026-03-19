# @aiai-go/claude — Community & Social Media Guide

## Brand Voice
- Professional but approachable
- Technical but not intimidating
- Grateful to every contributor
- Never corporate, always human
- Like a senior engineer who genuinely cares about the community

## Social Media Accounts
- GitHub: github.com/aiai-go/claude
- Telegram: t.me/aiai_go
- Twitter: [TBD]
- npm: npmjs.com/package/@aiai-go/claude
- Website: aiaigo.org
- Email: hi@aiaigo.org

---

## PR Review Checklist

When reviewing a pull request:

### Code Quality
- [ ] Code follows existing patterns (read nearby code first)
- [ ] No hardcoded strings — all user-facing text through `t()`
- [ ] i18n: new keys have zh-CN, zh-TW, en translations
- [ ] Modern Rich colors (bright_blue, bright_cyan, dim blue borders)
- [ ] No e-commerce references (Amazon, Shopify)
- [ ] Brand name: @aiai-go/claude (not claudezh, except CLI command)
- [ ] URLs: github.com/aiai-go/claude
- [ ] Safety: no credential modification, no dangerous defaults

### Testing
- [ ] `python3 -c "from aicodezh.cli import run; print('OK')"` passes
- [ ] New features have i18n entries
- [ ] Interactive menus have `0. Back` option

### Response Templates

**Approve:**
```
LGTM! Clean code, good i18n coverage. Thanks for contributing! 🎉
```

**Request changes:**
```
Thanks for the PR! A few things to address:

1. [specific feedback]
2. [specific feedback]

Happy to merge once these are updated. Let me know if you need help!
```

**First-time contributor:**
```
Welcome to @aiai-go/claude! 🎉 Thanks for your first contribution.

[feedback]

Looking forward to merging this!
```

---

## Issue Response Templates

### Bug Report
```
Thanks for reporting this! I can reproduce the issue.

**Root cause:** [explain briefly]
**Fix:** [describe approach]

Working on a fix now — should be in the next release.
```

### Feature Request (aligned)
```
Great idea! This aligns with our roadmap.

I've added this to our backlog. If you'd like to implement it yourself, here's a starting point:
- File to modify: `aicodezh/[file].py`
- Key function: `[function_name]`

Happy to guide you through a PR!
```

### Feature Request (not aligned)
```
Thanks for the suggestion! Interesting idea.

For now, this is outside our current scope — we're focused on [current priorities]. But I'll keep it in mind for future versions.

If you feel strongly about it, you're welcome to fork and experiment!
```

### Language Contribution
```
Awesome! We'd love to add [language] support! 🌍

Here's how:
1. Fork the repo
2. Edit `aicodezh/i18n.py`
3. Add your locale to each `_STRINGS` entry
4. Submit a PR

If you need help getting started, join us on [Telegram](https://t.me/aiai_go)!
```

### Duplicate Issue
```
Thanks for reporting! This looks like a duplicate of #[number].

Following the discussion there. Closing this one to keep things organized — feel free to add your thoughts on the original issue!
```

---

## Release Announcement Templates

### Telegram
```
🚀 @aiai-go/claude v[X.Y.Z] released!

What's new:
- [feature 1]
- [feature 2]
- [feature 3]

Update: npm update -g @aiai-go/claude

Changelog: github.com/aiai-go/claude/releases/tag/v[X.Y.Z]
```

### Twitter
```
🚀 @aiai-go/claude v[X.Y.Z] is out!

[key feature highlight in one sentence]

npm install -g @aiai-go/claude

⭐ github.com/aiai-go/claude

#ClaudeCode #AI #OpenSource #DevTools
```

### GitHub Release Notes
```markdown
## v[X.Y.Z] — [Title]

### What's New
- **[Feature]** — [one-line description]
- **[Feature]** — [one-line description]

### Bug Fixes
- Fixed [issue] (#[number])

### Install / Update
\`\`\`bash
npm install -g @aiai-go/claude
\`\`\`

**Changelog**: [link]
```

---

## Handling Negative Feedback

### "This is just a wrapper"
```
You're right that we build on Claude's capabilities — but we add real value:
undo, safety hooks, session resume, multilingual i18n, and 12 custom tools
that Claude Code doesn't have. Try it and see the difference!
```

### "Why not just use Claude Code directly?"
```
Great question! If you only need English and don't need undo/safety features,
Claude Code is perfect. @aiai-go/claude is for developers who want:
- Multilingual interface
- File undo (AI makes mistakes too)
- Safety hooks (block dangerous commands)
- Session resume (terminals crash)
- Custom MCP tools

It reuses your Claude Code subscription — zero extra cost.
```

### "Is this affiliated with Anthropic?"
```
No — @aiai-go/claude is an independent open-source project. We use
Claude's public SDK and API. Not affiliated with Anthropic.
```

---

## Weekly Community Tasks
1. Check and respond to new issues (within 24h)
2. Review open PRs
3. Post update on Telegram if there's news
4. Thank new contributors publicly
5. Update labels on issues

## Star Milestones
- 10 stars: Post thanks on Telegram
- 50 stars: Twitter celebration post
- 100 stars: Write a blog post / 掘金 article
- 500 stars: Consider ProductHunt launch
- 1000 stars: GitHub Sponsors setup
