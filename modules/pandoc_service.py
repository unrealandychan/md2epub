from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from modules.preprocessor import preprocess_files

# Path to the fallback Kobo-safe CSS shipped with this app
_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_CSS = os.path.join(_HERE, '..', 'static', 'kobo.css')

# Prefer Homebrew pandoc (3.x) over any older system-wide install.
# On Apple Silicon Macs, Homebrew lands in /opt/homebrew; on Intel in /usr/local.
_PANDOC_BIN = next(
    (p for p in (
        '/opt/homebrew/bin/pandoc',
        '/usr/local/homebrew/bin/pandoc',
    ) if os.path.isfile(p)),
    'pandoc',  # fall back to whatever is on PATH
)


def build_epub(
    files: list,
    output_path: str,
    metadata: dict,
    cover_path: str | None = None,
    css_path: str | None = None,
) -> tuple:
    """
    Build an EPUB using Pandoc.

    Args:
        files:        Ordered list of absolute paths to Markdown files.
        output_path:  Absolute path for the output .epub file.
        metadata:     Dict containing title, author, language, toc.
        cover_path:   Absolute path to cover image (optional).
        css_path:     Absolute path to CSS file (optional).

    Returns:
        (success: bool, log: str)
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # ── Step 1: preprocess Markdown to strip Hugo/Jekyll shortcodes ──────────
    # Shortcode tags are passed through literally by Pandoc; Kobo's strict
    # EPUB XML parser rejects them, causing "unreadable" pages.
    tmp_dir = tempfile.mkdtemp(prefix='md2epub_')
    try:
        processed = preprocess_files(files, tmp_dir)
        success, log = _run_pandoc(processed, output_path, metadata, cover_path, css_path)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return success, log


def _run_pandoc(
    files: list,
    output_path: str,
    metadata: dict,
    cover_path: str | None,
    css_path: str | None,
) -> tuple:
    # Use caller's CSS, or fall back to the bundled Kobo-safe stylesheet.
    # The fallback fixes the blank-page bug (Pandoc issue #8435) and the
    # footnote rendering bug (#9851) that only appear on Kobo firmware.
    effective_css = css_path or (
        os.path.normpath(_DEFAULT_CSS) if os.path.isfile(os.path.normpath(_DEFAULT_CSS)) else None
    )

    cmd = [_PANDOC_BIN] + files + [
        "-o", output_path,
        "--to=epub3",
        # Each H1 starts a new EPUB chapter — required for Kobo chapter nav
        "--epub-chapter-level=1",
    ]

    if metadata.get("title"):
        cmd += ["--metadata", f'title={metadata["title"]}']
    if metadata.get("author"):
        cmd += ["--metadata", f'author={metadata["author"]}']
    if metadata.get("language"):
        cmd += ["--metadata", f'lang={metadata["language"]}']
    if metadata.get("toc"):
        cmd.append("--toc")
    if cover_path:
        cmd.append(f"--epub-cover-image={cover_path}")
    if effective_css:
        cmd.append(f"--css={effective_css}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        log_parts = []
        if result.stdout:
            log_parts.append(result.stdout)
        if result.stderr:
            log_parts.append(result.stderr)
        log = "\n".join(log_parts).strip()

        if result.returncode == 0:
            return True, log or "Build successful."
        return False, log or f"Pandoc exited with code {result.returncode}."

    except FileNotFoundError:
        return False, "Pandoc is not installed or not found in PATH."
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 120 seconds."
