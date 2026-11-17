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

Only the exact string `human:whsutherland` is the human actor. That string is Billy (William Sutherland). A different case, extra whitespace, or a unicode lookalike is a different string and is not this identity.

### How Billy attests

Markdown is the source of truth. Billy attests a note by editing the file and setting:

```yaml
authoredBy: human:whsutherland
```

`is_human` is true only for that exact string. `normalize_authored_by` accepts that exact string when a non-agent caller checks an attestation. `SaveMemoryTool`, the memory store, and wiki seed/import do not accept it.

### Agent and MCP writes

`SaveMemoryTool` and `FileMemoryStore.save` stamp `grokbot/<bot name>` from `bot_name`, a `grokbot/` author, or a plain bot name in `agent_id`. Wiki seed and import stamp the same way.

An agent write raises `ValueError` when `agent_id`, `bot_name`, `authored_by`, or a note field named `author`, `generated.by`, or `verified-by` is a `human:` actor. The refused value includes `human:whsutherland` and case, whitespace, and unicode variants. The error text starts with `refusing to write human: actor` and says the write was not rewritten. The store file is left unchanged.

`user_id` is the memory subject, not the author. The statement text may name Billy. That does not set authorship.

## Trust tiers

Frontmatter `trustTier` values (`verified`, `attested`, `provisional`, `agent-draft`) affect display classes and filters only. They never gate reads or writes. Tiers stay meaningful because an agent cannot take Billy's actor identity.

## Memory MCP (rules-only)

```bash
python -m core_system.memory.mcp_server
```

Tools: `SaveMemoryTool`, `SearchMemoryTool`, `DeleteMemoryTool`. No LLM inference; agents write exact statements. Default store is file-backed under `data/agent-memory/`.

## Write-back

`CORE_WRITE_BACK=0` (default). The graph/RDF view is derived; Markdown remains master.
