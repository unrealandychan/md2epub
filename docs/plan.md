# Markdown to Kobo Builder Product Plan

## Product overview

This product is a local-first tool that turns one or more Markdown files into a Kobo-friendly ebook package by letting the user import files, arrange chapter order, set ebook metadata, and export an EPUB through Pandoc. The product should support both direct multi-file import and ZIP project import, because ZIP works well as a reusable packaging format while a visual chapter-ordering interface is still needed for human review and editing.[1][2][3][4][5]

The recommended v1 output is EPUB, not direct KEPUB, because Pandoc already provides a solid EPUB workflow and Calibre 8 now has native KEPUB support for Kobo workflows, including EPUB-to-KEPUB conversion during device transfer. This keeps the product simple, robust, and aligned with how Kobo users can already manage delivery today.[6][7][8][1]

## Problem statement

Markdown writers often have content split across multiple files and need a simple way to combine them into a real ebook while preserving chapter order, metadata, cover image, and styling. Existing conversion tooling is powerful but too command-line oriented for repeated publishing workflows, especially when chapter order changes often or a packaged ZIP project needs to be reopened later.[9][10][1]

The core problem is not just conversion; it is workflow orchestration. Users need a visual layer over Pandoc that handles file import, ordering, metadata entry, ZIP extraction, validation, build execution, and output management in one place.[2][3][1]

## Product goals

- Allow users to import multiple `.md` files and reorder them visually before build.[11][12]
- Allow users to import a ZIP file containing Markdown, cover image, CSS, and optional manifest metadata.[3][4]
- Generate a valid EPUB using Pandoc with title, author, language, TOC, cover image, and custom CSS options.[1][2]
- Save and reload projects so the same book can be rebuilt later without manual re-entry.[2][3]
- Fit Kobo workflows by producing EPUB that can be tested in Calibre and transferred to Kobo devices.[7][6]

## Non-goals for v1

- No cloud sync or user accounts.
- No collaborative editing.
- No direct in-app Kobo sync.
- No custom EPUB rendering engine.
- No direct KEPUB generation unless it can be added safely after the EPUB workflow is stable.[6][1]

## Target user

The primary user is a technical or semi-technical writer who already writes in Markdown and wants a repeatable publishing workflow for Kobo-compatible ebooks. The user may keep chapters in separate files, version them in Git, and occasionally package the whole project as a ZIP for portability or backup.[3][1]

A secondary user is a content creator who prefers a simple GUI over command-line Pandoc usage. That user still benefits from the same workflow but needs visible ordering, clear validation, and a single build action.[13][1]

## Product scope

### v1 scope

The first version should be a local-first app with a visual interface and a Pandoc-based build engine. It should support these flows:[1]

1. Import multiple Markdown files directly.[5]
2. Import one ZIP project file and extract its contents.[3]
3. Display chapters in a sortable list and let the user choose final order.[12][11]
4. Let the user edit metadata and choose optional assets such as cover image and CSS.[2]
5. Build one EPUB and show success or error logs.[1]
6. Save the project manifest for reopening later.[2]

### v2 scope

After v1 is stable, the product can add:

- One-click Calibre handoff or “Open in Calibre” action.[7][6]
- Chapter title extraction from Markdown headings.[9]
- Live merged preview.
- Watch mode for rebuild-on-change.
- Optional export presets for Kobo, Kindle-side EPUB, and generic EPUB.

## Recommended product shape

The recommended shape is a local web app or desktop-style local app with a GUI and a backend process that invokes Pandoc. Browser-only logic is suitable for UI work such as drag-and-drop, ZIP parsing, and metadata editing, but actual ebook generation should be delegated to Pandoc through a local process rather than recreated manually.[5][3][1]

The most practical implementation path is Python plus a lightweight web UI, or a desktop wrapper such as Tauri or Electron if a more app-like feel is desired. The key architectural principle is to keep the conversion engine external and stable while the product focuses on workflow orchestration and usability.[10][1]

## User experience

### Main entry options

The home screen should present two clear paths:

- Add Markdown files.
- Import ZIP project.[5][3]

This keeps the product simple while covering both the fast path and the reusable packaged-project path. Direct file import is best for quick one-off books, while ZIP import is best for archiving and transport.[3]

### Main interface sections

The main workspace should include:

| Section | Purpose |
|---|---|
| Input area | Add `.md` files or import one ZIP project.[3][5] |
| Chapter list | Show all Markdown files in a reorderable list; this order becomes book order.[11][12] |
| Metadata panel | Edit title, author, language, TOC, subtitle if supported, and output filename.[2] |
| Assets panel | Attach cover image and optional EPUB CSS.[1][2] |
| Build panel | Run build, show logs, show output path, surface errors.[1] |
| Project actions | Save manifest, load manifest, reset workspace. |

### Chapter ordering behavior

