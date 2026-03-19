"""
统一后端抽象层 — 订阅模式 (claude-agent-sdk) 与 API 模式 (anthropic) 双轨切换。

架构:
    Backend (ABC)
    ├── SDKBackend   — 基于 claude-agent-sdk，复用 Claude Code 订阅，免费
    └── APIBackend   — 基于 anthropic SDK，独立调用，需 API Key

使用:
    backend = detect_backend()         # 自动检测
    async for event in backend.ask("帮我看看这个项目"):
        if event.type == "text":
            print(event.text)
        elif event.type == "tool_use":
            print(f"工具: {event.tool.name_zh}")
        elif event.type == "done":
            print(f"完成 — {event.usage}")
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from .checkpoint import CheckpointManager, extract_modified_file

logger = logging.getLogger("claudezh.backend")

# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------


@dataclass
class ToolAction:
    """AI 请求执行的工具操作。"""

    name: str  # 工具英文名
    name_zh: str  # 工具中文名
    input: dict  # 工具输入参数
    result: str = ""  # 工具执行结果


@dataclass
class StreamEvent:
    """后端统一流式事件。

    type 取值:
        text         — AI 生成的文本片段 (text 字段)
        tool_use     — AI 请求调用工具 (tool 字段)
        tool_result  — 工具执行结果 (tool 字段, tool.result 已填充)
        thinking     — AI 的思考过程 (text 字段)
        done         — 本轮对话结束 (usage 字段)
        error        — 发生错误 (text 字段)
    """

    type: str
    text: str = ""
    tool: Optional[ToolAction] = None
    usage: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 工具名称中文映射 (SDK 内置 + 自定义)
# ---------------------------------------------------------------------------

TOOL_NAME_ZH: dict[str, str] = {
    # SDK 内置
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
    # 自定义 (APIBackend)
    "read_file": "读取文件",
    "write_file": "写入文件",
    "list_files": "列出文件",
    "search_in_files": "搜索内容",
    "run_command": "执行命令",
    "run_python": "执行 Python",
    "analyze_project": "分析项目",
    "get_git_info": "Git 信息",
}

# Merge custom MCP tool names
try:
    from .mcp_tools import MCP_TOOL_NAMES_ZH
    TOOL_NAME_ZH.update(MCP_TOOL_NAMES_ZH)
except ImportError:
    pass

# SDK 内置工具列表
SDK_BUILTIN_TOOLS = ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]

# APIBackend 中需要用户确认的危险工具
DANGEROUS_TOOLS = {"write_file", "run_command", "run_python"}

# API 模式工具调用最大轮次
MAX_TOOL_ROUNDS = 20


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------


class Backend(ABC):
    """后端抽象接口 — 所有后端实现必须继承此类。"""

    def __init__(self):
        self.checkpoint_mgr = CheckpointManager()

    @abstractmethod
    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        history: list | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """发送提示词，流式产出 StreamEvent。"""
        ...

    @abstractmethod
    def get_mode_name(self) -> str:
        """返回当前模式的中文显示名称。"""
        ...

    @abstractmethod
    def get_model(self) -> str:
        """返回当前使用的模型名称。"""
        ...

    @abstractmethod
    def set_model(self, model: str) -> None:
        """切换模型。"""
        ...

    @abstractmethod
    def set_permission(self, mode: str) -> None:
        """设置权限模式。"""
        ...

    @property
    @abstractmethod
    def available_tools(self) -> list[str]:
        """返回当前后端可用的工具名称列表。"""
        ...


# ---------------------------------------------------------------------------
# SDKBackend — 基于 claude-agent-sdk (订阅模式)
# ---------------------------------------------------------------------------


class SDKBackend(Backend):
    """基于 claude-agent-sdk 的后端 — 需要 Claude Code 已安装并激活订阅。

    内部调用 ``claude_agent_sdk.query()``，自动使用 SDK 内置工具
    (Read, Edit, Write, Bash, Glob, Grep)，无需额外配置。
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        permission_mode: str = "default",
        cwd: str = ".",
        max_turns: int = 20,
    ):
        super().__init__()
        self._model = model
        self._permission_mode = permission_mode
        self._cwd = cwd
        self._max_turns = max_turns
        self._thinking_config = None  # None = SDK default (adaptive)
        self._effort: str | None = None  # None = SDK default
        # 会话恢复
        self._resume_session_id: str | None = None
        self._fork_session: bool = False

    def set_thinking(self, mode: str, budget: int | None = None) -> None:
        """设置思考模式。

        mode:
            "auto" → ThinkingConfigAdaptive (SDK 自适应)
            "deep" → ThinkingConfigEnabled(budget_tokens=100000)
            "off"  → ThinkingConfigDisabled
        """
        from claude_agent_sdk import (
            ThinkingConfigAdaptive,
            ThinkingConfigDisabled,
            ThinkingConfigEnabled,
        )

        if mode == "auto":
            self._thinking_config = ThinkingConfigAdaptive(type="adaptive")
        elif mode == "deep":
            tokens = budget or 100_000
            self._thinking_config = ThinkingConfigEnabled(type="enabled", budget_tokens=tokens)
        elif mode == "off":
            self._thinking_config = ThinkingConfigDisabled(type="disabled")
        else:
            self._thinking_config = None

    def set_effort(self, level: str) -> None:
        """设置推理强度: low / medium / high / max。"""
        if level in ("low", "medium", "high", "max"):
            self._effort = level
        else:
            self._effort = None

    @property
    def thinking_mode(self) -> str:
        """返回当前思考模式名称。"""
        if self._thinking_config is None:
            return "auto"
        if isinstance(self._thinking_config, dict):
            cfg_type = self._thinking_config.get("type", "adaptive")
        else:
            cfg_type = getattr(self._thinking_config, "type", "adaptive")
        return {"adaptive": "auto", "enabled": "deep", "disabled": "off"}.get(cfg_type, "auto")

    @property
    def effort_level(self) -> str:
        """返回当前推理强度。"""
        return self._effort or "medium"

    # -- Backend 接口实现 --------------------------------------------------

    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        history: list | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """通过 claude-agent-sdk 发送请求，产出统一 StreamEvent。"""
        try:
            from claude_agent_sdk import (
                AssistantMessage,
                ClaudeAgentOptions,
                ResultMessage,
                query,
            )
        except ImportError:
            yield StreamEvent(
                type="error",
                text="claude-agent-sdk 未安装。请运行: pip install claude-agent-sdk",
            )
            return

        # 构建安全钩子配置
        hooks_config = None
        try:
            from .hooks import build_hook_config
            hooks_config = build_hook_config()
            logger.debug("安全钩子已加载")
        except Exception as e:
            logger.debug(f"安全钩子加载失败 (非致命): {e}")

        opt_kwargs = {
            "model": self._model,
            "permission_mode": self._permission_mode,
            "max_turns": self._max_turns,
            "tools": list(SDK_BUILTIN_TOOLS),
            "cwd": self._cwd,
            "enable_file_checkpointing": True,
        }
        if system_prompt:
            opt_kwargs["system_prompt"] = system_prompt
        if self._thinking_config is not None:
            opt_kwargs["thinking"] = self._thinking_config
        if self._effort is not None:
            opt_kwargs["effort"] = self._effort

        # 会话恢复
        if self._resume_session_id:
            opt_kwargs["resume"] = self._resume_session_id
            if self._fork_session:
                opt_kwargs["fork_session"] = True
            # 一次性使用，恢复后清除
            self._resume_session_id = None
            self._fork_session = False

        if hooks_config:
            opt_kwargs["hooks"] = hooks_config

        # 加载自定义 MCP 工具服务器
        try:
            from .mcp_tools import create_claudezh_mcp_server
            mcp_server = create_claudezh_mcp_server()
            opt_kwargs["mcp_servers"] = {"claudezh-tools": mcp_server}
            logger.debug("自定义 MCP 工具已加载")
        except Exception as e:
            logger.debug(f"MCP 工具加载失败 (非致命): {e}")

        options = ClaudeAgentOptions(**opt_kwargs)

        # 开始文件检查点
        self.checkpoint_mgr.begin_checkpoint(prompt)

        try:
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        # 文本块
                        if hasattr(block, "text") and block.text:
                            yield StreamEvent(type="text", text=block.text)

                        # 思考块
                        elif hasattr(block, "thinking") and block.thinking:
                            yield StreamEvent(type="thinking", text=block.thinking)

                        # 工具调用块
                        elif hasattr(block, "name"):
                            tool_name = block.name
                            tool_input = (
                                block.input if hasattr(block, "input") else {}
                            )

                            # 检查点: 在文件修改前备份
                            modified_file = extract_modified_file(tool_name, tool_input)
                            if modified_file:
                                self.checkpoint_mgr.track_file_modification(modified_file)

                            tool = ToolAction(
                                name=tool_name,
                                name_zh=TOOL_NAME_ZH.get(tool_name, tool_name),
                                input=tool_input,
                            )
                            yield StreamEvent(type="tool_use", tool=tool)

                        # 工具结果块
                        elif hasattr(block, "content") and hasattr(block, "tool_use_id"):
                            content = block.content if isinstance(block.content, str) else str(block.content)
                            tool = ToolAction(
                                name="",
                                name_zh="",
                                input={},
                                result=content[:500],
                            )
                            yield StreamEvent(type="tool_result", tool=tool)

                elif isinstance(message, ResultMessage):
                    usage = {}
                    if message.usage:
                        if isinstance(message.usage, dict):
                            usage = message.usage
                        else:
                            usage = {
                                "input_tokens": getattr(
                                    message.usage, "input_tokens", 0
                                ),
                                "output_tokens": getattr(
                                    message.usage, "output_tokens", 0
                                ),
                            }
                    yield StreamEvent(type="done", usage=usage)

        except KeyboardInterrupt:
            yield StreamEvent(type="error", text="用户中断操作")
        except Exception as e:
            error_text = _classify_error(e)
            yield StreamEvent(type="error", text=error_text)
        finally:
            # 完成检查点 (无论成功失败都记录)
            self.checkpoint_mgr.finish_checkpoint()

    def get_mode_name(self) -> str:
        return "订阅模式 (Claude Code)"

    def get_model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        self._model = model

    def set_permission(self, mode: str) -> None:
        self._permission_mode = mode

    @property
    def available_tools(self) -> list[str]:
        tools = list(SDK_BUILTIN_TOOLS)
        try:
            from .mcp_tools import MCP_TOOL_NAMES_ZH
            tools.extend(MCP_TOOL_NAMES_ZH.keys())
        except ImportError:
            pass
        return tools

    # -- 会话管理 (Session resume) ------------------------------------------

    def list_sessions(self, limit: int = 20) -> list:
        """列出最近的会话。返回 SDKSessionInfo 列表。"""
        try:
            from claude_agent_sdk import list_sessions
            return list_sessions(limit=limit)
        except ImportError:
            logger.warning("claude-agent-sdk 未安装，无法列出会话")
            return []
        except Exception as e:
            logger.warning(f"列出会话失败: {e}")
            return []

    def get_session_messages(self, session_id: str, limit: int = 50) -> list:
        """获取指定会话的消息历史。返回 SessionMessage 列表。"""
        try:
            from claude_agent_sdk import get_session_messages
            return get_session_messages(session_id=session_id, limit=limit)
        except ImportError:
            logger.warning("claude-agent-sdk 未安装，无法获取会话消息")
            return []
        except Exception as e:
            logger.warning(f"获取会话消息失败: {e}")
            return []

    def resume_session(self, session_id: str, fork: bool = False) -> None:
        """设置下一次 ask() 使用 resume 模式继续指定会话。"""
        self._resume_session_id = session_id
        self._fork_session = fork


