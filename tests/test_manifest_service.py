import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.manifest_service import load_manifest, save_manifest, DEFAULT_MANIFEST


def test_load_manifest_valid(tmp_path):
    data = {"title": "My Book", "author": "Alice"}
    manifest_file = tmp_path / "book.json"
    manifest_file.write_text(json.dumps(data))
    result = load_manifest(str(manifest_file))
    assert result["title"] == "My Book"
    assert result["author"] == "Alice"
    # Should include defaults too
    assert "language" in result


def test_save_manifest(tmp_path):
    manifest = {"title": "Test", "author": "Bob", "files": ["ch1.md"]}
    path = str(tmp_path / "book.json")
    save_manifest(manifest, path)
    with open(path, "r") as f:
        loaded = json.load(f)
    assert loaded["title"] == "Test"
    assert loaded["files"] == ["ch1.md"]


def test_default_manifest_keys():
    expected_keys = {"title", "author", "language", "toc", "cover_image", "css", "output_filename", "files"}
    assert expected_keys.issubset(set(DEFAULT_MANIFEST.keys()))