Chapter ordering must be treated as a primary feature, not a convenience. Pandoc assembles multi-file books in the order files are passed to it, so the app must preserve the exact user-selected order.[11][12]

The app should support:

- Drag-and-drop reordering.
- Move up/down actions for keyboard users.
- A–Z sorting.
- Natural numeric sorting, such as `2.md` before `10.md`.
- Manifest-defined order when loading a saved project.[9][2]

## ZIP import specification

ZIP import should be implemented as project import, not as blind archive upload. After the ZIP is loaded, the app should extract it, inspect contents, and populate the workspace.[4][3]

Recommended ZIP contents:

- `*.md` files for chapters.
- `cover.jpg` or `cover.png`.
- `epub.css` for ebook styling.
- `book.json` manifest for metadata and chapter order.

If `book.json` exists, the app should preload metadata and honor the manifest file order. If no manifest exists, the app should auto-detect all Markdown files, sort them naturally, and still let the user manually reorder them before build.[2][3]

## Manifest format

A simple JSON manifest should be used so projects are portable and reproducible. A recommended structure is:

```json
{
  "title": "My Book",
  "author": "Author Name",
  "language": "en-US",
  "toc": true,
  "cover_image": "cover.jpg",
  "css": "epub.css",
  "files": [
    "01-intro.md",
    "02-chapter-one.md",
    "03-chapter-two.md"
  ]
}
```

This manifest captures the complete build state needed to recreate the ebook later. It also decouples book order from folder ordering, which is important when users rename or reorganize files.[2]

## Functional requirements

### Input handling

- Import multiple Markdown files directly.[5]
- Import ZIP and extract supported file types.[3]
- Detect invalid or unsupported files and surface clear error messages.
- Support replacing, removing, or re-adding individual chapters.

### Metadata handling

- Title.
- Author.
- Language.
- Output filename.
- Table of contents toggle.[2]
- Cover image.[1][2]
- Custom EPUB CSS.[1]

### Build handling

- Validate Pandoc installation before build.[1]
- Validate referenced files exist.
- Build EPUB with ordered Markdown inputs.[12][1]
- Surface build logs and failure reasons.
- Write output to a predictable location such as `dist/`.

### Project persistence

- Save current project as `book.json`.
- Reload a previous project.
- Persist the chosen order of files.
- Rebind extracted ZIP contents into a working directory when needed.

## Technical architecture

### Recommended stack

The simplest recommended stack is Python plus a local web UI. Python is a strong fit because filesystem work, ZIP extraction, manifest handling, and subprocess execution for Pandoc are all straightforward.[3][1]

Suggested stack:

- Backend: Python with FastAPI or Flask.
- Frontend: HTML, CSS, and JavaScript with drag-and-drop sorting.
- ZIP handling: Python backend extraction, or JSZip in the UI if import is browser-assisted.[3]
- Build engine: Pandoc subprocess call.[1]
- Optional later integration: Calibre open/send workflow for Kobo.[6][7]

### Core modules

| Module | Responsibility |
|---|---|
| `file_loader` | Import Markdown files, inspect folders, normalize paths. |
| `zip_importer` | Extract ZIP contents and find supported assets.[3] |
| `ordering_service` | Store chapter order, sorting rules, drag/drop updates. |
| `manifest_service` | Read and write `book.json`. |
| `validation_service` | Check dependencies, missing files, invalid inputs. |
| `pandoc_service` | Build Pandoc command and execute EPUB export.[1] |
| `ui` | Render file list, metadata form, build panel, logs. |

## Build pipeline

The build pipeline should work as follows:

1. Validate Pandoc is installed and callable.[1]
2. Validate the ordered chapter list is not empty.
3. Validate all referenced files exist.
4. Collect metadata, cover image, and CSS options.[2]
5. Build the ordered Pandoc argument list.
6. Execute Pandoc and write EPUB output.[1]
7. Capture and display stdout and stderr in the interface.
8. Save build artifact path for easy opening.

A representative command shape is:

```bash
pandoc chapter1.md chapter2.md chapter3.md \
  -o output/book.epub \
  --to=epub3 \
  --toc \
  --css=epub.css \
  --epub-cover-image=cover.jpg
```

Pandoc’s EPUB support already covers the core output features this product needs, so the product should wrap that command cleanly rather than attempt direct EPUB internals manipulation.[2][1]

## Kobo workflow

The product should position itself as “Kobo-ready” rather than “Kobo-device-managed” in v1. EPUB is the right initial output because Calibre 8 adds native KEPUB support and supports EPUB-to-KEPUB workflows for Kobo users.[7][6]

The expected user path is:

1. Build EPUB in the app.
2. Open or inspect EPUB in Calibre.
3. Send to Kobo, optionally using Calibre’s KEPUB workflow.[8][6]

This avoids premature device integration work while still fitting real Kobo usage well. It also reduces product complexity during the initial build.

## Risks and constraints

### Compatibility risk

