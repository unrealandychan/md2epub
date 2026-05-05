import os
import zipfile

SUPPORTED_MD = {".md", ".markdown"}
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".gif"}
SUPPORTED_CSS = {".css"}
MANIFEST_NAME = "book.json"


def extract_zip(zip_path: str, extract_dir: str) -> str:
    """Extract a ZIP archive to extract_dir. Returns the extract directory."""
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Prevent path traversal: only extract safe members
        for member in zf.infolist():
            member_path = os.path.realpath(
                os.path.join(extract_dir, member.filename)
            )
            if not member_path.startswith(os.path.realpath(extract_dir) + os.sep):
                continue
            zf.extract(member, extract_dir)
    return extract_dir


def inspect_contents(extract_dir: str) -> dict:
    """Walk extract_dir and categorise files into md, cover, css, manifest."""
    md_files = []
    cover = None
    css = None
    manifest = None

    for root, dirs, files in os.walk(extract_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            fpath = os.path.join(root, fname)
            ext = os.path.splitext(fname)[1].lower()
            name_lower = fname.lower()

            if ext in SUPPORTED_MD:
                md_files.append(fpath)
            elif name_lower == MANIFEST_NAME and manifest is None:
                manifest = fpath
            elif name_lower in ("cover.jpg", "cover.jpeg", "cover.png") and cover is None:
                cover = fpath
            elif ext in SUPPORTED_IMAGES and cover is None and "cover" in name_lower:
                cover = fpath
            elif name_lower == "epub.css" and css is None:
                css = fpath
            elif ext in SUPPORTED_CSS and css is None:
                css = fpath

    return {
        "md_files": md_files,
        "cover": cover,
        "css": css,
        "manifest": manifest,
        "extract_dir": extract_dir,
    }
