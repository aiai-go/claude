"""Usage tracking for @aiai-go/claude.

Reads REAL usage data from Claude's internal API (utilization percentages)
and from Claude Code's stats-cache.json when available.
Tracks per-session stats locally as fallback.
"""

import json
import os
import time
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta


# ---------------------------------------------------------------------------
# Real Claude usage API (utilization percentages from claude.ai)
# ---------------------------------------------------------------------------

_usage_cache: dict | None = None
_usage_cache_time: float = 0


def get_real_claude_usage() -> dict | None:
    """Get real usage data from Claude's internal API.

    Returns dict with five_hour and seven_day utilization percentages,
    or None if unavailable. NEVER modifies credentials or account state.
    """
    try:
        # Step 1: Read OAuth token (READ ONLY, never modify)
        creds_path = Path.home() / ".claude" / ".credentials.json"
        if not creds_path.exists():
            return None

        with open(creds_path, "r") as f:
            creds = json.load(f)

        oauth = creds.get("claudeAiOauth", {})
        access_token = oauth.get("accessToken")
        if not access_token:
            return None

        # Check if token is expired
        expires_at = oauth.get("expiresAt", 0)
        if expires_at > 1e12:  # milliseconds
            expires_at = expires_at / 1000
        if expires_at < datetime.now(timezone.utc).timestamp():
            return None  # Token expired, don't try

        # Step 2: Get org ID
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "claude-code/2.1.79",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(
            "https://claude.ai/api/organizations",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            orgs = json.loads(resp.read())

        if not orgs:
            return None

        org_id = orgs[0].get("uuid") or orgs[0].get("id")
        if not org_id:
            return None

        # Step 3: Get usage (READ ONLY)
        req = urllib.request.Request(
            f"https://claude.ai/api/organizations/{org_id}/usage",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            usage = json.loads(resp.read())

        return usage

    except Exception:
        return None


def get_cached_usage() -> dict | None:
    """Get usage data with 60-second cache to avoid rate limits."""
    global _usage_cache, _usage_cache_time
    if time.time() - _usage_cache_time < 60:
        return _usage_cache
    _usage_cache = get_real_claude_usage()
    _usage_cache_time = time.time()
    return _usage_cache


def make_usage_bar(pct: float, width: int = 20) -> str:
    """Build a progress bar from a real utilization percentage."""
    pct = max(0.0, min(100.0, pct))
    filled = int(width * pct / 100)
    return "\u2588" * filled + "\u2591" * (width - filled)


def format_time_remaining(resets_at: str) -> str:
    """Calculate human-readable time remaining until reset."""
    try:
        reset_time = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = reset_time - now
        if diff.total_seconds() <= 0:
            return "now"
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes = remainder // 60
        if hours >= 24:
            days = hours // 24
            hours = hours % 24
            return f"{days}d {hours}h"
        return f"{hours}h {minutes}m"
    except Exception:
        return "?"


# ---------------------------------------------------------------------------
# Real Claude Code stats reader (stats-cache.json)
# ---------------------------------------------------------------------------

CLAUDE_STATS_FILE = Path.home() / ".claude" / "stats-cache.json"


def get_claude_stats() -> dict | None:
    """Read real usage stats from Claude Code's stats-cache.json.

    Returns parsed dict or None if unavailable.
    """
    if not CLAUDE_STATS_FILE.exists():
        return None
    try:
        with open(CLAUDE_STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_real_usage_summary() -> dict | None:
    """Extract a human-friendly summary from Claude Code stats.

    Returns dict with keys:
        total_sessions, total_messages,
        today (dict with date, messages, sessions, tool_calls),
        recent_days (list of last 7 days),
        models (dict of model -> token stats),
        first_session_date
    or None if stats unavailable.
    """
    stats = get_claude_stats()
    if not stats:
        return None

    daily = stats.get("dailyActivity", [])
    models = stats.get("modelUsage", {})
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Find today's entry
    today_data = None
    for day in daily:
        if day.get("date") == today_str:
            today_data = day
            break

    # Recent 7 days
    recent = sorted(daily, key=lambda d: d.get("date", ""), reverse=True)[:7]

    return {
        "total_sessions": stats.get("totalSessions", 0),
        "total_messages": stats.get("totalMessages", 0),
        "first_session_date": stats.get("firstSessionDate", ""),
        "today": today_data,
        "recent_days": recent,
        "models": models,
    }


# ---------------------------------------------------------------------------
# Local session tracker (accurate per-session stats)
# ---------------------------------------------------------------------------

class QuotaTracker:
    """Track per-session usage stats.

    Persists usage records to ``~/.claudezh/usage_history.json``.
    Provides honest session-level stats without fake limits.
    """

    def __init__(self, config_dir: Path | None = None):
        self.config_dir = config_dir or Path.home() / ".claudezh"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.usage_file = self.config_dir / "usage_history.json"
        self.records: list[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "",
        cost_usd: float = 0.0,
        prompt: str = "",
        num_turns: int = 1,
        duration_ms: int = 0,
    ) -> None:
        """Record a single usage event (one ask() round-trip)."""
        record = {
            "ts": time.time(),
            "in": input_tokens,
            "out": output_tokens,
            "model": model,
            "cost": cost_usd,
            "prompt": prompt[:80] if prompt else "",
            "turns": num_turns,
            "dur_ms": duration_ms,
        }
        self.records.append(record)
        self._save()

    def get_session_stats(self) -> dict:
        """Get stats for the current session (records from last load)."""
        return self._aggregate(self.records)

    def get_today_stats(self) -> dict:
        """Usage for today (since midnight local time)."""
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = midnight.timestamp()
        filtered = [r for r in self.records if r["ts"] >= cutoff]
        return self._aggregate(filtered)

    def get_recent_stats(self, hours: float = 5.0) -> dict:
        """Usage in the rolling N-hour window."""
        return self._aggregate(self._filter_window(hours))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _aggregate(self, records: list[dict]) -> dict:
        """Aggregate a list of records into summary stats."""
        input_tokens = sum(r.get("in", 0) for r in records)
        output_tokens = sum(r.get("out", 0) for r in records)
        cost = sum(r.get("cost", 0.0) for r in records)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "requests": len(records),
            "cost_usd": round(cost, 4),
        }

    def _filter_window(self, hours: float) -> list[dict]:
        """Return records within the last *hours* hours."""
        cutoff = time.time() - hours * 3600
        return [r for r in self.records if r["ts"] >= cutoff]

    def _load(self) -> None:
        """Load usage history from disk."""
        if not self.usage_file.exists():
            self.records = []
            return
        try:
            with open(self.usage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            self.records = []

    def _save(self) -> None:
        """Save usage history. Prune records older than 7 days."""
        cutoff = time.time() - 7 * 24 * 3600
        self.records = [r for r in self.records if r["ts"] >= cutoff]
        try:
            with open(self.usage_file, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Display helpers (used by CLI)
# ---------------------------------------------------------------------------

def format_tokens(n: int) -> str:
    """Format token count with comma separators."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def format_number(n: int) -> str:
    """Format a number with comma separators."""
    return f"{n:,}"