# ---------------------------------------------------------------------------
# APIBackend — 基于 anthropic SDK (独立 API 模式)
# ---------------------------------------------------------------------------


class APIBackend(Backend):
    """基于 anthropic SDK 的后端 — 需要 API Key，独立计费。

    使用 ``anthropic.Anthropic`` 客户端，自动管理工具调用循环:
    AI 请求工具 → 执行工具 → 发送结果 → 重复直到 AI 给出文本回复。

    危险工具 (write_file, run_command, run_python) 执行前会请求用户确认。
    """

    # effort → max_tokens 映射 (API 模式下用 max_tokens 模拟强度)
    EFFORT_MAX_TOKENS = {
        "low": 1024,
        "medium": 4096,
        "high": 8192,
        "max": 16384,
    }

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        permission_mode: str = "default",
        timeout: float = 120.0,
    ):
        super().__init__()
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._base_max_tokens = max_tokens  # 保存原始值
        self._permission_mode = permission_mode
        self._timeout = timeout
        self._client = None
        self._effort: str = "medium"

    def set_thinking(self, mode: str, budget: int | None = None) -> None:
        """API 模式下思考功能有限，仅做标记。"""
        pass  # API 模式暂不支持 extended thinking

    def set_effort(self, level: str) -> None:
        """设置推理强度 — API 模式通过调整 max_tokens 模拟。"""
        if level in self.EFFORT_MAX_TOKENS:
            self._effort = level
            self._max_tokens = self.EFFORT_MAX_TOKENS[level]

    @property
    def thinking_mode(self) -> str:
        return "off"  # API 模式不支持 extended thinking

    @property
    def effort_level(self) -> str:
        return self._effort

    def _ensure_client(self):
        """懒初始化 anthropic 客户端。"""
        if self._client is not None:
            return
        try:
            import anthropic

            self._client = anthropic.Anthropic(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        except ImportError:
            raise RuntimeError(
                "anthropic SDK 未安装。请运行: pip install anthropic"
            )

    # -- Backend 接口实现 --------------------------------------------------

    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        history: list | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """通过 anthropic API 发送请求，处理工具调用循环。"""
        try:
            self._ensure_client()
        except RuntimeError as e:
            yield StreamEvent(type="error", text=str(e))
            return

        # 构建工具 schema
        tools = _build_api_tools()

        # 构建消息列表
        messages = []
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        # 构建请求参数
        create_kwargs = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "messages": messages,
            "tools": tools,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        # 开始文件检查点
        self.checkpoint_mgr.begin_checkpoint(prompt)

        # 工具调用循环
        total_input = 0
        total_output = 0

        try:
            for round_num in range(MAX_TOOL_ROUNDS):
                try:
                    import anthropic as anthropic_mod

                    response = self._client.messages.create(**create_kwargs)
                except Exception as e:
                    yield StreamEvent(type="error", text=_classify_error(e))
                    return

                # 累计 token 用量
                if response.usage:
                    total_input += response.usage.input_tokens
                    total_output += response.usage.output_tokens

                # 检查是否有工具调用
                has_tool_use = False
                tool_results = []

                for block in response.content:
                    if block.type == "text":
                        yield StreamEvent(type="text", text=block.text)

                    elif block.type == "tool_use":
                        has_tool_use = True
                        tool_name = block.name
                        tool_input = block.input

                        # 检查点: 在文件修改前备份
                        modified_file = extract_modified_file(tool_name, tool_input)
                        if modified_file:
                            self.checkpoint_mgr.track_file_modification(modified_file)

                        tool = ToolAction(
                            name=tool_name,
                            name_zh=TOOL_NAME_ZH.get(tool_name, tool_name),
                            input=tool_input,
                        )
                        yield StreamEvent(type="tool_use", tool=tool)

                        # 执行工具
                        result = await _execute_tool(
                            tool_name, tool_input, self._permission_mode
                        )
                        tool.result = result

                        yield StreamEvent(
                            type="tool_result",
                            tool=ToolAction(
                                name=tool_name,
                                name_zh=TOOL_NAME_ZH.get(tool_name, tool_name),
                                input=tool_input,
                                result=result[:500] if len(result) > 500 else result,
                            ),
                        )

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )

                    elif hasattr(block, "thinking") and block.type == "thinking":
                        yield StreamEvent(
                            type="thinking",
                            text=getattr(block, "thinking", ""),
                        )

                # 如果没有工具调用或 stop_reason 是 end_turn, 结束循环
                if not has_tool_use or response.stop_reason == "end_turn":
                    break

                # 有工具调用 — 将 assistant 回复 + tool results 追加到 messages
                # assistant 回复 (包含 tool_use blocks)
                messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            _block_to_dict(b) for b in response.content
                        ],
                    }
                )
                # tool results
                messages.append({"role": "user", "content": tool_results})

                # 更新 create_kwargs 的 messages
                create_kwargs["messages"] = messages
            else:
                # 超过最大轮次
                yield StreamEvent(
                    type="error",
                    text=f"工具调用超过最大轮次限制 ({MAX_TOOL_ROUNDS})，已终止。",
                )

            yield StreamEvent(
                type="done",
                usage={
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                },
            )
        finally:
            # 完成检查点 (无论成功失败都记录)
            self.checkpoint_mgr.finish_checkpoint()

    def get_mode_name(self) -> str:
        return "API 模式 (独立)"

    def get_model(self) -> str:
        return self._model

    def set_model(self, model: str) -> None:
        self._model = model

    def set_permission(self, mode: str) -> None:
        self._permission_mode = mode

    @property
    def available_tools(self) -> list[str]:
        from .tools import TOOL_REGISTRY

        return list(TOOL_REGISTRY.keys())


