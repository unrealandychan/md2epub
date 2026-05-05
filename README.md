# md → Kobo EPUB Builder

A local-first web app that converts Markdown files into a Kobo-ready EPUB through a visual interface powered by Pandoc.

## Requirements

- **Python 3.9+**
- **Pandoc** — install from [pandoc.org/installing.html](https://pandoc.org/installing.html)

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open <http://localhost:5000> in your browser.

## Features

- **Import Markdown files** — add one or more `.md` files directly
- **Import ZIP project** — extract a ZIP and auto-detect chapters, cover, CSS, and `book.json` manifest
- **Visual chapter ordering** — drag-and-drop, move up/down buttons, A–Z and natural-numeric sort
- **Metadata** — title, author, language, output filename, TOC toggle
- **Assets** — attach a cover image (JPG/PNG) and custom EPUB CSS
- **Build** — invokes Pandoc to produce a valid EPUB3; logs are shown in the interface
- **Project save/load** — saves a `book.json` manifest for reuse; load it back via file upload

## ZIP project format

```
my-book.zip
├── 01-intro.md
├── 02-chapter-one.md
├── cover.jpg          # optional
├── epub.css           # optional
└── book.json          # optional manifest
```

If `book.json` is present it defines metadata and chapter order. Otherwise chapters are sorted naturally and can be reordered in the UI.

## Manifest format (`book.json`)

```json
{
  "title": "My Book",
  "author": "Author Name",
  "language": "en-US",
  "toc": true,
  "cover_image": "cover.jpg",
  "css": "epub.css",
  "output_filename": "book.epub",
  "files": [
    "01-intro.md",
    "02-chapter-one.md"
  ]
}
```

## Output

Built EPUBs are written to `dist/`. They can be opened in Calibre for inspection or transfer to a Kobo device (Calibre 8 supports KEPUB conversion on transfer).
