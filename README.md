# md2epub

Convert Markdown files to EPUB using Pandoc — with a simple web UI.

## Features

- Upload Markdown files (individually or as a ZIP archive)
- Automatic natural sorting (2.md before 10.md)
- Frontmatter extraction (title → H1 heading)
- Hugo shortcode stripping
- Custom cover image and CSS
- Project manifest (book.json) save/load

## Quick Start (Docker)

```bash
docker compose up --build
```

Open http://localhost:8000 in your browser.

## Local Development

**Requirements:** Python 3.10+, [Pandoc](https://pandoc.org/installing.html)

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000.

## Testing

```bash
pytest tests/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/api/status` | Check Pandoc installation |
| POST | `/api/files/upload` | Upload Markdown files |
| POST | `/api/zip/upload` | Upload ZIP archive |
| POST | `/api/assets/cover` | Upload cover image |
| POST | `/api/assets/css` | Upload CSS stylesheet |
| POST | `/api/build` | Build EPUB |
| POST | `/api/manifest/save` | Save project manifest |
| POST | `/api/manifest/load` | Load project manifest |
| GET | `/api/output/{filename}` | Download built EPUB |
| POST | `/api/workspace/clear` | Clear workspace |

## Stack

- **FastAPI** — async web framework
- **Uvicorn** — ASGI server
- **Pandoc** — Markdown → EPUB conversion
- **PyYAML** — frontmatter parsing