# ---------------------------------------------------------------------------
# 后端自动检测
# ---------------------------------------------------------------------------


def detect_backend(config: dict | None = None) -> Backend:
    """自动检测并创建最佳可用后端。

    优先级:
      1. config 指定 mode="api"  → APIBackend
      2. config 指定 mode="sdk"  → SDKBackend
      3. 自动检测:
         a. ``claude`` CLI 存在 → SDKBackend (订阅模式, 免费)
         b. 有 API Key → APIBackend (独立模式)
         c. 都没有 → 抛出异常并给出中文指引

    参数:
        config: 可选配置字典，支持 key:
            - mode: "api" | "sdk" | "auto" (默认 auto)
            - api_key: Anthropic API Key
            - model: 模型名称
            - permission_mode: 权限模式
            - cwd: 工作目录

    返回:
        Backend 实例
    """
    config = config or {}
    mode = config.get("mode", "auto")
    model = config.get("model", "claude-sonnet-4-6")
    permission_mode = config.get("permission_mode", "default")
    cwd = config.get("cwd", ".")

    # 强制 API 模式
    if mode == "api":
        api_key = _resolve_api_key(config)
        if not api_key:
            raise RuntimeError(
                "API 模式需要 API Key。\n"
                "请设置环境变量 ANTHROPIC_API_KEY 或在配置中提供 api_key。"
            )
        logger.info("后端: API 模式 (用户指定)")
        return APIBackend(
            api_key=api_key,
            model=model,
            permission_mode=permission_mode,
        )

    # 强制 SDK 模式
    if mode == "sdk":
        if not _check_claude_cli():
            raise RuntimeError(
                "SDK 模式需要安装 Claude Code CLI。\n"
                "请参考: https://docs.anthropic.com/en/docs/claude-code"
            )
        logger.info("后端: SDK 模式 (用户指定)")
        return SDKBackend(
            model=model,
            permission_mode=permission_mode,
            cwd=cwd,
        )

    # 自动检测
    # 优先尝试 SDK (免费)
    if _check_claude_cli():
        logger.info("后端: SDK 模式 (自动检测 — 发现 claude CLI)")
        return SDKBackend(
            model=model,
            permission_mode=permission_mode,
            cwd=cwd,
        )

    # 其次尝试 API
    api_key = _resolve_api_key(config)
    if api_key:
        logger.info("后端: API 模式 (自动检测 — 发现 API Key)")
        return APIBackend(
            api_key=api_key,
            model=model,
            permission_mode=permission_mode,
        )

    # 两者都不可用
    raise RuntimeError(
        "未找到可用的后端。请选择以下方式之一:\n"
        "\n"
        "  方式一 (推荐): 安装 Claude Code，使用订阅模式 (免费)\n"
        "    → npm install -g @anthropic-ai/claude-code\n"
        "    → 运行 claude 完成登录\n"
        "\n"
        "  方式二: 提供 API Key，使用独立 API 模式\n"
        "    → export ANTHROPIC_API_KEY=sk-ant-...\n"
        "    → 或在 ~/.claudezh/config.json 中设置 api_key\n"
    )


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------


