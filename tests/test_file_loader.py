import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.file_loader import sort_files_naturally, sort_files_alphabetically


def test_natural_sort():
    files = ["/tmp/10.md", "/tmp/2.md", "/tmp/1.md"]
    result = sort_files_naturally(files)
    names = [os.path.basename(f) for f in result]
    assert names == ["1.md", "2.md", "10.md"]


def test_alphabetical_sort():
    files = ["/tmp/chapter_b.md", "/tmp/chapter_a.md", "/tmp/chapter_c.md"]
    result = sort_files_alphabetically(files)
    names = [os.path.basename(f) for f in result]
    assert names == ["chapter_a.md", "chapter_b.md", "chapter_c.md"]


def test_empty_list():
    assert sort_files_naturally([]) == []
    assert sort_files_alphabetically([]) == []
