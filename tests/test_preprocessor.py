import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.preprocessor import strip_shortcodes, _extract_frontmatter, preprocess_file, _renumber_footnotes


def test_strip_shortcodes_removes_tags():
    text = "Before {{< callout type=\"warning\" >}} middle {{< /callout >}} after"
    result = strip_shortcodes(text)
    assert "{{<" not in result
    assert ">}}" not in result
    assert "before" in result.lower()
    assert "after" in result.lower()


def test_extract_frontmatter_extracts_title():
    text = "---\ntitle: My Chapter\nweight: 1\n---\nSome content here."
    title, body = _extract_frontmatter(text)
    assert title == "My Chapter"
    assert "---" not in body
    assert "weight" not in body
    assert "Some content here." in body


def test_extract_frontmatter_no_frontmatter():
    text = "No frontmatter here."
    title, body = _extract_frontmatter(text)
    assert title is None
    assert body == text


def test_preprocess_file_creates_temp_with_h1(tmp_path):
    src = tmp_path / "chapter.md"
    src.write_text("---\ntitle: Hello World\n---\nContent goes here.")
    tmp_dir = str(tmp_path / "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    result = preprocess_file(str(src), tmp_dir, 0)
    assert os.path.isfile(result)
    content = open(result).read()
    assert "# Hello World" in content
    assert "Content goes here." in content


def test_renumber_footnotes():
    text = "See [^1] and [^note].\n\n[^1]: First footnote.\n[^note]: Another."
    result = _renumber_footnotes(text, "ch0001")
    assert "[^ch0001_1]" in result
    assert "[^ch0001_note]" in result
    assert "[^1]" not in result