def _check_claude_cli() -> bool:
    """检查 claude CLI 是否可用。"""
    return shutil.which("claude") is not None


def _resolve_api_key(config: dict) -> str | None:
    """从 config 或环境变量中解析 API Key。"""
    # 1. config 直接指定
    key = config.get("api_key", "").strip()
    if key:
        return key

    # 2. 环境变量
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # 3. 配置文件
    try:
        from .config import load_config

        saved = load_config()
        key = saved.get("api_key", "").strip()
        if key:
            return key
    except Exception:
        pass

    return None


def _classify_error(e: Exception) -> str:
    """将异常转为中文错误消息。"""
    msg = str(e).lower()

    if "auth" in msg or "key" in msg or "unauthorized" in msg or "401" in msg:
        return f"认证失败，请检查 API Key 或 CLI 配置。({type(e).__name__})"
    if "connect" in msg or "network" in msg or "timeout" in msg:
        return f"网络连接失败，请检查网络。({type(e).__name__})"
    if "rate" in msg and "limit" in msg:
        return f"请求频率超限，请稍后重试。({type(e).__name__})"
    if "not found" in msg or "404" in msg:
        return f"资源未找到。({type(e).__name__}: {e})"
    if "overloaded" in msg or "529" in msg or "503" in msg:
        return f"服务暂时过载，请稍后重试。({type(e).__name__})"

    return f"错误 ({type(e).__name__}): {e}"


