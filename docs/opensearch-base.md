# OpenSearch-integrated base

The agent-memory MCP tools in this repo follow the **OpenSearch Memory Tools**
shape (`SaveMemoryTool`, `SearchMemoryTool`, `DeleteMemoryTool`):

- Rules-only: the agent writes exact statements
- No paid AI / no server-side LLM inference (`infer` stays unused)
- Authorship stamped as `grokbot/<bot>`

Default storage is file-backed (`data/agent-memory/`) so the MVP runs without a
cluster. Point `CORE_MEMORY_DIR` at a shared path, or later swap the store for
Amazon OpenSearch / OpenSearch 2.19+ with `MEMORY_TOOLS_ENABLED=true` on
`opensearch-mcp-server-py` when Sutherland wiring is ready.

Agentic Memory (`agentic_memory` category, OpenSearch 3.3+) is **not** enabled:
it is the paid/LLM extraction path we locked out for v0.
