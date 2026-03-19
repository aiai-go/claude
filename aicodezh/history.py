"""Conversation history management."""
import json
import os
from datetime import datetime, timezone


class History:
    """Manages an in-memory conversation history with persistence."""

    def __init__(self, max_size: int = 100):
        self.messages: list[dict] = []
        self.max_size = max_size

    # -- core operations ------------------------------------------------

    def add(self, role: str, content: str):
        """Append a message and evict the oldest if over *max_size*."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Trim from the front, keeping the most recent messages.
        if len(self.messages) > self.max_size:
            self.messages = self.messages[-self.max_size:]

    def get_recent(self, n: int = 10) -> list[dict]:
        """Return the last *n* messages (or all if fewer)."""
        return self.messages[-n:]

    def clear(self):
        """Remove all messages."""
        self.messages.clear()

    # -- persistence ----------------------------------------------------

    def save(self, path: str):
        """Save the history to a JSON file.

        Parent directories are created automatically.
        """
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"messages": self.messages, "max_size": self.max_size},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load(self, path: str):
        """Load history from a JSON file.

        If the file does not exist or is malformed the history is left
        unchanged (no error raised).
        """
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.messages = data.get("messages", [])
            self.max_size = data.get("max_size", self.max_size)
        except (json.JSONDecodeError, OSError):
            pass

    # -- helpers --------------------------------------------------------

    def __len__(self) -> int:
        return len(self.messages)

    def __bool__(self) -> bool:
        return bool(self.messages)

    def to_api_messages(self) -> list[dict]:
        """Return messages in the ``[{"role": ..., "content": ...}]``
        format expected by the Anthropic API (timestamps stripped)."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.messages
        ]
