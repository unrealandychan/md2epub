"""
Preprocess Markdown files before handing them to Pandoc.

Problems solved:
1. Hugo/Jekyll shortcodes ({{< ... >}}, {{% ... %}}) — stripped, inner text kept.
2. YAML frontmatter with Hugo-specific keys — the `title` field is converted into
   a real `# H1` heading so Pandoc's --epub-chapter-level=1 can split on it.
   All other frontmatter is removed (Hugo fields like `weight`, `breadcrumbs`
   are meaningless to Pandoc and can produce garbled output).
   Without H1 headings, every file lands in one XHTML document and Kobo only
   renders the first screen of it — appearing as a single page even though the
   TOC lists multiple chapters.
3. Excessive blank lines are collapsed.
4. Footnote labels are prefixed per-file so they are globally unique when
   Pandoc merges all files (prevents "Duplicate note reference" warnings).
5. Heading IDs are prefixed per-file to prevent "Duplicate identifier" warnings
   for common headings like ## Summary or ## References.
6. Absolute image paths (e.g. /map/ch01.png) are resolved by searching up the
   source file's directory tree; if not found the image tag is stripped.
"""
from __future__ import annotations

import os
import re

import yaml  # PyYAML — already a transitive dep of many packages; added to requirements

# Matches both opening and closing Hugo shortcode tags, e.g.:
#   {{< callout type="warning" >}}   {{% ref page %}}   {{< /callout >}}
_SHORTCODE_TAG = re.compile(r'\{\{[<%]\s*/?[\w-][^}]*?[>%]\}\}[ \t]*')

# YAML frontmatter block at the very top of a file
_FRONTMATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.DOTALL)

# Markdown heading line, optionally ending with a Pandoc attrs block {#id .cls}
_HEADING_LINE = re.compile(
    r'^(#{1,6})([ \t]+)(.*?)(\s*\{[^}]*\})?\s*$',
    re.MULTILINE,
)

# Footnote reference [^label] and definition [^label]: (both forms)
_FOOTNOTE_REF = re.compile(r'\[\^([^\]]+)\]')


def _extract_frontmatter(text: str) -> tuple:
    """
    Return (title_or_None, body_without_frontmatter).
    Strips ALL frontmatter; promotes title to an H1 if found.
    """
    m = _FRONTMATTER.match(text)
    if not m:
        return None, text

    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}

    title = meta.get('title') or None
    body = text[m.end():]
    return title, body


def strip_shortcodes(text: str) -> str:
    """Remove shortcode tags; text between paired tags is preserved."""
    text = _SHORTCODE_TAG.sub('', text)
    # Collapse 3+ blank lines down to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


def _slugify(heading_text: str) -> str:
    """Produce a Pandoc-style ID slug from heading text."""
    # Strip inline markup characters
    slug = re.sub(r'[`*_]', '', heading_text)
    slug = slug.lower().strip()
    slug = re.sub(r'\s+', '-', slug)
    slug = re.sub(r'[^\w-]', '', slug)
    slug = slug.strip('-')
    return slug or 'sec'


def _add_heading_ids(text: str, ch_prefix: str) -> str:
    """
    Add explicit per-chapter IDs to every heading so that common headings
    like '## Summary' in different chapters don't produce duplicate HTML ids.
    """
    def repl(m):
        hashes = m.group(1)
        space = m.group(2)
        head_text = m.group(3).rstrip()
        existing_attrs = m.group(4)  # e.g. ' {#foo .bar}' or None

        if existing_attrs:
            inner = existing_attrs.strip()[1:-1]  # strip leading/trailing { }
            if re.search(r'#\S', inner):
                # Prefix the existing explicit ID
                new_inner = re.sub(
                    r'#(\S+)',
                    lambda im: f'#{ch_prefix}-{im.group(1)}',
                    inner,
                    count=1,
                )
                return f'{hashes}{space}{head_text} {{{new_inner}}}'
            else:
                # Attrs block exists but has no id — add one
                slug = _slugify(head_text)
                return f'{hashes}{space}{head_text} {{#{ch_prefix}-{slug} {inner}}}'
        else:
            slug = _slugify(head_text)
            return f'{hashes}{space}{head_text} {{#{ch_prefix}-{slug}}}'

    return _HEADING_LINE.sub(repl, text)


