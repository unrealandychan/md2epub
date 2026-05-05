import sys
import os
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.validation_service import validate_build, check_pandoc


def test_validate_build_empty_files():
    errors = validate_build([], None, None)
    assert any("No Markdown files" in e for e in errors)


def test_validate_build_file_not_found(tmp_path):
    errors = validate_build(["/nonexistent/path/chapter.md"], None, None)
    assert any("not found" in e.lower() for e in errors)


def test_check_pandoc_not_found():
    import subprocess
    with patch("subprocess.run", side_effect=FileNotFoundError):
        installed, version = check_pandoc()
    assert installed is False
    assert version == ""
