"""Rules-only agent-memory MCP tools (OpenSearch Memory Tools names/params)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..authorship import reject_human_actors
from .store import FileMemoryStore

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE = Path(os.environ.get("CORE_MEMORY_DIR", ROOT / "data" / "agent-memory"))

mcp = FastMCP("core-agent-memory")
store = FileMemoryStore(DEFAULT_STORE)


@mcp.tool(name="SaveMemoryTool")
def save_memory_tool(
    memory: str,
    user_id: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
    tags: str | None = None,
    bot_name: str | None = None,
) -> str:
    """Save an exact statement to persistent memory. Rules-only — no LLM extraction.

    Authorship is grokbot/<bot name> via bot_name or agent_id. This tool refuses
    a human: actor, including human:whsutherland and case, whitespace, or unicode
    variants, and does not rewrite it. Billy attests only by editing markdown
    authoredBy to the exact string human:whsutherland.
    """
    reject_human_actors({"agent_id": agent_id, "bot_name": bot_name})
    rec = store.save(
        memory,
        bot_name=bot_name,
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
    )
    return json.dumps(rec.to_dict(), ensure_ascii=False)


@mcp.tool(name="SearchMemoryTool")
def search_memory_tool(
    query: str,
    user_id: str | None = None,
    agent_id: str | None = None,
    session_id: str | None = None,
    tags: str | None = None,
    size: int = 10,
) -> str:
    """Search memories with lexical matching. Use query '*' to list newest first."""
    hits = store.search(
        query,
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        tags=tags,
        size=size,
    )
    return json.dumps([h.to_dict() for h in hits], ensure_ascii=False)


@mcp.tool(name="DeleteMemoryTool")
def delete_memory_tool(memory_id: str) -> str:
    """Delete one memory by id from a prior SearchMemoryTool result."""
    ok = store.delete(memory_id)
    return json.dumps({"deleted": ok, "memory_id": memory_id})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
