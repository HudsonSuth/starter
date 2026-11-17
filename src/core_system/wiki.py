"""Wiki import: seed / refresh the working vault from Vault-LD and OKF demos."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

from . import AGENT_AUTHOR_PREFIX
from .authorship import (
    agent_author,
    is_agent,
    normalize_authored_by,
    reject_human_actor,
    reject_human_actors,
)
from .trust import normalize_tier
from .yaml_ld import join_note, split_note

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WIKI = ROOT / "wiki"
DEFAULT_VAULT_DEMO = ROOT / "demos" / "vault-ld"
DEFAULT_OKF_DEMO = ROOT / "demos" / "okf-bundle"

# Graph → Markdown write-back stays off for now (DECISIONS.md).
WRITE_BACK = False


def _assert_no_human_actors_in_markdown_tree(root: Path) -> None:
    """Refuse to copy notes whose actor fields already claim a human: identity."""
    if not root.exists():
        return
    for md in sorted(root.rglob("*.md")):
        meta, _body = split_note(md.read_text(encoding="utf-8"))
        try:
            reject_human_actors(meta)
        except ValueError as exc:
            raise ValueError(f"{exc} (in {md})") from exc


def _stamp_note(path: Path, *, authored_by: str, trust_tier: str, format_tag: str) -> None:
    text = path.read_text(encoding="utf-8")
    meta, body = split_note(text)
    reject_human_actors(meta)
    reject_human_actor(authored_by, field="authoredBy")
    stamped = normalize_authored_by(authored_by, allow_human=False)
    reject_human_actor(stamped, field="authoredBy")
    if not is_agent(stamped):
        raise ValueError(
            f"agent writes must carry {AGENT_AUTHOR_PREFIX}<bot name> (got {stamped!r})"
        )
    updated = dict(meta)
    updated["authoredBy"] = stamped
    updated["trustTier"] = normalize_tier(trust_tier)
    updated.setdefault("format", format_tag)
    reject_human_actors(updated)
    path.write_text(join_note(updated, body), encoding="utf-8")


def import_vault_ld(
    source: Path = DEFAULT_VAULT_DEMO,
    dest: Path = DEFAULT_WIKI,
    *,
    bot_name: str = "seed",
    trust_tier: str = "attested",
) -> Path:
    """Copy a Vault-LD vault into the working wiki and stamp authorship."""
    authored = agent_author(bot_name)
    reject_human_actor(authored, field="authoredBy")
    _assert_no_human_actors_in_markdown_tree(source)
    if dest.exists():
        for child in dest.iterdir():
            if child.name.startswith("."):
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        dest.mkdir(parents=True)

    for item in source.iterdir():
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    for md in dest.rglob("*.md"):
        _stamp_note(md, authored_by=authored, trust_tier=trust_tier, format_tag="vault-ld")
    return dest


def lift_okf_context() -> dict[str, Any]:
    """Appendix B style OKF lift: map bare `type` and give a default vocab."""
    return {
        "@context": {
            "@base": "https://example.org/okf/",
            "@vocab": "https://example.org/okf/vocab/",
            "type": "@type",
            "id": "@id",
        }
    }


def import_okf(
    source: Path = DEFAULT_OKF_DEMO,
    dest: Path | None = None,
    *,
    bot_name: str = "seed",
    trust_tier: str = "provisional",
) -> Path:
    """Import an OKF bundle into wiki/okf/ without rewriting producer files' meaning.

    Adds context.jsonld beside the copy (Vault-LD Appendix B lift).
    """
    authored = agent_author(bot_name)
    reject_human_actor(authored, field="authoredBy")
    _assert_no_human_actors_in_markdown_tree(source)
    dest = dest or (DEFAULT_WIKI / "okf")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    (dest / "context.jsonld").write_text(
        json.dumps(lift_okf_context(), indent=2) + "\n",
        encoding="utf-8",
    )
    for md in dest.rglob("*.md"):
        _stamp_note(md, authored_by=authored, trust_tier=trust_tier, format_tag="okf")
    return dest


def seed_wiki(*, bot_name: str = "seed") -> dict[str, Path]:
    """First wiki: agent-generated seed from the demos."""
    authored = agent_author(bot_name)
    vault = import_vault_ld(bot_name=bot_name, trust_tier="attested")
    okf = import_okf(bot_name=bot_name, trust_tier="provisional")
    index = DEFAULT_WIKI / "index.md"
    meta = {
        "type": "[[Wiki]]",
        "label": "Core wiki",
        "authoredBy": authored,
        "trustTier": "agent-draft",
        "format": "vault-ld",
    }
    reject_human_actors(meta)
    body = (
        "# Core wiki\n\n"
        "Agent-seeded from the Vault-LD culinary demo and the OKF sample bundle.\n\n"
        "- Vault-LD notes live at the wiki root (context.jsonld, Ontologies/, …).\n"
        "- OKF notes live under `okf/` with a lift context.\n"
        "- Markdown is master; graph write-back is off.\n"
    )
    index.write_text(join_note(meta, body), encoding="utf-8")
    return {"wiki": vault, "okf": okf, "index": index}


def list_notes(wiki: Path = DEFAULT_WIKI) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    for md in sorted(wiki.rglob("*.md")):
        meta, _ = split_note(md.read_text(encoding="utf-8"))
        notes.append(
            {
                "path": str(md.relative_to(wiki)),
                "trustTier": meta.get("trustTier"),
                "authoredBy": meta.get("authoredBy"),
                "format": meta.get("format"),
                "type": meta.get("type"),
            }
        )
    return notes


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Seed or list the working wiki")
    p.add_argument("command", choices=["seed", "list"])
    p.add_argument("--bot", default="seed")
    args = p.parse_args()
    if args.command == "seed":
        paths = seed_wiki(bot_name=args.bot)
        for k, v in paths.items():
            print(f"{k}: {v}")
    else:
        for n in list_notes():
            print(yaml.safe_dump(n, sort_keys=False).rstrip())
            print("---")


if __name__ == "__main__":
    main()
