# Core system (MVP)

Markdown-first knowledge wiki with Vault-LD / OKF import, YAML-LD ↔ RDF round trip, and rules-only agent-memory MCP tools shaped like OpenSearch Memory Tools.

See [DECISIONS.md](DECISIONS.md) for the locked product choices.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make test
make roundtrip
```

## Layout

```
DECISIONS.md                 locked product choices
wiki/                        working vault (seeded from demos)
demos/vault-ld/              Vault-LD culinary example (upstream)
demos/okf-bundle/            minimal OKF-shaped bundle
vendor/vault-ld-scripts/     Vault-LD converter (Apache-2.0)
src/core_system/             YAML-LD, wiki import, trust, authorship, MCP memory
tests/                       unit + roundtrip smoke tests
```

## Authorship

- Human notes: `authoredBy: human:whsutherland`
- Agent notes: `authoredBy: grokbot/<bot name>`

## Trust tiers

Frontmatter `trustTier` values (`verified`, `attested`, `provisional`, `agent-draft`) affect display classes and filters only. They never gate reads or writes.

## Memory MCP (rules-only)

```bash
python -m core_system.memory.mcp_server
```

Tools: `SaveMemoryTool`, `SearchMemoryTool`, `DeleteMemoryTool`. No LLM inference; agents write exact statements. Default store is file-backed under `data/agent-memory/`.

## Write-back

`CORE_WRITE_BACK=0` (default). The graph/RDF view is derived; Markdown remains master.
