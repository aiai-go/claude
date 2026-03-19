"""
文件检查点系统 — 支持撤销 AI 对文件的修改。

架构:
    CheckpointManager 负责:
    1. 在每次 ask() 调用前，记录当前检查点信息
    2. 监听工具调用事件 (Edit/Write/write_file)，在文件被修改前备份
    3. 提供 undo() 方法回滚到指定检查点
    4. 提供 list_checkpoints() 方法查看可用检查点

存储:
    ~/.claudezh/checkpoints/
    ├── checkpoint_001/          # 每个检查点一个目录
    │   ├── meta.json            # 检查点元数据
    │   └── files/               # 被修改文件的备份 (保留原始路径结构)
    │       └── home/user/project/file.py
    ├── checkpoint_002/
    ...
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import get_config_dir
from .i18n import t

logger = logging.getLogger("claudezh.checkpoint")

# 最多保留的检查点数量
MAX_CHECKPOINTS = 50

# 单个文件最大备份大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


def _checkpoints_dir() -> Path:
    """检查点存储根目录。"""
    d = get_config_dir() / "checkpoints"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class CheckpointInfo:
    """检查点元数据。"""
    checkpoint_id: str           # 检查点唯一ID
    timestamp: float             # 创建时间戳
    prompt_preview: str          # 用户提示词预览 (前60字符)
    files_backed_up: list[str]   # 已备份的文件路径列表
    files_created: list[str]     # AI 新创建的文件路径列表 (撤销时需删除)
    session_id: str = ""         # SDK session_id (如果有)

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "timestamp": self.timestamp,
            "prompt_preview": self.prompt_preview,
            "files_backed_up": self.files_backed_up,
            "files_created": self.files_created,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> CheckpointInfo:
        return cls(
            checkpoint_id=d["checkpoint_id"],
            timestamp=d["timestamp"],
            prompt_preview=d.get("prompt_preview", ""),
            files_backed_up=d.get("files_backed_up", []),
            files_created=d.get("files_created", []),
            session_id=d.get("session_id", ""),
        )

    @property
    def time_str(self) -> str:
        """格式化的时间字符串。"""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


class CheckpointManager:
    """文件检查点管理器。"""

    def __init__(self):
        self._current: Optional[CheckpointInfo] = None
        self._backed_up_files: set[str] = set()  # 当前检查点中已备份的文件

    def begin_checkpoint(self, prompt: str, session_id: str = "") -> str:
        """开始一个新检查点 — 在 ask() 调用前调用。

        返回 checkpoint_id。
        """
        checkpoint_id = f"ckpt_{int(time.time() * 1000)}"
        self._current = CheckpointInfo(
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
            prompt_preview=prompt[:60],
            files_backed_up=[],
            files_created=[],
            session_id=session_id,
        )
        self._backed_up_files = set()

        # 创建检查点目录
        ckpt_dir = _checkpoints_dir() / checkpoint_id
        (ckpt_dir / "files").mkdir(parents=True, exist_ok=True)

        logger.debug("开始检查点: %s", checkpoint_id)
        return checkpoint_id

    def track_file_modification(self, file_path: str) -> None:
        """在文件被修改前备份。由工具调用事件触发。

        如果文件存在，备份原始内容；如果文件不存在（新创建），
        记录到 files_created 列表中（撤销时删除）。
        """
        if self._current is None:
            return

        abs_path = os.path.abspath(file_path)

        # 避免重复备份同一文件
        if abs_path in self._backed_up_files:
            return
        self._backed_up_files.add(abs_path)

        ckpt_dir = _checkpoints_dir() / self._current.checkpoint_id / "files"

        if os.path.exists(abs_path):
            # 文件已存在 — 备份原始内容
            try:
                file_size = os.path.getsize(abs_path)
                if file_size > MAX_FILE_SIZE:
                    logger.warning("文件过大，跳过备份: %s (%d bytes)", abs_path, file_size)
                    return

                # 使用绝对路径的结构保存备份
                # /home/user/project/file.py -> checkpoints/ckpt_xxx/files/_home_user_project_file.py
                safe_name = abs_path.replace("/", "_").replace("\\", "_").lstrip("_")
                backup_path = ckpt_dir / safe_name

                shutil.copy2(abs_path, backup_path)
                self._current.files_backed_up.append(abs_path)
                logger.debug("已备份文件: %s -> %s", abs_path, backup_path)

            except (OSError, IOError) as e:
                logger.warning("备份文件失败: %s — %s", abs_path, e)
        else:
            # 文件不存在 — 标记为新创建的文件
            self._current.files_created.append(abs_path)
            logger.debug("标记为新文件: %s", abs_path)

    def finish_checkpoint(self) -> Optional[CheckpointInfo]:
        """完成当前检查点 — 在 ask() 完成后调用。

        仅当有文件变更时才保存检查点。
        返回检查点信息，如果没有变更则返回 None。
        """
        if self._current is None:
            return None

        info = self._current
        self._current = None
        self._backed_up_files = set()

        # 没有任何文件变更 — 清理空检查点目录
        if not info.files_backed_up and not info.files_created:
            ckpt_dir = _checkpoints_dir() / info.checkpoint_id
            if ckpt_dir.exists():
                shutil.rmtree(ckpt_dir, ignore_errors=True)
            logger.debug("无文件变更，丢弃检查点: %s", info.checkpoint_id)
            return None

        # 保存元数据
        meta_path = _checkpoints_dir() / info.checkpoint_id / "meta.json"
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(info.to_dict(), f, ensure_ascii=False, indent=2)
        except (OSError, IOError) as e:
            logger.error("保存检查点元数据失败: %s", e)

        # 清理过多的旧检查点
        self._cleanup_old_checkpoints()

        logger.info("检查点已保存: %s (备份 %d 文件, 新建 %d 文件)",
                     info.checkpoint_id, len(info.files_backed_up), len(info.files_created))
        return info

    def list_checkpoints(self) -> list[CheckpointInfo]:
        """列出所有可用检查点，按时间倒序。"""
        checkpoints = []
        ckpts_dir = _checkpoints_dir()

        for entry in sorted(ckpts_dir.iterdir(), reverse=True):
            if not entry.is_dir() or not entry.name.startswith("ckpt_"):
                continue
            meta_path = entry / "meta.json"
            if not meta_path.exists():
                continue
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append(CheckpointInfo.from_dict(data))
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        return checkpoints

    def undo(self, checkpoint_id: Optional[str] = None) -> tuple[bool, str, list[str]]:
        """撤销到指定检查点。

        参数:
            checkpoint_id: 要回滚到的检查点ID。如果为 None，回滚最近的检查点。

        返回:
            (success, message, reverted_files) 三元组
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return False, t("undo.no_checkpoints"), []

        target: Optional[CheckpointInfo] = None
        if checkpoint_id is None:
            target = checkpoints[0]
        else:
            for ckpt in checkpoints:
                if ckpt.checkpoint_id == checkpoint_id:
                    target = ckpt
                    break

        if target is None:
            return False, f"Checkpoint not found: {checkpoint_id}", []

        reverted_files: list[str] = []
        errors: list[str] = []

        ckpt_dir = _checkpoints_dir() / target.checkpoint_id / "files"

        for file_path in target.files_backed_up:
            safe_name = file_path.replace("/", "_").replace("\\", "_").lstrip("_")
            backup_path = ckpt_dir / safe_name

            if not backup_path.exists():
                errors.append(f"Backup file missing: {file_path}")
                continue

            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                shutil.copy2(str(backup_path), file_path)
                reverted_files.append(f"[{t('undo.restored')}] {file_path}")
            except (OSError, IOError) as e:
                errors.append(f"Restore failed {file_path}: {e}")

        for file_path in target.files_created:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    reverted_files.append(f"[{t('undo.removed')}] {file_path}")
                except (OSError, IOError) as e:
                    errors.append(f"Delete failed {file_path}: {e}")

        for ckpt in checkpoints:
            if ckpt.timestamp >= target.timestamp:
                ckpt_path = _checkpoints_dir() / ckpt.checkpoint_id
                if ckpt_path.exists():
                    shutil.rmtree(ckpt_path, ignore_errors=True)

        if errors:
            error_msg = "; ".join(errors)
            msg = f"Partial undo ({len(reverted_files)} files), errors: {error_msg}"
            return True, msg, reverted_files

        msg = f"Undone to {target.time_str} ({len(reverted_files)} files)"
        return True, msg, reverted_files

    def _cleanup_old_checkpoints(self):
        """清理超出 MAX_CHECKPOINTS 的旧检查点。"""
        checkpoints = self.list_checkpoints()
        if len(checkpoints) <= MAX_CHECKPOINTS:
            return

        for ckpt in checkpoints[MAX_CHECKPOINTS:]:
            ckpt_path = _checkpoints_dir() / ckpt.checkpoint_id
            if ckpt_path.exists():
                shutil.rmtree(ckpt_path, ignore_errors=True)
                logger.debug("清理旧检查点: %s", ckpt.checkpoint_id)


