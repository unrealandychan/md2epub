import os
import sys
import zipfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.zip_importer import extract_zip, inspect_contents


def test_extract_zip(tmp_path):
    # Create a zip with some files
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(str(zip_path), "w") as zf:
        zf.writestr("chapter1.md", "# Chapter 1\nContent.")
        zf.writestr("chapter2.md", "# Chapter 2\nMore content.")

    extract_dir = str(tmp_path / "extracted")
    result = extract_zip(str(zip_path), extract_dir)
    assert os.path.isdir(result)
    assert os.path.isfile(os.path.join(extract_dir, "chapter1.md"))
    assert os.path.isfile(os.path.join(extract_dir, "chapter2.md"))


def test_inspect_contents_categorises(tmp_path):
    # Create files in a directory
    (tmp_path / "intro.md").write_text("# Intro")
    (tmp_path / "chapter.md").write_text("# Chapter")
    (tmp_path / "cover.jpg").write_bytes(b"\xff\xd8\xff")  # fake JPEG
    (tmp_path / "epub.css").write_text("body { font-family: serif; }")
    (tmp_path / "book.json").write_text('{"title": "Test"}')

    result = inspect_contents(str(tmp_path))
    md_names = [os.path.basename(f) for f in result["md_files"]]
    assert "intro.md" in md_names
    assert "chapter.md" in md_names
    assert result["cover"] is not None
    assert "cover.jpg" in result["cover"]
    assert result["css"] is not None
    assert "epub.css" in result["css"]
    assert result["manifest"] is not None
    assert "book.json" in result["manifest"]
