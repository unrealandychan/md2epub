import json
import os

DEFAULT_MANIFEST = {
    "title": "",
    "author": "",
    "language": "en-US",
    "toc": True,
    "cover_image": None,
    "css": None,
    "output_filename": "book.epub",
    "files": [],
}


def load_manifest(path: str) -> dict:
    """Load a book.json manifest from disk."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    manifest = dict(DEFAULT_MANIFEST)
    manifest.update(data)
    return manifest


def save_manifest(manifest: dict, path: str) -> None:
    """Save a manifest dict to disk as book.json."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
