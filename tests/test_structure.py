from gitskills.structure import STRUCTURE_VERSION, extract_structure, normalize_section_name


def test_normalize_section_name_removes_markup_and_collapses_space():
    assert normalize_section_name("  **Setup**   Guide  ") == "setup guide"


def test_extracts_headings_blocks_and_template_without_text_payload():
    content = "---\nname: x\ndescription: y\n---\n# Intro\n\nText.\n\n- one\n- two\n\n```python\nprint(1)\n```\n"
    row = extract_structure("sha", content, ["name", "description"])
    assert row["structure_version"] == STRUCTURE_VERSION
    assert row["n_headings"] == 1
    assert row["heading_names"] == ["intro"]
    assert row["n_bullet_lists"] == 1
    assert row["n_code_blocks"] == 1
    assert row["template_signature"]
    assert "Text." not in str(row)


def test_empty_and_symlink_statuses_are_explicit():
    empty = extract_structure("a", "", [], is_empty=True)
    link = extract_structure("b", "other/SKILL.md", [], is_symlink_like=True)
    assert empty["structure_status"] == "empty"
    assert link["structure_status"] == "symlink_like"


def test_counts_tables_quotes_and_nested_headings():
    content = "# A\n## A\n> quote\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\n---\n"
    row = extract_structure("sha", content, [])
    assert row["heading_levels"] == [1, 2]
    assert row["n_blockquotes"] == 1
    assert row["n_tables"] == 1
    assert row["n_thematic_breaks"] == 1


def test_counts_inline_code_children():
    row = extract_structure("sha", "Use `python` here.", [])
    assert row["n_inline_code"] == 1
