"""Who wrote what — agents vs the single human author.

Billy (William Sutherland) is the only human actor. He attests by editing
markdown, which is the source of truth, and setting frontmatter ``authoredBy``
to the exact string ``human:whsutherland``. Case, whitespace, and unicode
lookalikes are not that identity.

``SaveMemoryTool``, the memory store, and wiki seed/import are agent write
paths. They stamp ``grokbot/<bot name>``. A ``human:`` actor in an author,
``generated.by``, ``verified-by``, ``agent_id``, or ``bot_name`` field is
refused with ``ValueError``. The caller's value is not rewritten into a
``grokbot/`` author and is not stored.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from typing import Any

from . import AGENT_AUTHOR_PREFIX, HUMAN_AUTHOR

# Colon characters that look like ":" but do not all fold under NFKC.
_COLON_LOOKALIKES = str.maketrans(
    {
        "\u2236": ":",  # RATIO
        "\u02d0": ":",  # MODIFIER LETTER TRIANGULAR COLON
        "\u02f8": ":",  # MODIFIER LETTER RAISED COLON
        "\u0589": ":",  # ARMENIAN FULL STOP
        "\u1361": ":",  # ETHIOPIC WORDSPACE
        "\u205a": ":",  # TWO DOT PUNCTUATION
        "\ua789": ":",  # MODIFIER LETTER COLON
        "\ufe13": ":",  # PRESENTATION FORM FOR VERTICAL COLON
        "\ufe55": ":",  # SMALL COLON
        "\uff1a": ":",  # FULLWIDTH COLON
    }
)

# Letters that still look like h/u/a after NFKC + casefold.
_HOMOGLYPHS = str.maketrans(
    {
        "\u04bb": "h",  # CYRILLIC SMALL LETTER SHHA
        "\u0430": "a",  # CYRILLIC SMALL LETTER A
        "\u0251": "a",  # LATIN SMALL LETTER ALPHA
        "\u03c5": "u",  # GREEK SMALL LETTER UPSILON
    }
)

# Key spellings of actor / provenance fields, after separator stripping.
_ACTOR_FIELD_KEYS = frozenset(
    {
        "author",
        "authors",
        "authoredby",
        "generatedby",
        "verifiedby",
        "agentid",
        "botname",
    }
)


def _canonical_actor(value: str) -> str:
    """Fold case, whitespace, and unicode tricks for detection only.

    The result is never written back. Storing it would turn a spoof into
    Billy's exact identity.
    """
    text = unicodedata.normalize("NFKC", value)
    text = "".join(
        ch for ch in text if unicodedata.category(ch) != "Cf" and not ch.isspace()
    )
    return text.casefold().translate(_COLON_LOOKALIKES).translate(_HOMOGLYPHS)


def is_human_actor_claim(value: str | None) -> bool:
    """True when ``value`` is a ``human:`` actor, including spoofed spellings.

    Broader than :func:`is_human`. The exact human identity is a claim too:
    agent write paths refuse it. Only :func:`is_human` treats the exact
    spelling as Billy.
    """
    if not isinstance(value, str) or not value:
        return False
    return _canonical_actor(value).startswith("human:")


def is_human(authored_by: str | None) -> bool:
    """True only for Billy's exact actor string. Variants are not human."""
    return authored_by == HUMAN_AUTHOR


def is_agent(authored_by: str | None) -> bool:
    return (authored_by or "").strip().startswith(AGENT_AUTHOR_PREFIX)


def _human_actor_refusal(value: str, *, field: str) -> ValueError:
    return ValueError(
        "refusing to write human: actor "
        f"in {field} (got {value!r}); the write was not rewritten. "
        "Agent and MCP callers cannot claim a human: identity. "
        f"Agent writes must carry {AGENT_AUTHOR_PREFIX}<bot name>. "
        f"Only the exact identity {HUMAN_AUTHOR} is human; "
        "Billy attests by setting that exact authoredBy string in markdown, "
        "not through a tool."
    )


def reject_human_actor(value: str | None, *, field: str) -> None:
    """Refuse a ``human:`` actor. Does not rewrite the value into ``grokbot/``."""
    if isinstance(value, str) and is_human_actor_claim(value):
        raise _human_actor_refusal(value, field=field)


def _norm_actor_key(key: object) -> str:
    text = unicodedata.normalize("NFKC", str(key)).casefold()
    text = "".join(
        ch for ch in text if not ch.isspace() and unicodedata.category(ch) != "Cf"
    )
    return text.replace(".", "").replace("_", "").replace("-", "")


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        found: list[str] = []
        for item in value.values():
            found.extend(_iter_strings(item))
        return found
    if isinstance(value, (list, tuple)):
        found = []
        for item in value:
            found.extend(_iter_strings(item))
        return found
    return []


def reject_human_actors(fields: Mapping[str, Any]) -> None:
    """Refuse ``human:`` values on author, generated.by, verified-by, and actor ids.

    Nested mappings are scanned so a buried ``generated.by`` is not a bypass.
    Labels, prose, and memory text are not actor fields and are left alone.
    """
    for key, value in fields.items():
        if _norm_actor_key(key) in _ACTOR_FIELD_KEYS:
            for text in _iter_strings(value):
                reject_human_actor(text, field=str(key))
        elif isinstance(value, Mapping):
            reject_human_actors(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    reject_human_actors(item)


def agent_author(bot_name: str) -> str:
    reject_human_actor(bot_name, field="bot_name")
    name = (bot_name or "").strip().strip("/")
    if not name:
        raise ValueError("bot_name is required")
    reject_human_actor(name, field="bot_name")
    return f"{AGENT_AUTHOR_PREFIX}{name}"


def normalize_authored_by(
    value: str | None,
    *,
    default_bot: str | None = None,
    allow_human: bool = True,
) -> str:
    """Normalize an author string.

    ``allow_human=True`` accepts only the exact identity
    ``human:whsutherland``. That is the non-agent check for Billy's markdown
    attestation. It is not an MCP tool. Agent write paths pass
    ``allow_human=False``. Every other ``human:`` spelling is refused on both
    paths. Nothing is rewritten to ``grokbot/``.
    """
    if allow_human and value == HUMAN_AUTHOR:
        return HUMAN_AUTHOR
    if isinstance(value, str) and is_human_actor_claim(value):
        raise _human_actor_refusal(value, field="authoredBy")
    raw = (value or "").strip()
    if not raw:
        if default_bot:
            return agent_author(default_bot)
        raise ValueError("authoredBy is required")
    if is_human_actor_claim(raw) or raw.startswith("human:"):
        raise _human_actor_refusal(raw, field="authoredBy")
    if raw.startswith(AGENT_AUTHOR_PREFIX):
        return raw
    return agent_author(raw)
