import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

app = FastAPI()

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

ALLOWED_MD = {".md", ".markdown"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".gif"}
ALLOWED_CSS = {".css"}
ALLOWED_ZIP = {".zip"}
ALLOWED_JSON = {".json"}


def _ext(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def _safe(filename: str) -> str:
    return Path(filename).name


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
async def index():
    index_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)


@app.get("/api/status")
async def status():
    installed, version = validation_service.check_pandoc()
    return JSONResponse({"pandoc": {"installed": installed, "version": version}})


@app.post("/api/files/upload")
async def upload_files(files: list[UploadFile] = File(...)):
    if not files:
        return JSONResponse({"error": "No files provided"}, status_code=400)

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
        content = await f.read()
        with open(dest, "wb") as out:
            out.write(content)
        results.append({"name": filename, "path": dest})

    if not results:
        return JSONResponse({"error": "No valid Markdown files uploaded"}, status_code=400)

    return JSONResponse({"files": results, "skipped": skipped})


@app.post("/api/zip/upload")
async def upload_zip(file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)

    if _ext(file.filename) not in ALLOWED_ZIP:
        return JSONResponse({"error": "File must be a ZIP archive"}, status_code=400)

    zip_name = f"upload_{uuid.uuid4().hex}.zip"
    zip_path = os.path.join(WORKSPACE_DIR, zip_name)
    content = await file.read()
    with open(zip_path, "wb") as out:
        out.write(content)

    extract_dir = os.path.join(WORKSPACE_DIR, f"zip_{uuid.uuid4().hex}")
    try:
        zip_importer.extract_zip(zip_path, extract_dir)
    except Exception as exc:
        os.remove(zip_path)
        return JSONResponse({"error": f"Failed to extract ZIP: {exc}"}, status_code=400)

    os.remove(zip_path)
    contents = zip_importer.inspect_contents(extract_dir)

    loaded_manifest = None
    if contents["manifest"]:
        try:
            loaded_manifest = manifest_service.load_manifest(contents["manifest"])
        except Exception:
            loaded_manifest = None

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
    return JSONResponse(result)


@app.post("/api/assets/cover")
async def upload_cover(file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)
    if _ext(file.filename) not in ALLOWED_IMAGE:
        return JSONResponse({"error": "Cover must be a JPG or PNG image"}, status_code=400)
    filename = _safe(file.filename)
    dest = os.path.join(WORKSPACE_DIR, filename)
    content = await file.read()
    with open(dest, "wb") as out:
        out.write(content)
    return JSONResponse({"name": filename, "path": dest})


@app.post("/api/assets/css")
async def upload_css(file: UploadFile = File(...)):
    if not file or not file.filename:
        return JSONResponse({"error": "No file provided"}, status_code=400)
    if _ext(file.filename) not in ALLOWED_CSS:
        return JSONResponse({"error": "CSS must be a .css file"}, status_code=400)
    filename = _safe(file.filename)
    dest = os.path.join(WORKSPACE_DIR, filename)
    content = await file.read()
    with open(dest, "wb") as out:
        out.write(content)
    return JSONResponse({"name": filename, "path": dest})


@app.post("/api/build")
async def build(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid request body"}, status_code=400)

    if not data:
        return JSONResponse({"error": "Invalid request body"}, status_code=400)

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
        return JSONResponse({"success": False, "log": "\n".join(errors)})

    pandoc_ok, _ = validation_service.check_pandoc()
    if not pandoc_ok:
        return JSONResponse(
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
    return JSONResponse(result)


@app.post("/api/manifest/save")
async def save_manifest(request: Request):
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid request body"}, status_code=400)
    if not data:
        return JSONResponse({"error": "Invalid request body"}, status_code=400)
    manifest = data.get("manifest", {})
    save_path = os.path.join(WORKSPACE_DIR, "book.json")
    try:
        manifest_service.save_manifest(manifest, save_path)
        return JSONResponse({"success": True, "path": save_path})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/manifest/load")
async def load_manifest(request: Request, file: Optional[UploadFile] = File(None)):
    if file and file.filename:
        if _ext(file.filename) not in ALLOWED_JSON:
            return JSONResponse({"error": "Manifest must be a .json file"}, status_code=400)
        try:
            content = await file.read()
            manifest = json.loads(content.decode("utf-8"))
            return JSONResponse({"manifest": manifest})
        except Exception as exc:
            return JSONResponse({"error": f"Invalid manifest file: {exc}"}, status_code=400)

    save_path = os.path.join(WORKSPACE_DIR, "book.json")
    if not os.path.isfile(save_path):
        return JSONResponse({"error": "No saved project found in workspace"}, status_code=404)
    try:
        manifest = manifest_service.load_manifest(save_path)
        return JSONResponse({"manifest": manifest})
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/api/output/{filename}")
async def download_output(filename: str):
    safe = _safe(filename)
    file_path = os.path.join(DIST_DIR, safe)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=safe, media_type="application/epub+zip")


@app.post("/api/workspace/clear")
async def clear_workspace():
    for item in os.listdir(WORKSPACE_DIR):
        item_path = os.path.join(WORKSPACE_DIR, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)
    return JSONResponse({"success": True})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
