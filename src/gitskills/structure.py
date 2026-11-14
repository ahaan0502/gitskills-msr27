"""Versioned, anonymized structural features for E3."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from markdown_it import MarkdownIt
from gitskills.parse import _FM_RAW_RE, _normalize, _split_frontmatter

STRUCTURE_VERSION = "e3-structure-v1"
_MD = MarkdownIt("commonmark").enable("table")


def normalize_section_name(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:200]


def _frontmatter_keys(fm_keys: object) -> list[str]:
    if not isinstance(fm_keys, (list, tuple)):
        return []
    return sorted({str(x).casefold().strip() for x in fm_keys if str(x).strip()})


def extract_structure(
    file_sha: str,
    content: str | None,
    fm_keys: object,
    parse_error: str | None = None,
    is_empty: bool = False,
    is_symlink_like: bool = False,
    cohort: str = "other_or_undated",
    location_class: str = "unknown",
    catalog_flag: bool = False,
    template_flag: bool = False,
    bulk_repo_flag: bool = False,
    repo_rank: int | None = None,
) -> dict[str, Any]:
    """Return structural features without retaining source text."""
    keys = _frontmatter_keys(fm_keys)
    rec: dict[str, Any] = {
        "file_sha": file_sha,
        "structure_version": STRUCTURE_VERSION,
        "cohort": cohort,
        "location_class": location_class,
        "catalog_flag": bool(catalog_flag),
        "template_flag": bool(template_flag),
        "bulk_repo_flag": bool(bulk_repo_flag),
        "repo_rank": repo_rank,
        "structure_status": "ok",
        "parse_error_present": bool(parse_error),
        "is_empty": bool(is_empty),
        "is_symlink_like": bool(is_symlink_like),
        "frontmatter_key_count": len(keys),
        "frontmatter_keys": keys,
        "has_name_key": "name" in keys,
        "has_description_key": "description" in keys,
        "body_chars": 0,
        "body_words": 0,
        "body_lines": 0,
        "n_paragraphs": 0,
        "n_headings": 0,
        "heading_levels": [],
        "heading_names": [],
        "max_heading_depth": 0,
        "n_bullet_lists": 0,
        "n_ordered_lists": 0,
        "n_blockquotes": 0,
        "n_tables": 0,
        "n_code_blocks": 0,
        "n_inline_code": 0,
        "n_thematic_breaks": 0,
        "block_sequence": [],
        "template_signature": None,
    }
    if not content or is_empty or is_symlink_like:
        rec["structure_status"] = "empty" if is_empty or not content else "symlink_like"
        return rec
    raw_match = _FM_RAW_RE.match(content)
    original_body_crs = raw_match.group(2).count("\r") if raw_match else content.count("\r")
    _, body = _split_frontmatter(_normalize(content))
    rec["body_chars"] = len(body) + original_body_crs
    rec["body_words"] = len(body.split())
    rec["body_lines"] = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if parse_error:
        rec["structure_status"] = "parser_error_present"
    try:
        tokens = _MD.parse(body)
    except Exception:
        rec["structure_status"] = "markdown_error"
        return rec
    block_sequence: list[str] = []
    for i, token in enumerate(tokens):
        token_type = token.type
        if token.children:
            rec["n_inline_code"] += sum(child.type == "code_inline" for child in token.children)
        if token_type == "heading_open":
            level = int(token.tag[1])
            title = tokens[i + 1].content if i + 1 < len(tokens) and tokens[i + 1].type == "inline" else ""
            rec["heading_levels"].append(level)
            rec["heading_names"].append(normalize_section_name(title))
            rec["n_headings"] += 1
            rec["max_heading_depth"] = max(rec["max_heading_depth"], level)
            block_sequence.append(f"h{level}")
        elif token_type == "paragraph_open":
            rec["n_paragraphs"] += 1
            block_sequence.append("paragraph")
        elif token_type == "bullet_list_open":
            rec["n_bullet_lists"] += 1
            block_sequence.append("bullet_list")
        elif token_type == "ordered_list_open":
            rec["n_ordered_lists"] += 1
            block_sequence.append("ordered_list")
        elif token_type == "blockquote_open":
            rec["n_blockquotes"] += 1
            block_sequence.append("blockquote")
        elif token_type == "table_open":
            rec["n_tables"] += 1
            block_sequence.append("table")
        elif token_type in ("fence", "code_block"):
            rec["n_code_blocks"] += 1
            block_sequence.append("code")
        elif token_type == "hr":
            rec["n_thematic_breaks"] += 1
            block_sequence.append("thematic_break")
    rec["block_sequence"] = block_sequence
    template_payload = {
        "frontmatter_keys": keys,
        "heading_levels": rec["heading_levels"],
        "block_sequence": block_sequence,
        "n_bullet_lists": rec["n_bullet_lists"],
        "n_ordered_lists": rec["n_ordered_lists"],
        "n_blockquotes": rec["n_blockquotes"],
        "n_tables": rec["n_tables"],
        "n_code_blocks": rec["n_code_blocks"],
        "n_inline_code": rec["n_inline_code"],
    }
    rec["template_signature"] = hashlib.sha256(
        json.dumps(template_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return rec
