from __future__ import annotations

import os
import subprocess


def check_pandoc() -> tuple:
    """Check if pandoc is installed. Returns (installed: bool, version: str)."""
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            return True, version
        return False, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, ""


def validate_build(files: list, cover_path: str | None, css_path: str | None) -> list:
    """Validate build inputs. Returns a list of human-readable error strings."""
    errors = []

    if not files:
        errors.append("No Markdown files selected.")

    for f in files:
        if not os.path.isfile(f):
            errors.append(f"File not found: {f}")

    if cover_path and not os.path.isfile(cover_path):
        errors.append(f"Cover image not found: {cover_path}")

    if css_path and not os.path.isfile(css_path):
        errors.append(f"CSS file not found: {css_path}")

    return errors
