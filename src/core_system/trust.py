"""Trust tiers — display and filter only, never access control."""

from __future__ import annotations

from . import TRUST_TIERS

# CSS / UI class per tier (look only)
TIER_LOOK = {
    "verified": "trust-verified",
    "attested": "trust-attested",
    "provisional": "trust-provisional",
    "agent-draft": "trust-agent-draft",
}


def normalize_tier(value: str | None, *, default: str = "provisional") -> str:
    tier = (value or default).strip().lower()
    if tier not in TRUST_TIERS:
        raise ValueError(f"unknown trust tier {value!r}; expected one of {TRUST_TIERS}")
    return tier


def look_class(tier: str | None) -> str:
    return TIER_LOOK[normalize_tier(tier)]


def filter_notes(notes: list[dict], *, min_tier: str | None = None, allow: set[str] | None = None) -> list[dict]:
    """Filter by tier for presentation. Does not enforce access."""
    if allow is not None:
        allowed = {normalize_tier(t) for t in allow}
        return [n for n in notes if normalize_tier(n.get("trustTier")) in allowed]
    if min_tier is None:
        return list(notes)
    order = {t: i for i, t in enumerate(TRUST_TIERS)}
    floor = order[normalize_tier(min_tier)]
    # verified is strongest (index 0); agent-draft weakest
    return [n for n in notes if order[normalize_tier(n.get("trustTier"))] <= floor]