There have been Kobo-related reports for some Pandoc-generated EPUB files, including blank-page behavior and footnote issues on certain Kobo workflows. The product should therefore keep output conservative, test with real devices when possible, and avoid making advanced EPUB features mandatory in v1.[14][15]

### UX risk

ZIP import can become confusing if the archive contains nested folders, duplicate chapter names, or missing manifests. The interface should therefore always show extracted contents and final resolved order before build, rather than building silently from ZIP contents.[4][3]

### Dependency risk

The build depends on Pandoc being installed locally. The app should detect this early, provide a clear installation message, and avoid ambiguous build errors when the dependency is missing.[1]

## Milestones

### Milestone 1: core engine

- Create local project structure.
- Implement manifest model.
- Implement Pandoc subprocess build.
- Validate EPUB generation from ordered files.[12][1]

### Milestone 2: visual interface

- Build main UI layout.
- Add multi-file import.
- Add sortable chapter list.
- Add metadata and asset forms.[13][5]

### Milestone 3: ZIP project import

- Add ZIP upload.
- Extract and inspect contents.
- Read `book.json` if present.
- Populate UI with inferred files and metadata.[3]

### Milestone 4: persistence and polish

- Save/load project manifest.
- Improve validation and error handling.
- Add output folder open action.
- Add keyboard-friendly ordering controls.

### Milestone 5: Kobo testing

- Validate output in Calibre.[6][7]
- Test on Kobo device where available.
- Document known formatting limitations.[15][14]

## Acceptance criteria

The product should be considered ready for v1 when it satisfies all of the following:

- Users can import multiple Markdown files and reorder them visually.[11][12]
- Users can import a ZIP project and inspect extracted contents before build.[4][3]
- Users can set title, author, language, TOC, cover image, and CSS options.[2][1]
- The app can build a single EPUB successfully through Pandoc.[1]
- The app can save and reload project configuration through a manifest.[2]
- Build logs and validation errors are clear and actionable.
- Output can be opened in Calibre for Kobo workflows.[7][6]

## Implementation notes for Copilot

A useful implementation prompt is:

> Build a local-first app called `md-to-kobo-builder` that converts multiple Markdown files into one EPUB for Kobo workflows. The app must support direct Markdown import and ZIP project import, display chapters in a drag-and-drop reorderable list, collect metadata such as title, author, language, TOC, cover image, and CSS, and export a single EPUB by invoking Pandoc as a subprocess. If a ZIP contains `book.json`, preload metadata and file order from it; otherwise infer all Markdown files and let the user reorder them manually. Keep v1 local only, with no auth, database, or cloud sync. Add project save/load, validation, and build logs.

## Next build order

The most efficient implementation order is:

1. Build the Pandoc wrapper and manifest model first.[1]
2. Add the chapter ordering UI next.[11][12]
3. Add ZIP import after the basic file workflow works.[3]
4. Add save/load and polish after the build loop is stable.
5. Test the output in Calibre and then on Kobo hardware if available.[6][7]

Sources
[1] Creating an ebook with pandoc https://pandoc.org/epub.html
[2] 11.1 EPUB Metadata https://pandoc.org/demo/example33/11.1-epub-metadata.html
[3] Create Zip archives in the browser with Jszip - Transloadit https://transloadit.com/devtips/create-zip-archives-in-the-browser-with-jszip/
[4] Does html input support drag & drop from zip folder? https://stackoverflow.com/questions/57828382/does-html-input-support-drag-drop-from-zip-folder
[5] File drag and drop - Web APIs | MDN https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/File_drag_and_drop
[6] New in calibre 8.0 https://calibre-ebook.com/new-in/seventeen
[7] What's new https://calibre-ebook.com/whats-new
[8] Calibre Ebook Manager Improves Support for Kobo E- ... https://www.omgubuntu.co.uk/2025/03/calibre-update-convert-kobo-kepub-files
[9] Compiling multiple markdown files to epub https://www.glaciology.net/2025/compiling-multiple-markdown-files-to-epub/
[10] Customizing pandoc to generate beautiful pdf and epub from ... https://learnbyexample.github.io/customizing-pandoc/
[11] Inserting Part Dividers Into Markdown ePub with Pandoc https://stackoverflow.com/questions/64269487/inserting-part-dividers-into-markdown-epub-with-pandoc
[12] Converting multiple Markdown files to EPUB with Pandoc in C# https://stackoverflow.com/questions/50695395/converting-multiple-markdown-files-to-epub-with-pandoc-in-c-sharp
[13] How to make a Drag-and-Drop file uploader https://uploadcare.com/blog/how-to-make-a-drag-and-drop-file-uploader/
[14] Pandoc 2.19 epubs don't work on Kobo device #8435 https://github.com/jgm/pandoc/issues/8435
[15] Epub: Footnotes don't work on Kobo readers · Issue #9851 https://github.com/jgm/pandoc/issues/9851