def _renumber_footnotes(text: str, ch_prefix: str) -> str:
    """
    Prefix every footnote label with ch_prefix so that [^1] in chapter 2
    becomes [^ch0002_1], avoiding collisions with [^1] in chapter 1.
    Handles both inline references [^label] and definitions [^label]:.
    """
    return _FOOTNOTE_REF.sub(lambda m: f'[^{ch_prefix}_{m.group(1)}]', text)


def _resolve_image_path(img_path: str, src_dir: str) -> str:
    """
    Try to resolve an absolute image path by searching up the source directory
    tree (checking bare path and a 'static/' sub-directory at each level).
    Returns absolute path string if found, else None.
    """
    if not img_path.startswith('/'):
        return img_path  # relative paths need no fixing

    stripped = img_path.lstrip('/')
    search_dir = src_dir
    for _ in range(6):
        for subdir in ('', 'static', 'public'):
            candidate = os.path.join(search_dir, subdir, stripped) if subdir else os.path.join(search_dir, stripped)
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        parent = os.path.dirname(search_dir)
        if parent == search_dir:
            break
        search_dir = parent
    return None


def _fix_image_paths(text: str, src_dir: str) -> str:
    """
    Rewrite absolute image paths to resolved absolute paths, or strip the
    image tag (keeping alt text) if the file cannot be found.
    """
    img_pattern = re.compile(
        r'!\[([^\]]*)\]\((/[^)\s]*)([^)]*)\)'
    )

    def repl(m):
        alt = m.group(1)
        path = m.group(2)
        extras = m.group(3)  # title or extra attributes

        resolved = _resolve_image_path(path, src_dir)
        if resolved:
            return f'![{alt}]({resolved}{extras})'
        # Strip missing image — return alt text as plain text, or empty string
        return alt if alt else ''

    return img_pattern.sub(repl, text)


def preprocess_file(src_path: str, tmp_dir: str, idx: int) -> str:
    """
    Read one Markdown file, normalise it for Pandoc/Kobo, write a temp copy.

    Processing order:
      1. Extract YAML frontmatter — convert title to # H1, drop the rest.
      2. Strip Hugo shortcode tags.
      3. Collapse blank lines.
      4. Prefix footnote labels to make them globally unique.
      5. Add per-chapter heading IDs to prevent duplicate identifier warnings.
      6. Resolve or strip absolute image paths.

    The idx prefix avoids basename collisions across directories.
    Returns the temp file path.
    """
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    src_dir = os.path.dirname(os.path.abspath(src_path))
    ch_prefix = f'ch{idx:04d}'

    title, body = _extract_frontmatter(content)
    body = strip_shortcodes(body)

    # Prepend H1 heading so Pandoc's --epub-chapter-level=1 splits here.
    # Only add it if the body doesn't already open with an H1.
    if title and not re.match(r'^#\s', body.lstrip()):
        body = f'# {title}\n\n{body.lstrip()}'

    body = _renumber_footnotes(body, ch_prefix)
    body = _add_heading_ids(body, ch_prefix)
    body = _fix_image_paths(body, src_dir)

    basename = f'{idx:04d}_{os.path.basename(src_path)}'
    dest = os.path.join(tmp_dir, basename)
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(body)

    return dest


def preprocess_files(file_paths: list, tmp_dir: str) -> list:
    """Preprocess every file in file_paths. Returns list of temp paths."""
    return [preprocess_file(p, tmp_dir, i) for i, p in enumerate(file_paths)]
