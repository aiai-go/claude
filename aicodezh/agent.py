"""
高级中文封装 — claude-agent-sdk 桥接模块

提供 ChineseAgent 持久会话、中文格式化、预设子代理、权限回调、一次性查询。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, AsyncIterator

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    PermissionResultAllow,
    PermissionResultDeny,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolPermissionContext,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

# ---------------------------------------------------------------------------
# 工具名称中文映射
# ---------------------------------------------------------------------------

TOOL_NAME_ZH: dict[str, str] = {
    "Read": "读取文件",
    "Edit": "编辑文件",
    "Write": "写入文件",
    "Bash": "执行命令",
    "Glob": "搜索文件",
    "Grep": "搜索内容",
    "Notebook": "操作笔记本",
    "WebFetch": "抓取网页",
    "WebSearch": "搜索网页",
    "TodoWrite": "写入待办",
    "TodoRead": "读取待办",
}

# ---------------------------------------------------------------------------
# 预设子代理
# ---------------------------------------------------------------------------

PRESET_AGENTS: dict[str, AgentDefinition] = {
    "code_reviewer": AgentDefinition(
        description="代码审查员 — 审查代码质量、发现潜在问题",
        prompt=(
            "你是代码审查专家。用中文指出代码中的问题，包括但不限于：\n"
            "- 逻辑错误和潜在 bug\n"
            "- 安全隐患\n"
            "- 性能问题\n"
            "- 代码风格和可读性\n"
            "- 缺失的边界检查和错误处理\n"
            "给出具体的文件路径、行号和改进建议。"
        ),
        tools=["Read", "Glob", "Grep"],
    ),
    "bug_fixer": AgentDefinition(
        description="Bug修复师 — 定位并修复代码缺陷",
        prompt=(
            "你是 Bug 修复专家。用中文分析问题根因并实施修复。\n"
            "工作流程：\n"
            "1. 理解问题描述，定位相关代码\n"
            "2. 分析根本原因（不做表面补丁）\n"
            "3. 实施最小化修复\n"
            "4. 验证修复不引入新问题\n"
            "修复完成后给出简要总结。"
        ),
        tools=["Read", "Edit", "Write", "Bash", "Grep"],
    ),
    "test_writer": AgentDefinition(
        description="测试工程师 — 编写单元测试和集成测试",
        prompt=(
            "你是测试专家。用中文与用户交流，为指定代码编写测试。\n"
            "要求：\n"
            "- 覆盖正常路径和边界情况\n"
            "- 使用项目已有的测试框架\n"
            "- 测试命名清晰，断言明确\n"
            "- 必要时创建 mock/fixture\n"
            "完成后列出测试覆盖的场景。"
        ),
        tools=["Read", "Write", "Bash", "Glob"],
    ),
}

# ---------------------------------------------------------------------------
# 消息格式化（中文）
# ---------------------------------------------------------------------------


def format_tool_use(block: ToolUseBlock) -> str:
    """格式化工具调用为中文可读字符串。"""
    zh_name = TOOL_NAME_ZH.get(block.name, block.name)
    summary = _summarize_tool_input(block.name, block.input)
    return f"🔧 使用工具: {block.name} | {zh_name} {summary}"


def format_thinking(block: ThinkingBlock) -> str:
    """格式化思考块。"""
    preview = block.thinking[:80].replace("\n", " ") if block.thinking else ""
    suffix = "..." if block.thinking and len(block.thinking) > 80 else ""
    return f"💭 思考中… {preview}{suffix}"


def format_result(msg: ResultMessage) -> str:
    """格式化结果消息为中文摘要。"""
    status = "❌ 出错" if msg.is_error else "✅ 完成"
    parts = [status]

    if msg.usage:
        input_tokens = msg.usage.get("input_tokens", 0)
        output_tokens = msg.usage.get("output_tokens", 0)
        parts.append(f"用量: 输入 {input_tokens} / 输出 {output_tokens} tokens")

    if msg.total_cost_usd is not None:
        parts.append(f"费用: ${msg.total_cost_usd:.4f}")

    if msg.num_turns:
        parts.append(f"轮次: {msg.num_turns}")

    if msg.duration_ms:
        secs = msg.duration_ms / 1000
        parts.append(f"耗时: {secs:.1f}s")

    return " | ".join(parts)


def format_error(e: Exception) -> str:
    """将异常转为中文错误消息。"""
    type_name = type(e).__name__
    error_map: dict[str, str] = {
        "CLINotFoundError": "未找到 Claude CLI，请确认已安装 claude 并加入 PATH",
        "CLIConnectionError": "与 Claude CLI 连接失败，请检查进程是否正常运行",
        "CLIJSONDecodeError": "Claude CLI 返回了无效的 JSON 数据",
        "TimeoutError": "请求超时，请稍后重试",
        "KeyboardInterrupt": "用户中断操作",
    }
    zh = error_map.get(type_name)
    if zh:
        return f"❗ {zh}"
    return f"❗ 错误 ({type_name}): {e}"


def _summarize_tool_input(tool_name: str, tool_input: dict[str, Any]) -> str:
    """从工具输入中提取关键信息用于显示。"""
    if tool_name == "Read":
        return tool_input.get("file_path", "")
    if tool_name in ("Edit", "Write"):
        return tool_input.get("file_path", "")
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return cmd[:60] + ("…" if len(cmd) > 60 else "")
    if tool_name in ("Glob", "Grep"):
        return tool_input.get("pattern", "")
    # 回退：显示精简 JSON
    try:
        s = json.dumps(tool_input, ensure_ascii=False)
        return s[:80] + ("…" if len(s) > 80 else "")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# 权限回调（中文交互）
# ---------------------------------------------------------------------------


async def chinese_permission_handler(
    tool_name: str,
    tool_input: dict[str, Any],
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:
    """中文权限确认回调 — 向用户展示工具操作并等待确认。"""
    zh_name = TOOL_NAME_ZH.get(tool_name, tool_name)
    summary = _summarize_tool_input(tool_name, tool_input)

    print(f"\n⚠️  AI 请求执行操作:")
    print(f"   工具: {tool_name} ({zh_name})")
    if summary:
        print(f"   详情: {summary}")

    try:
        answer = input("   确认执行? [y/n] (默认 y): ").strip().lower()
    except EOFError:
        answer = "y"

    if answer in ("", "y", "yes", "是"):
        return PermissionResultAllow()
    return PermissionResultDeny(message="用户取消了此操作")


# ---------------------------------------------------------------------------
# ChineseAgent — 持久会话封装
# ---------------------------------------------------------------------------


class ChineseAgent:
    """Claude Agent SDK 的中文高级封装，支持持久会话。

    用法::

        agent = ChineseAgent(model="claude-sonnet-4-6")
        await agent.connect(cwd="/my/project")

        async for msg in agent.ask("帮我看看这个项目的结构"):
            print(msg)

        await agent.disconnect()
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        permission_mode: str = "default",
        system_prompt: str | None = None,
        tools: list[str] | None = None,
        max_turns: int | None = None,
        agents: dict[str, AgentDefinition] | None = None,
        use_chinese_permissions: bool = False,
    ) -> None:
        self._model = model
        self._permission_mode = permission_mode
        self._system_prompt = system_prompt or "你是一位经验丰富的编程助手，始终用中文回答。"
        self._tools = tools or ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
        self._max_turns = max_turns
        self._agents = agents
        self._use_chinese_permissions = use_chinese_permissions
        self._client: ClaudeSDKClient | None = None
        self._connected: bool = False

    # -- 生命周期 ----------------------------------------------------------

    async def connect(self, cwd: str | Path = ".") -> None:
        """连接 Claude 会话。"""
        options = self._build_options(cwd=str(cwd))
        self._client = ClaudeSDKClient(options=options)
        await self._client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        """断开会话，释放资源。"""
        if self._client is not None:
            try:
                await self._client.disconnect()
            finally:
                self._client = None
                self._connected = False

    # -- 查询 --------------------------------------------------------------

    async def ask(
        self, prompt: str
    ) -> AsyncIterator[
        AssistantMessage | UserMessage | SystemMessage | ResultMessage
    ]:
        """发送问题，返回流式消息迭代器。"""
        if not self._connected or self._client is None:
            raise RuntimeError("尚未连接，请先调用 connect()")

        self._client.query(prompt)
        async for msg in self._client.receive_messages():
            yield msg

    # -- 设置 --------------------------------------------------------------

    def set_model(self, model: str) -> None:
        """切换模型（下次 ask 生效；若已连接则实时切换）。"""
        self._model = model
        if self._client is not None:
            self._client.set_model(model)

    def set_permission(self, mode: str) -> None:
        """切换权限模式（default / acceptEdits / plan / bypassPermissions）。"""
        self._permission_mode = mode
        if self._client is not None:
            self._client.set_permission_mode(mode)

    # -- 内部 --------------------------------------------------------------

    def _build_options(self, cwd: str = ".") -> ClaudeAgentOptions:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "permission_mode": self._permission_mode,
            "system_prompt": self._system_prompt,
            "tools": self._tools,
            "cwd": cwd,
        }
        if self._max_turns is not None:
            kwargs["max_turns"] = self._max_turns
        if self._agents is not None:
            kwargs["agents"] = self._agents
        if self._use_chinese_permissions:
            kwargs["can_use_tool"] = chinese_permission_handler
        return ClaudeAgentOptions(**kwargs)

    # -- 上下文管理器 ------------------------------------------------------

    async def __aenter__(self) -> ChineseAgent:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.disconnect()

    @property
    def connected(self) -> bool:
        return self._connected


# ---------------------------------------------------------------------------
# quick_query — 一次性查询（无持久会话）
# ---------------------------------------------------------------------------


async def quick_query(
    prompt: str,
    *,
    model: str = "claude-sonnet-4-6",
    system_prompt: str | None = None,
    tools: list[str] | None = None,
    permission_mode: str = "default",
    cwd: str | Path = ".",
    max_turns: int | None = None,
    agents: dict[str, AgentDefinition] | None = None,
) -> AsyncIterator[
    AssistantMessage | UserMessage | SystemMessage | ResultMessage
]:
    """一次性查询 — 不需要持久会话的简便接口。

    用法::

        async for msg in quick_query("用中文解释这段代码", cwd="/my/project"):
            if isinstance(msg, ResultMessage):
                print(format_result(msg))
    """
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt or "你是一位经验丰富的编程助手，始终用中文回答。",
        tools=tools or ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        permission_mode=permission_mode,
        cwd=str(cwd),
        **({"max_turns": max_turns} if max_turns is not None else {}),
        **({"agents": agents} if agents is not None else {}),
    )
    async for msg in query(prompt=prompt, options=options):
        yield msg
