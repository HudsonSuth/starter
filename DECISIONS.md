# Locked decisions — Initial core system

Recorded 2026-11-16 (America/New_York). These are the product locks for v0.

| Decision | Lock |
|---|---|
| Base | OpenSearch-integrated agent-memory shape (rules-only Memory Tools style) |
| Source of truth | Markdown files are master; graph → file write-back is **off** |
| Formats | Vault-LD **and** OKF from day one |
| First wiki | Agent-generated, seeded from the demos |
| Trust tiers | Change how notes **look** and **filter** only — never access control |
| AI spend | Rules-only; **no paid AI calls** |
| Libraries | Vault-LD converter **and** a JSON-LD library (`PyLD`) both in |
| Authorship | Agents write as `grokbot/<bot name>`; only `human:whsutherland` counts as human |
| Deferred | Neo4j and KI until Neo4j version on Sutherland is confirmed |

## Neo4j note (not Sutherland)

This Cloud Agent VM cannot reach Sutherland. The only Neo4j pin visible in your
repos today is `neo4j:5.26.8` in `HudsonSuth/Graph-Engine-ETL` `abac/docker-compose.yml`
(and OntoSmith docs call for Neo4j 5.x). Confirm what Sutherland actually runs
before wiring Neo4j / KI.

## MVP slice (this branch)

1. New base layout in this repo  
2. Converter wired in (`vendor/vault-ld-scripts/`)  
3. Wiki import (Vault-LD demo + OKF demo)  
4. YAML-LD ↔ RDF round trip  
5. Agent-memory MCP tools (rules-only, file-backed; OpenSearch-shaped API)

Neo4j sync and KI stay out of this slice.