def _build_api_tools() -> list[dict]:
    """从 tools.py 的 TOOL_REGISTRY 构建 anthropic API 工具 schema。"""
    from .tools import TOOL_REGISTRY

    tools = []

    # 工具参数到 JSON Schema 类型的映射
    _param_schemas = {
        "read_file": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径",
                },
            },
            "required": ["path"],
        },
        "write_file": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要写入的文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "文件内容",
                },
            },
            "required": ["path", "content"],
        },
        "list_files": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目录路径",
                    "default": ".",
                },
                "pattern": {
                    "type": "string",
                    "description": "glob 匹配模式",
                    "default": "**/*",
                },
            },
            "required": [],
        },
        "search_in_files": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "正则表达式搜索模式",
                },
                "path": {
                    "type": "string",
                    "description": "搜索目录路径",
                    "default": ".",
                },
                "glob": {
                    "type": "string",
                    "description": "文件匹配模式",
                    "default": "**/*",
                },
            },
            "required": ["pattern"],
        },
        "run_command": {
            "type": "object",
            "properties": {
                "cmd": {
                    "type": "string",
                    "description": "要执行的 Shell 命令",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时秒数",
                    "default": 30,
                },
            },
            "required": ["cmd"],
        },
        "run_python": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时秒数",
                    "default": 30,
                },
            },
            "required": ["code"],
        },
        "analyze_project": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "项目目录路径",
                    "default": ".",
                },
            },
            "required": [],
        },
        "get_git_info": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Git 仓库路径",
                    "default": ".",
                },
            },
            "required": [],
        },
    }

    for name, info in TOOL_REGISTRY.items():
        schema = _param_schemas.get(name)
        if not schema:
            # 兜底: 根据 params 生成简单 schema
            schema = {
                "type": "object",
                "properties": {
                    k: {"type": "string", "description": v}
                    for k, v in info.get("params", {}).items()
                },
                "required": list(info.get("params", {}).keys()),
            }

        tools.append(
            {
                "name": name,
                "description": info["description"],
                "input_schema": schema,
            }
        )

    return tools


