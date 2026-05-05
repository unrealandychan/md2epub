from __future__ import annotations

import os
import subprocess


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

    cmd = ["pandoc"] + files + ["-o", output_path, "--to=epub3"]

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
    if css_path:
        cmd.append(f"--css={css_path}")

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
