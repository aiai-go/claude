<div align="center">

# claudezh

**全中文 AI 编程助手** — 基于 Claude 的智能编程终端工具

[![npm version](https://img.shields.io/npm/v/claudezh.svg)](https://www.npmjs.com/package/claudezh)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](#english) | [简体中文](#简体中文)

</div>

---

## 简体中文

### 什么是 claudezh？

claudezh 是一个全中文的 AI 编程终端工具。在终端用中文描述需求，AI 自动帮你写代码、改代码、执行命令。

### 特性

- 全中文交互 — 命令、提示、输出全部中文
- 智能工具 — 自动读写文件、执行命令、搜索代码
- 双模式 — 订阅模式（免费复用 Claude Code 订阅）+ API 模式（独立运行）
- 预设模板 — 代码生成、审查、Bug修复、重构、测试、Amazon Listing...
- 预设代理 — 代码审查员、Bug修复师、测试工程师
- 三语支持 — 简体中文 / 繁體中文 / English
- 权限控制 — 安全模式（操作前确认）/ 自动模式（全自动执行）

### 安装

```bash
npm install -g claudezh
```

### 快速开始

```bash
claudezh
```

### 使用示例

```
你> 帮我写一个 FastAPI 的用户注册接口，要有密码加密和 JWT 认证

助手> 我来帮你创建...
  使用工具: Write | 创建文件 app/auth.py
  使用工具: Write | 创建文件 app/models.py
  完成 | 已创建 2 个文件

你> /模板
  1. 代码生成
  2. 代码审查
  3. Bug修复
  ...

你> /自动
  已切换到自动模式，AI 将自动执行所有操作
```

### 中文命令

| 命令 | 英文别名 | 说明 |
|------|----------|------|
| /帮助 | /help | 显示帮助 |
| /清屏 | /clear | 清空对话 |
| /设置 | /settings | 查看设置 |
| /模型 | /model | 切换模型 |
| /语言 | /lang | 切换语言 |
| /模板 | /template | 预设模板 |
| /工具 | /tools | 查看工具 |
| /自动 | /auto | 自动模式 |
| /安全 | /safe | 安全模式 |
| /切换 | /switch | 切换后端 |
| /历史 | /history | 对话历史 |
| /退出 | /exit | 退出 |

### 双模式架构

```
claudezh 启动
  |
检测本机环境
  |-- 有 Claude Code --> 订阅模式（免费）
  +-- 无 Claude Code --> API 模式（需 API Key）
```

**订阅模式**: 复用 Claude Code 订阅，零额外成本，功能完整

**API 模式**: 只需 Anthropic API Key，独立运行，按量付费

### 系统要求

- Node.js >= 16
- Python >= 3.10
- Claude Code（订阅模式）或 Anthropic API Key（API 模式）

### 配置

```bash
# 设置语言
export CLAUDEZH_LANG=zh-CN  # 简体中文（默认）
export CLAUDEZH_LANG=zh-TW  # 繁體中文
export CLAUDEZH_LANG=en     # English

# API 模式需要设置 Key
export ANTHROPIC_API_KEY=your-key-here
```

配置文件位于 `~/.claudezh/config.json`

---

## English

### What is claudezh?

claudezh is a Chinese-first AI coding assistant for the terminal. Describe what you need in Chinese (or English), and AI writes code, edits files, and runs commands for you.

### Install

```bash
npm install -g claudezh
```

### Quick Start

```bash
claudezh
```

### Features

- Full Chinese interface (Simplified / Traditional / English)
- Dual backend: Claude Code subscription (free) or Anthropic API (standalone)
- Built-in tools: file read/write, code search, command execution
- Preset templates: code generation, review, bug fix, refactoring, tests
- Preset agents: code reviewer, bug fixer, test writer
- Permission control: safe mode / auto mode

---

## License

MIT

## Author

[whaleaicode](https://github.com/whaleaicode)
