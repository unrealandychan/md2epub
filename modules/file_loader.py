import os
import re


def natural_sort_key(filepath: str):
    """Split filename on digit runs for natural ordering (2.md before 10.md)."""
    name = os.path.basename(filepath)
    parts = re.split(r"(\d+)", name)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


def sort_files_naturally(file_paths: list) -> list:
    return sorted(file_paths, key=natural_sort_key)


def sort_files_alphabetically(file_paths: list) -> list:
    return sorted(file_paths, key=lambda p: os.path.basename(p).lower())