# ---------------------------------------------------------------------------
# 工具名称 → 文件路径参数名 映射
# ---------------------------------------------------------------------------

# SDK 内置工具中涉及文件修改的工具及其路径参数
FILE_MODIFY_TOOLS = {
    # SDK tools
    "Edit": "file_path",
    "Write": "file_path",
    # API tools
    "write_file": "path",
}

# 可能创建新文件的命令模式 (Bash 工具)
_BASH_FILE_PATTERNS = [
    # 重定向写入
    r">\s*(\S+)",
    r">>\s*(\S+)",
]


def extract_modified_file(tool_name: str, tool_input: dict) -> Optional[str]:
    """从工具调用中提取被修改的文件路径。

    返回文件的绝对路径，如果工具不涉及文件修改则返回 None。
    """
    param_name = FILE_MODIFY_TOOLS.get(tool_name)
    if param_name:
        path = tool_input.get(param_name)
        if path:
            return os.path.abspath(path)

    # Bash 工具: 尝试从命令中提取文件路径 (尽力而为)
    if tool_name == "Bash":
        import re
        cmd = tool_input.get("command", "")
        for pattern in _BASH_FILE_PATTERNS:
            match = re.search(pattern, cmd)
            if match:
                path = match.group(1).strip("'\"")
                if path and not path.startswith("/dev/"):
                    return os.path.abspath(path)

    return None
