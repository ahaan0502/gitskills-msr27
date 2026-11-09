"""Pure SKILL.md parser: content -> flat record. No I/O, no globals, deterministic.

Splits YAML front matter from the Markdown body, then extracts headings, fenced code
blocks and a prose-only view of the body (code removed). Never raises on bad input:
failures are reported in `parse_error` so they can be tallied in the E0 report.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

import yaml
from markdown_it import MarkdownIt

_MD = MarkdownIt("commonmark").enable("table")

# Front matter must start at byte 0 (after optional BOM) with a '---' line.
_FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n-{3,}[ \t]*(?:\n|\Z)", re.DOTALL)
_FM_RAW_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n-{3,}[ \t]*(?:\r?\n|\Z)(.*)\Z", re.DOTALL)
_FM_FIELD_RE = re.compile(r"(?m)^(name|description)[ \t]*:[ \t]*([^\r\n]*)[ \t]*$")

_YamlLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _normalize(text: str) -> str:
    if text.startswith("﻿"):
        text = text[1:]
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    m = _FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _set_spec_valid(rec: dict[str, Any]) -> None:
    rec["spec_valid"] = bool(
        isinstance(rec["fm_name"], str)
        and rec["fm_name"].strip()
        and isinstance(rec["fm_description"], str)
        and rec["fm_description"].strip()
    )


def _recover_frontmatter_fields(raw: str, rec: dict[str, Any]) -> None:
    for match in _FM_FIELD_RE.finditer(raw):
        value = match.group(2).strip()
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        rec[f"fm_{match.group(1)}"] = value or None


def norm_hash(body: str) -> str:
    """Hash of the body with whitespace collapsed and case folded.

    Used to collapse near-exact copies (differing only in spacing or case).
    """
    collapsed = re.sub(r"\s+", " ", body).strip().lower()
    return hashlib.sha1(collapsed.encode("utf-8")).hexdigest()


def parse_skill(content: str | None) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "is_empty": False,
        "is_symlink_like": False,
        "has_frontmatter": False,
        "frontmatter_valid": False,
        "spec_valid": False,
        "fm_recovered": False,
        "fm_keys": [],
        "fm_name": None,
        "fm_description": None,
        "body_chars": 0,
        "body_lines": 0,
        "body_words": 0,
        "n_headings": 0,
        "heading_levels": [],
        "headings": [],
        "n_code_blocks": 0,
        "code_langs": [],
        "code_chars": 0,
        "body_prose": "",
        "norm_hash": None,
        "parse_error": None,
    }

    if content is None or not content.strip():
        rec["is_empty"] = True
        return rec

    # Keep parsing normalized, but retain CR characters in the published body length.
    # The dataset's body_chars is measured on the original body, including CRLF bytes.
    raw_match = _FM_RAW_RE.match(content)
    original_body_crs = raw_match.group(2).count("\r") if raw_match else content.count("\r")
    text = _normalize(content)

    # Symlink skills store the link target path as their whole content.
    stripped = text.strip()
    if "\n" not in stripped and len(stripped) < 300 and re.fullmatch(r"[\w./\\@~-]+", stripped) \
            and ("/" in stripped or stripped.endswith(".md")):
        rec["is_symlink_like"] = True
        return rec

    fm_raw, body = _split_frontmatter(text)
    if fm_raw is not None:
        rec["has_frontmatter"] = True
        try:
            data = yaml.load(fm_raw, Loader=_YamlLoader)
            if isinstance(data, dict):
                rec["frontmatter_valid"] = True
                rec["fm_keys"] = sorted(str(k) for k in data.keys())
                name, desc = data.get("name"), data.get("description")
                rec["fm_name"] = None if name is None else str(name)
                rec["fm_description"] = None if desc is None else str(desc)
                _set_spec_valid(rec)
            else:
                rec["parse_error"] = "frontmatter_not_a_mapping"
        except yaml.YAMLError:
            rec["parse_error"] = "frontmatter_yaml_error"
            rec["fm_recovered"] = True
            _recover_frontmatter_fields(fm_raw, rec)

    rec["body_chars"] = len(body) + original_body_crs
    rec["body_lines"] = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    rec["body_words"] = len(body.split())
    rec["norm_hash"] = norm_hash(body)

    try:
        tokens = _MD.parse(body)
    except Exception as exc:  # defensive: markdown-it should not raise
        rec["parse_error"] = rec["parse_error"] or f"markdown_error:{type(exc).__name__}"
        rec["body_prose"] = body
        return rec

    prose_parts: list[str] = []
    in_heading = False
    for i, tok in enumerate(tokens):
        if tok.type == "heading_open":
            in_heading = True
            level = int(tok.tag[1])
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            title = nxt.content.strip() if nxt is not None and nxt.type == "inline" else ""
            rec["heading_levels"].append(level)
            rec["headings"].append(title)
        elif tok.type == "heading_close":
            in_heading = False
        elif tok.type in ("fence", "code_block"):
            rec["n_code_blocks"] += 1
            rec["code_chars"] += len(tok.content)
            if tok.type == "fence":
                lang = (tok.info or "").strip().split(" ")[0].lower()
                rec["code_langs"].append(lang)
        elif tok.type == "inline" and not in_heading:
            prose_parts.append(tok.content)

    rec["n_headings"] = len(rec["headings"])
    rec["body_prose"] = "\n".join(prose_parts)
    return rec
