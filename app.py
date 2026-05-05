import json
import os
import shutil
import uuid

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

from modules import (
    file_loader,
    manifest_service,
    pandoc_service,
    validation_service,
    zip_importer,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
DIST_DIR = os.path.join(BASE_DIR, "dist")

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(DIST_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB

ALLOWED_MD = {".md", ".markdown"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".gif"}
ALLOWED_CSS = {".css"}
ALLOWED_ZIP = {".zip"}
ALLOWED_JSON = {".json"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _safe(filename: str) -> str:
    return secure_filename(filename)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    installed, version = validation_service.check_pandoc()
    return jsonify({"pandoc": {"installed": installed, "version": version}})


@app.route("/api/files/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    results = []
    skipped = []
    for f in files:
        if not f.filename:
            continue
        if _ext(f.filename) not in ALLOWED_MD:
            skipped.append(f.filename)
            continue
        filename = _safe(f.filename)
        if not filename:
            skipped.append(f.filename)
            continue
        dest = os.path.join(WORKSPACE_DIR, filename)
        f.save(dest)
        results.append({"name": filename, "path": dest})

    if not results:
        return jsonify({"error": "No valid Markdown files uploaded"}), 400

    return jsonify({"files": results, "skipped": skipped})


@app.route("/api/zip/upload", methods=["POST"])
def upload_zip():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400

    if _ext(f.filename) not in ALLOWED_ZIP:
        return jsonify({"error": "File must be a ZIP archive"}), 400

    zip_name = f"upload_{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(WORKSPACE_DIR, zip_name)
    f.save(zip_path)

    extract_dir = os.path.join(WORKSPACE_DIR, f"zip_{uuid.uuid4().hex}")
    try:
        zip_importer.extract_zip(zip_path, extract_dir)
    except Exception as exc:
        os.remove(zip_path)
        return jsonify({"error": f"Failed to extract ZIP: {exc}"}), 400

    os.remove(zip_path)
    contents = zip_importer.inspect_contents(extract_dir)

    # Load manifest if present
    loaded_manifest = None
    if contents["manifest"]:
        try:
            loaded_manifest = manifest_service.load_manifest(contents["manifest"])
        except Exception:
            loaded_manifest = None

    # Build ordered file list, honouring manifest order when available
    md_files = contents["md_files"]
    if loaded_manifest and loaded_manifest.get("files"):
        ordered = []
        remaining = list(md_files)
        for fname in loaded_manifest["files"]:
            for fpath in remaining:
                if os.path.basename(fpath) == fname:
                    ordered.append(fpath)
                    remaining.remove(fpath)
                    break
        ordered += file_loader.sort_files_naturally(remaining)
        md_files = ordered
    else:
        md_files = file_loader.sort_files_naturally(md_files)

    files_info = [{"name": os.path.basename(p), "path": p} for p in md_files]
    result = {
        "files": files_info,
        "cover": (
            {"name": os.path.basename(contents["cover"]), "path": contents["cover"]}
            if contents["cover"]
            else None
        ),
        "css": (
            {"name": os.path.basename(contents["css"]), "path": contents["css"]}
            if contents["css"]
            else None
        ),
        "manifest": loaded_manifest,
    }
    return jsonify(result)


@app.route("/api/assets/cover", methods=["POST"])
def upload_cover():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400
    if _ext(f.filename) not in ALLOWED_IMAGE:
        return jsonify({"error": "Cover must be a JPG or PNG image"}), 400
    filename = _safe(f.filename)
    dest = os.path.join(WORKSPACE_DIR, filename)
    f.save(dest)
    return jsonify({"name": filename, "path": dest})


@app.route("/api/assets/css", methods=["POST"])
def upload_css():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file provided"}), 400
    if _ext(f.filename) not in ALLOWED_CSS:
        return jsonify({"error": "CSS must be a .css file"}), 400
    filename = _safe(f.filename)
    dest = os.path.join(WORKSPACE_DIR, filename)
    f.save(dest)
    return jsonify({"name": filename, "path": dest})


@app.route("/api/build", methods=["POST"])
def build():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    files = data.get("files", [])
    metadata = data.get("metadata", {})
    cover_path = data.get("cover_path") or None
    css_path = data.get("css_path") or None
    output_filename = (data.get("output_filename") or "book").strip()
    if not output_filename.endswith(".epub"):
        output_filename += ".epub"
    output_filename = _safe(output_filename)
    output_path = os.path.join(DIST_DIR, output_filename)

    errors = validation_service.validate_build(files, cover_path, css_path)
    if errors:
        return jsonify({"success": False, "log": "\n".join(errors)})

    pandoc_ok, _ = validation_service.check_pandoc()
    if not pandoc_ok:
        return jsonify(
            {
                "success": False,
                "log": (
                    "Pandoc is not installed. "
                    "Please install it from https://pandoc.org/installing.html"
                ),
            }
        )

    success, log = pandoc_service.build_epub(
        files=files,
        output_path=output_path,
        metadata=metadata,
        cover_path=cover_path,
        css_path=css_path,
    )
    result: dict = {"success": success, "log": log}
    if success:
        result["output_path"] = output_path
        result["output_filename"] = output_filename
    return jsonify(result)


@app.route("/api/manifest/save", methods=["POST"])
def save_manifest():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request body"}), 400
    manifest = data.get("manifest", {})
    save_path = os.path.join(WORKSPACE_DIR, "book.json")
    try:
        manifest_service.save_manifest(manifest, save_path)
        return jsonify({"success": True, "path": save_path})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/manifest/load", methods=["POST"])
def load_manifest():
    # Accept uploaded JSON file, or fall back to workspace/book.json
    f = request.files.get("file")
    if f and f.filename:
        if _ext(f.filename) not in ALLOWED_JSON:
            return jsonify({"error": "Manifest must be a .json file"}), 400
        try:
            content = f.read().decode("utf-8")
            manifest = json.loads(content)
            return jsonify({"manifest": manifest})
        except Exception as exc:
            return jsonify({"error": f"Invalid manifest file: {exc}"}), 400

    save_path = os.path.join(WORKSPACE_DIR, "book.json")
    if not os.path.isfile(save_path):
        return jsonify({"error": "No saved project found in workspace"}), 404
    try:
        manifest = manifest_service.load_manifest(save_path)
        return jsonify({"manifest": manifest})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/output/<path:filename>")
def download_output(filename):
    safe = _safe(filename)
    return send_from_directory(DIST_DIR, safe, as_attachment=True)


@app.route("/api/workspace/clear", methods=["POST"])
def clear_workspace():
    for item in os.listdir(WORKSPACE_DIR):
        item_path = os.path.join(WORKSPACE_DIR, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
