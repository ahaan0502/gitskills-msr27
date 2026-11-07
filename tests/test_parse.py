from gitskills.parse import norm_hash, parse_skill

BASIC = """---
name: pdf-tools
description: Work with PDF files. Use when the user mentions PDFs.
license: MIT
---

# PDF Tools

Use this skill to read PDFs.

## Steps

1. Run the script.

```bash
# not a heading
python extract.py
```

## Notes

Done.
"""


def test_basic_frontmatter_and_structure():
    r = parse_skill(BASIC)
    assert r["frontmatter_valid"] and r["has_frontmatter"]
    assert r["fm_name"] == "pdf-tools"
    assert r["fm_description"].startswith("Work with PDF")
    assert r["fm_keys"] == ["description", "license", "name"]
    assert r["heading_levels"] == [1, 2, 2]
    assert r["headings"] == ["PDF Tools", "Steps", "Notes"]
    assert r["n_code_blocks"] == 1
    assert r["code_langs"] == ["bash"]


def test_hash_inside_code_fence_is_not_a_heading():
    r = parse_skill(BASIC)
    assert "not a heading" not in r["headings"]
    assert "not a heading" not in r["body_prose"]


def test_prose_excludes_code_and_headings():
    r = parse_skill(BASIC)
    assert "python extract.py" not in r["body_prose"]
    assert "Use this skill to read PDFs." in r["body_prose"]
    assert "PDF Tools" not in r["body_prose"]


def test_no_frontmatter():
    r = parse_skill("# Just a body\n\nHello.\n")
    assert not r["has_frontmatter"] and not r["frontmatter_valid"]
    assert r["n_headings"] == 1


def test_broken_yaml_reported_not_raised():
    r = parse_skill("---\nname: [unclosed\n---\nBody\n")
    assert r["has_frontmatter"] and not r["frontmatter_valid"]
    assert r["parse_error"] == "frontmatter_yaml_error"
    assert r["body_chars"] > 0


def test_frontmatter_not_mapping():
    r = parse_skill("---\n- a\n- b\n---\nBody\n")
    assert r["parse_error"] == "frontmatter_not_a_mapping"


def test_crlf_and_bom():
    r = parse_skill("﻿" + BASIC.replace("\n", "\r\n"))
    assert r["frontmatter_valid"] and r["fm_name"] == "pdf-tools"
    assert r["n_code_blocks"] == 1


def test_setext_headings():
    r = parse_skill("Title\n=====\n\nSub\n---\n\ntext\n")
    assert r["heading_levels"] == [1, 2]


def test_empty_and_none():
    assert parse_skill("")["is_empty"]
    assert parse_skill("   \n\n")["is_empty"]
    assert parse_skill(None)["is_empty"]


def test_symlink_like():
    r = parse_skill("../../shared/skills/foo/SKILL.md")
    assert r["is_symlink_like"]


def test_description_multiline_yaml():
    r = parse_skill("---\nname: x\ndescription: >\n  line one\n  line two\n---\nbody\n")
    assert r["fm_description"].strip() == "line one line two"


def test_norm_hash_ignores_whitespace_and_case():
    assert norm_hash("Hello   World\n") == norm_hash("hello world")


def test_never_raises_on_binary_ish():
    r = parse_skill("\x00\x01\x02 weird ```` ``` \n---\n")
    assert isinstance(r, dict)