def _block_to_dict(block) -> dict:
    """将 anthropic API 返回的 content block 转为可序列化字典。"""
    if block.type == "text":
        return {"type": "text", "text": block.text}
    elif block.type == "tool_use":
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    elif hasattr(block, "thinking"):
        return {
            "type": "thinking",
            "thinking": getattr(block, "thinking", ""),
        }
    # 兜底
    return {"type": "text", "text": str(block)}


async def _execute_tool(
    tool_name: str, tool_input: dict, permission_mode: str
) -> str:
    """执行工具并返回结果字符串。

    危险工具在非自动模式下会请求用户确认。
    """
    from .tools import TOOL_REGISTRY

    tool_info = TOOL_REGISTRY.get(tool_name)
    if not tool_info:
        return f"未知工具: {tool_name}"

    func = tool_info["function"]

    # 危险工具确认 (非自动模式)
    if tool_name in DANGEROUS_TOOLS and permission_mode != "acceptEdits":
        confirmed = await _confirm_dangerous_tool(tool_name, tool_input)
        if not confirmed:
            return "用户取消了此操作。"

    # 执行工具
    try:
        result = func(**tool_input)
        # 将结果转为字符串
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif isinstance(result, list):
            return json.dumps(result, ensure_ascii=False, indent=2)
        elif result is None:
            return "操作完成。"
        else:
            return str(result)
    except Exception as e:
        return f"工具执行出错 ({type(e).__name__}): {e}"


async def _confirm_dangerous_tool(tool_name: str, tool_input: dict) -> bool:
    """在终端中请求用户确认危险工具操作。

    使用 asyncio 在事件循环中运行阻塞的 input()。
    """
    import asyncio

    zh_name = TOOL_NAME_ZH.get(tool_name, tool_name)

    # 构建操作摘要
    summary = ""
    if tool_name == "write_file":
        summary = tool_input.get("path", "")
    elif tool_name == "run_command":
        cmd = tool_input.get("cmd", "")
        summary = cmd[:80] + ("..." if len(cmd) > 80 else "")
    elif tool_name == "run_python":
        code = tool_input.get("code", "")
        first_line = code.split("\n")[0][:80]
        summary = first_line + ("..." if len(code) > 80 or "\n" in code else "")

    prompt_text = (
        f"\n  ⚠️  AI 请求执行危险操作:\n"
        f"     工具: {tool_name} ({zh_name})\n"
    )
    if summary:
        prompt_text += f"     详情: {summary}\n"
    prompt_text += "     确认执行? [y/n] (默认 y): "

    def _ask():
        try:
            print(prompt_text, end="", flush=True)
            answer = input().strip().lower()
            return answer in ("", "y", "yes", "是")
        except (EOFError, KeyboardInterrupt):
            return False

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ask)
