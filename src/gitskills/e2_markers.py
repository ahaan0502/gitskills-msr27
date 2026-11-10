"""Versioned, double-anonymous authorship marker definitions for E2.

This module classifies transient normalized values and returns reason codes only;
it never stores or emits author names, email addresses, or commit messages.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


MARKER_SPEC_VERSION = "e2-marker-spec-v1"


@dataclass(frozen=True)
class MarkerRule:
    code: str
    family: str
    specificity: str
    pattern: re.Pattern[str]


def normalize_marker_text(value: object) -> str:
    """Normalize transient marker text without retaining the source value."""
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).casefold()
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _rules(family: str, patterns: tuple[tuple[str, str, str], ...]) -> tuple[MarkerRule, ...]:
    return tuple(
        MarkerRule(code, family, specificity, re.compile(pattern, re.IGNORECASE))
        for code, specificity, pattern in patterns
    )


IDENTITY_RULES = _rules("identity", (
    ("identity_bot_type", "high", r"\bbot\b"),
    ("identity_automation_token", "high", r"\b(?:automation|automated|ci|workflow)\b"),
    ("identity_agent_token", "medium", r"\b(?:agent|assistant|copilot|llm|model)\b"),
    ("identity_generated_account", "medium", r"\b(?:generated|generator|synthetic)\b"),
))

MESSAGE_RULES = _rules("message", (
    ("message_generated_by", "high", r"\b(?:generated|authored|created|written)\s+by\b"),
    ("message_agent_generated", "high", r"\b(?:agent|assistant|model|llm|ai)\s*[- ]?(?:generated|authored|created|written)\b"),
    ("message_automation", "medium", r"\b(?:automated|automation|bot|workflow|pipeline)\b"),
    ("message_coauthored_marker", "high", r"\bco[- ]?authored[- ]?by\b"),
))

CONTENT_RULES = _rules("content", (
    ("content_generated_by", "high", r"\b(?:generated|authored|created|written)\s+by\s+(?:an?\s+)?(?:agent|assistant|model|llm|ai|bot)\b"),
    ("content_agent_declaration", "high", r"\b(?:this|the)\s+(?:skill|file|document)\s+was\s+(?:generated|created|written)\s+by\b"),
    ("content_automation_declaration", "medium", r"\b(?:automatically|programmatically)\s+(?:generated|created|written)\b"),
))

WORKFLOW_RULES = _rules("workflow", (
    ("workflow_agent_generation", "medium", r"\b(?:agent|assistant|model|llm|ai)\b.{0,40}\b(?:generate|create|write|maintain)\b"),
    ("workflow_automation_generation", "medium", r"\b(?:automated|automation|bot)\b.{0,40}\b(?:generate|create|write|maintain)\b"),
))

RULES_BY_FAMILY = {
    "identity": IDENTITY_RULES,
    "message": MESSAGE_RULES,
    "content": CONTENT_RULES,
    "workflow": WORKFLOW_RULES,
}


def marker_matches(value: object, family: str) -> list[dict[str, str]]:
    """Return reason codes and specificity for transient text evidence."""
    if family not in RULES_BY_FAMILY:
        raise ValueError(f"unknown marker family: {family}")
    text = normalize_marker_text(value)
    return [
        {"reason_code": rule.code, "family": rule.family, "specificity": rule.specificity}
        for rule in RULES_BY_FAMILY[family]
        if rule.pattern.search(text)
    ]


def author_type_marker(value: object) -> dict[str, str] | None:
    """Classify dataset author-type metadata without exposing an identity."""
    normalized = normalize_marker_text(value)
    if normalized in {"bot", "programmaticaccessbot"}:
        return {"reason_code": "author_type_automated", "family": "identity", "specificity": "high"}
    if normalized in {"user", "organization", "mannequin"}:
        return {"reason_code": "author_type_non_automated", "family": "identity", "specificity": "low"}
    return None
