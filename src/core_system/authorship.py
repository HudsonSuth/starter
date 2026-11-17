"""Who wrote what — agents vs the single human author."""

from __future__ import annotations

from . import AGENT_AUTHOR_PREFIX, HUMAN_AUTHOR


def agent_author(bot_name: str) -> str:
    name = (bot_name or "").strip().strip("/")
    if not name:
        raise ValueError("bot_name is required")
    return f"{AGENT_AUTHOR_PREFIX}{name}"


def is_human(authored_by: str | None) -> bool:
    return (authored_by or "").strip() == HUMAN_AUTHOR


def is_agent(authored_by: str | None) -> bool:
    return (authored_by or "").strip().startswith(AGENT_AUTHOR_PREFIX)


def normalize_authored_by(value: str | None, *, default_bot: str | None = None) -> str:
    raw = (value or "").strip()
    if not raw:
        if default_bot:
            return agent_author(default_bot)
        raise ValueError("authoredBy is required")
    if raw == HUMAN_AUTHOR or raw.startswith(AGENT_AUTHOR_PREFIX):
        return raw
    if raw.startswith("human:"):
        raise ValueError(f"only {HUMAN_AUTHOR} counts as human; got {raw!r}")
    # bare bot name → grokbot/<name>
    return agent_author(raw)
