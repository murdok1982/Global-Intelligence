"""
State-grade classification, handling caveats and source-rating taxonomy.

This module defines the canonical taxonomy used everywhere a piece of
intelligence, a user, an agent, or an LLM provider needs to be tagged
with a clearance, a sharing caveat or a source rating.

Levels (ClassificationLevel) follow a coarse public-sector convention:
PUBLIC (0) is freely shareable, RESTRICTED (1) is OUO/FOUO-equivalent,
CONFIDENTIAL (2) and SECRET (3) require strict handling and local-only
processing. TOP_SECRET is intentionally NOT modeled here because it
demands physically isolated infrastructure that is out of scope.

Handling caveats follow the FIRST Traffic Light Protocol v2.0 (TLP).
Source rating follows the NATO Admiralty (STANAG 2511) scale, with
the reliability axis (A-F) and the credibility axis (1-6) separated.

NOTE: This taxonomy is a software-level enforcement aid, NOT a legal
certification. The system is designed to support compliance with the
Spanish Esquema Nacional de Seguridad (ENS), ISO/IEC 27001 and
NIST SP 800-53, but those certifications require additional
organizational controls outside this codebase.
"""

from __future__ import annotations

from enum import Enum, IntEnum
from typing import Any


class ClassificationLevel(IntEnum):
    """Hierarchical clearance / classification level.

    Integer ordering is meaningful: a user with clearance X may
    access items whose classification is <= X.
    """

    PUBLIC = 0
    RESTRICTED = 1  # OUO / FOUO equivalent
    CONFIDENTIAL = 2
    SECRET = 3
    # TOP_SECRET intentionally not modeled — requires isolated infra.

    @classmethod
    def from_any(cls, value: Any) -> "ClassificationLevel":
        """Coerce a string, int or enum into a ClassificationLevel."""
        if isinstance(value, cls):
            return value
        if isinstance(value, int):
            return cls(value)
        if isinstance(value, str):
            key = value.strip().upper()
            if key.isdigit():
                return cls(int(key))
            return cls[key]
        raise TypeError(f"Cannot coerce {value!r} to ClassificationLevel")


class TLP(str, Enum):
    """FIRST Traffic Light Protocol v2.0 handling caveats."""

    CLEAR = "TLP:CLEAR"  # Fully public, no handling restrictions.
    GREEN = "TLP:GREEN"  # Community-wide, not public.
    AMBER = "TLP:AMBER"  # Organization-wide, on need-to-know basis.
    AMBER_STRICT = "TLP:AMBER+STRICT"  # Restricted to the recipient organization.
    RED = "TLP:RED"  # Named recipients only.


class AdmiraltyReliability(str, Enum):
    """NATO Admiralty Code — source reliability (STANAG 2511)."""

    A = "A"  # Completely reliable
    B = "B"  # Usually reliable
    C = "C"  # Fairly reliable
    D = "D"  # Not usually reliable
    E = "E"  # Unreliable
    F = "F"  # Reliability cannot be judged


class AdmiraltyCredibility(IntEnum):
    """NATO Admiralty Code — information credibility (STANAG 2511)."""

    ONE = 1  # Confirmed by other sources
    TWO = 2  # Probably true
    THREE = 3  # Possibly true
    FOUR = 4  # Doubtful
    FIVE = 5  # Improbable
    SIX = 6  # Truth cannot be judged


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def can_user_access(
    user_clearance: ClassificationLevel,
    item_classification: ClassificationLevel,
) -> bool:
    """Return True when the user clearance dominates the item's classification.

    Both arguments are coerced through ``ClassificationLevel.from_any``.
    """
    u = ClassificationLevel.from_any(user_clearance)
    i = ClassificationLevel.from_any(item_classification)
    return u >= i


REDACTED_PLACEHOLDER = "[REDACTED — INSUFFICIENT CLEARANCE]"


def redact_for_clearance(
    item: Any,
    user_clearance: ClassificationLevel,
    *,
    classification_attr: str = "classification",
    redactable_fields: tuple[str, ...] = (
        "content",
        "executive_summary",
        "content_json",
        "content_markdown",
        "output_markdown",
        "description",
    ),
) -> Any:
    """Return either the original item or a redacted copy.

    The function inspects ``item.<classification_attr>`` and, if the
    user does not have sufficient clearance, scrubs every field listed
    in ``redactable_fields`` with ``REDACTED_PLACEHOLDER``. Non-string
    fields and missing attributes are silently skipped.

    The function does NOT mutate the input — it returns a shallow copy
    when redaction is needed, or the original object otherwise.

    Mappings, ORM objects and Pydantic models are all supported.
    """
    item_classification = _read_attr(item, classification_attr, ClassificationLevel.PUBLIC)
    if can_user_access(user_clearance, item_classification):
        return item

    # Need to redact — make a best-effort copy and overwrite fields.
    if isinstance(item, dict):
        out = dict(item)
        for field in redactable_fields:
            if field in out and isinstance(out[field], str):
                out[field] = REDACTED_PLACEHOLDER
        out["_redacted"] = True
        return out

    # For ORM / pydantic / plain objects: build a dict snapshot so we do not
    # mutate the underlying SQLAlchemy row.
    snapshot: dict[str, Any] = {}
    for field in redactable_fields:
        if hasattr(item, field):
            value = getattr(item, field)
            snapshot[field] = REDACTED_PLACEHOLDER if isinstance(value, str) else value
    snapshot[classification_attr] = item_classification
    snapshot["_redacted"] = True
    return snapshot


def _read_attr(item: Any, attr: str, default: Any) -> Any:
    if isinstance(item, dict):
        return item.get(attr, default)
    return getattr(item, attr, default)


__all__ = [
    "ClassificationLevel",
    "TLP",
    "AdmiraltyReliability",
    "AdmiraltyCredibility",
    "can_user_access",
    "redact_for_clearance",
    "REDACTED_PLACEHOLDER",
]
