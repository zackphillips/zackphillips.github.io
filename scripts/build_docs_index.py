"""Generate ``docs/index.json`` — the catalogue behind ``docs.html``.

A static site cannot list a directory, so the browser needs a manifest of the
Markdown files in ``docs/``. This script walks ``docs/**/*.md`` and writes one
JSON file describing each document: slug, title, category, ordering, a short
description, its headings (used for search), and the date of the last commit
that touched it.

Documents need no front matter. Anything missing is inferred:

* ``title``       → first ``# H1``, else the filename in Title Case
* ``description`` → first paragraph of prose, truncated
* ``category``    → the subdirectory name, else "General"
* ``order``       → ``DEFAULT_ORDER`` (ties break alphabetically by title)

Optional YAML front matter overrides any of those::

    ---
    title: Man Overboard
    category: Emergency
    order: 10
    description: What to do when someone goes over the side.
    ---

Run it via ``make docs-index``. The ``docs-index`` GitHub Action also runs it on
every push that touches ``docs/``, so files added through the GitHub web UI show
up on the site without anyone touching a terminal.
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .utils import atomic_write_text, get_project_root

DOCS_DIR = "docs"
INDEX_FILE = "docs/index.json"
DEFAULT_CATEGORY = "General"
DEFAULT_ORDER = 100
# Descriptions are teaser text on the document cards — keep them one line.
DESCRIPTION_MAX_CHARS = 180
# Wall-clock cap on the `git log` used for per-file modification dates.
GIT_TIMEOUT = 15

_FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
# Inline Markdown that should not survive into a plain-text title/description.
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"[*_`]+")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Split optional YAML front matter off the head of a Markdown document.

    Returns ``(metadata, body)``. Malformed or non-mapping front matter is
    ignored rather than raising: a typo in one SOP must not take the whole
    documents page offline.
    """
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[match.end() :]


def strip_inline_markdown(text: str) -> str:
    """Reduce a line of Markdown to readable plain text."""
    text = _HTML_COMMENT_RE.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = _EMPHASIS_RE.sub("", text)
    return " ".join(text.split())


def iter_content_lines(body: str):
    """Yield ``(line, in_code_fence)`` for every line of *body*.

    Headings inside fenced code blocks are examples, not structure, so callers
    need to know which side of a fence they are on.
    """
    in_fence = False
    for line in body.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            yield line, True
            continue
        yield line, in_fence


def extract_headings(body: str) -> list[dict[str, Any]]:
    """All ATX headings outside code fences, in document order."""
    headings = []
    for line, in_fence in iter_content_lines(body):
        if in_fence:
            continue
        match = _ATX_HEADING_RE.match(line)
        if match:
            text = strip_inline_markdown(match.group(2))
            if text:
                headings.append({"level": len(match.group(1)), "text": text})
    return headings


def derive_description(body: str) -> str:
    """First paragraph of prose, skipping headings, quotes, lists and tables."""
    parts: list[str] = []
    for line, in_fence in iter_content_lines(body):
        if in_fence:
            continue
        stripped = line.strip()
        if not stripped:
            if parts:
                break
            continue
        if (
            stripped.startswith(("#", ">", "|", "-", "*", "+", "<"))
            or stripped == "---"
        ):
            if parts:
                break
            continue
        if re.match(r"^\d+\.\s", stripped):
            if parts:
                break
            continue
        parts.append(stripped)

    text = strip_inline_markdown(" ".join(parts))
    if len(text) > DESCRIPTION_MAX_CHARS:
        text = text[:DESCRIPTION_MAX_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def last_modified(root: Path, rel_path: str) -> str | None:
    """Committer date of the newest commit touching *rel_path*, ISO-8601.

    Returns None outside a git checkout, or for a file that has never been
    committed — the frontend simply omits the "updated" line in that case.
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", rel_path],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def build_entry(root: Path, path: Path) -> dict[str, Any]:
    """Describe one Markdown file for the index."""
    rel_path = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    meta, body = split_front_matter(text)
    headings = extract_headings(body)

    h1 = next((h["text"] for h in headings if h["level"] == 1), None)
    title = str(meta.get("title") or h1 or title_from_filename(path))

    # Nested docs/<category>/<file>.md take their category from the directory.
    parent = path.parent.relative_to(root / DOCS_DIR).as_posix()
    folder_category = parent.replace("-", " ").replace("_", " ").title()
    category = str(
        meta.get("category") or (folder_category if parent != "." else DEFAULT_CATEGORY)
    )

    try:
        order = int(meta.get("order", DEFAULT_ORDER))
    except (TypeError, ValueError):
        order = DEFAULT_ORDER

    entry: dict[str, Any] = {
        "slug": path.relative_to(root / DOCS_DIR).with_suffix("").as_posix(),
        "path": rel_path,
        "title": title,
        "category": category,
        "order": order,
        "description": str(meta.get("description") or derive_description(body)),
        # Level 1 duplicates the title in the sidebar; the frontend builds its
        # table of contents from the rendered DOM anyway, so this list exists
        # only to make search find text that is not on screen yet.
        "headings": [h for h in headings if h["level"] > 1],
        "words": len(body.split()),
    }
    updated = last_modified(root, rel_path)
    if updated:
        entry["updated"] = updated
    return entry


def build_index(root: Path) -> dict[str, Any]:
    """Scan ``docs/`` and return the full index payload."""
    docs_dir = root / DOCS_DIR
    if not docs_dir.is_dir():
        return {"generated": datetime.now(UTC).isoformat(), "docs": []}

    entries = [
        build_entry(root, path)
        for path in sorted(docs_dir.rglob("*.md"))
        # Leading underscore marks a draft or include — not published.
        if not path.name.startswith("_")
    ]
    entries.sort(key=lambda e: (e["category"].lower(), e["order"], e["title"].lower()))
    return {"generated": datetime.now(UTC).isoformat(), "docs": entries}


def render_index(index: dict[str, Any]) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False) + "\n"


def read_existing(index_path: Path) -> dict[str, Any] | None:
    """The committed index, or None if it is absent or unreadable."""
    try:
        current = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return current if isinstance(current, dict) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed index is out of date (do not write)",
    )
    args = parser.parse_args(argv)

    root = get_project_root()
    index = build_index(root)
    index_path = root / INDEX_FILE
    current = read_existing(index_path)
    unchanged = current is not None and current.get("docs") == index["docs"]

    if args.check:
        if current is None:
            print(f"{INDEX_FILE} is missing or unreadable — run 'make docs-index'.")
            return 1
        if not unchanged:
            print(f"{INDEX_FILE} is out of date — run 'make docs-index'.")
            return 1
        print(f"{INDEX_FILE} is up to date ({len(index['docs'])} documents).")
        return 0

    # Rewriting the file just to bump `generated` would make the pre-commit hook
    # report "files were modified" on every single run, and would hand the CI
    # workflow an empty-but-dirty diff to commit. Only write on a real change.
    if unchanged:
        print(f"{INDEX_FILE} already up to date ({len(index['docs'])} documents).")
        return 0

    atomic_write_text(index_path, render_index(index))
    print(f"Wrote {INDEX_FILE} ({len(index['docs'])} documents).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
