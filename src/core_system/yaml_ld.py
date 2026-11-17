"""YAML-LD frontmatter helpers: wiki-link resolution + JSON-LD expand/compact via PyLD."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from pyld import jsonld

WIKI_LINK_RE = re.compile(r"^\[\[(.+?)\]\]$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def split_note(text: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return meta, m.group(2)


def join_note(meta: dict[str, Any], body: str) -> str:
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).rstrip()
    body = body or ""
    if body and not body.startswith("\n"):
        return f"---\n{dumped}\n---\n{body}"
    return f"---\n{dumped}\n---\n{body}"


def _wiki_target(value: str) -> str | None:
    m = WIKI_LINK_RE.match(value.strip())
    if not m:
        return None
    inner = m.group(1)
    # drop alias and fragment; keep final path segment for identity
    inner = inner.split("|", 1)[0].split("#", 1)[0].strip()
    if "/" in inner:
        inner = inner.rsplit("/", 1)[-1]
    return inner


def resolve_wiki_links(obj: Any, *, base: str) -> Any:
    """Rewrite [[Note]] strings to absolute IRIs under base (Vault-LD §4.4.1)."""
    if isinstance(obj, str):
        target = _wiki_target(obj)
        if target is None:
            return obj
        return f"{base.rstrip('/')}/{target}"
    if isinstance(obj, list):
        return [resolve_wiki_links(x, base=base) for x in obj]
    if isinstance(obj, dict):
        return {k: resolve_wiki_links(v, base=base) for k, v in obj.items()}
    return obj


def load_context(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def expand_frontmatter(
    meta: dict[str, Any],
    *,
    context: Any,
    base: str,
    subject_iri: str | None = None,
) -> list[dict[str, Any]]:
    doc = resolve_wiki_links(dict(meta), base=base)
    if subject_iri:
        doc["@id"] = subject_iri
    doc["@context"] = context.get("@context", context) if isinstance(context, dict) else context
    return jsonld.expand(doc, {"base": base})


def compact_frontmatter(expanded: list[dict[str, Any]], *, context: Any, base: str) -> dict[str, Any]:
    ctx = context.get("@context", context) if isinstance(context, dict) else context
    return jsonld.compact(expanded, ctx, {"base": base})


def note_to_expanded(path: Path, *, context_path: Path, base: str) -> list[dict[str, Any]]:
    meta, _body = split_note(path.read_text(encoding="utf-8"))
    context = load_context(context_path)
    subject = f"{base.rstrip('/')}/{path.stem}"
    return expand_frontmatter(meta, context=context, base=base, subject_iri=subject)


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Expand a note's YAML-LD frontmatter with PyLD")
    p.add_argument("note", type=Path)
    p.add_argument("--context", type=Path, required=True)
    p.add_argument("--base", default="https://example.org/")
    args = p.parse_args()
    expanded = note_to_expanded(args.note, context_path=args.context, base=args.base)
    print(json.dumps(expanded, indent=2))


if __name__ == "__main__":
    main()
