"""Tests for scripts/build_docs_index.py.

The index is what docs.html lists, so a regression here makes documents vanish
from the site even though the Markdown is still committed.
"""

import json

import pytest

from scripts import build_docs_index as bdi


def write_doc(root: str, name: str, text: str):
    """Create docs/<name> under a temp repo root and return its Path."""
    path = root / "docs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A temp repo root with no git history (so `updated` is always absent)."""
    monkeypatch.setattr(bdi, "last_modified", lambda root, rel: None)
    (tmp_path / "docs").mkdir()
    return tmp_path


# ── Front matter ────────────────────────────────────────────────────────────


def test_front_matter_is_parsed_and_stripped():
    meta, body = bdi.split_front_matter(
        "---\ntitle: Anchoring\norder: 3\n---\n# Anchoring\n"
    )
    assert meta == {"title": "Anchoring", "order": 3}
    assert body == "# Anchoring\n"


def test_no_front_matter_leaves_body_untouched():
    text = "# Anchoring\n\nDrop the hook.\n"
    meta, body = bdi.split_front_matter(text)
    assert meta == {}
    assert body == text


def test_malformed_front_matter_is_ignored_not_raised():
    # A typo in one SOP must not take the whole documents page offline.
    text = "---\ntitle: [unclosed\n---\nBody\n"
    meta, body = bdi.split_front_matter(text)
    assert meta == {}
    assert body == text


def test_horizontal_rule_is_not_mistaken_for_front_matter():
    text = "Intro\n\n---\n\nMore\n"
    meta, body = bdi.split_front_matter(text)
    assert meta == {}
    assert body == text


# ── Inferred metadata ───────────────────────────────────────────────────────


def test_title_falls_back_to_first_h1(repo):
    path = write_doc(repo, "man-overboard.md", "# Man Overboard\n\nStop the boat.\n")
    entry = bdi.build_entry(repo, path)
    assert entry["title"] == "Man Overboard"
    assert entry["slug"] == "man-overboard"
    assert entry["path"] == "docs/man-overboard.md"


def test_title_falls_back_to_filename_when_no_h1(repo):
    path = write_doc(repo, "shore_power-hookup.md", "Plug it in.\n")
    assert bdi.build_entry(repo, path)["title"] == "Shore Power Hookup"


def test_front_matter_overrides_inferred_values(repo):
    path = write_doc(
        repo,
        "engine.md",
        "---\ntitle: Yanmar 4JH\ncategory: Engine\norder: 5\ndescription: Start-up drill.\n---\n# Engine\n\nIgnored prose.\n",
    )
    entry = bdi.build_entry(repo, path)
    assert entry["title"] == "Yanmar 4JH"
    assert entry["category"] == "Engine"
    assert entry["order"] == 5
    assert entry["description"] == "Start-up drill."


def test_non_numeric_order_falls_back_to_default(repo):
    path = write_doc(repo, "a.md", "---\norder: soon\n---\n# A\n")
    assert bdi.build_entry(repo, path)["order"] == bdi.DEFAULT_ORDER


def test_description_uses_first_prose_paragraph(repo):
    path = write_doc(
        repo,
        "rigging.md",
        "# Rigging\n\n> A quote\n\nThe standing rigging was replaced in 2021.\n\nSecond paragraph.\n",
    )
    assert bdi.build_entry(repo, path)["description"] == (
        "The standing rigging was replaced in 2021."
    )


def test_description_strips_links_and_emphasis(repo):
    path = write_doc(
        repo, "a.md", "# A\n\nSee **[the manual](http://x.example)** for detail.\n"
    )
    assert bdi.build_entry(repo, path)["description"] == "See the manual for detail."


def test_description_is_empty_for_a_doc_with_no_prose(repo):
    path = write_doc(repo, "checklist.md", "# Checklist\n\n- [ ] Flares in date\n")
    assert bdi.build_entry(repo, path)["description"] == ""


# ── Headings ────────────────────────────────────────────────────────────────


def test_headings_exclude_h1_and_code_fences(repo):
    path = write_doc(
        repo,
        "systems.md",
        "# Systems\n\n## Electrical\n\n```bash\n# not a heading\n```\n\n### Batteries\n",
    )
    headings = bdi.build_entry(repo, path)["headings"]
    assert headings == [
        {"level": 2, "text": "Electrical"},
        {"level": 3, "text": "Batteries"},
    ]


# ── Categories and ordering ─────────────────────────────────────────────────


def test_subdirectory_becomes_the_category(repo):
    path = write_doc(repo, "safety/mob.md", "# MOB\n")
    entry = bdi.build_entry(repo, path)
    assert entry["category"] == "Safety"
    assert entry["slug"] == "safety/mob"


def test_index_sorts_by_category_then_order_then_title(repo):
    write_doc(repo, "b.md", "---\norder: 2\n---\n# Bravo\n")
    write_doc(repo, "a.md", "---\norder: 1\n---\n# Alpha\n")
    write_doc(repo, "safety/mob.md", "# MOB\n")
    index = bdi.build_index(repo)
    assert [d["title"] for d in index["docs"]] == ["Alpha", "Bravo", "MOB"]


def test_underscore_prefixed_files_are_drafts_and_excluded(repo):
    write_doc(repo, "published.md", "# Published\n")
    write_doc(repo, "_draft.md", "# Draft\n")
    assert [d["title"] for d in bdi.build_index(repo)["docs"]] == ["Published"]


def test_missing_docs_directory_yields_an_empty_index(tmp_path):
    index = bdi.build_index(tmp_path)
    assert index["docs"] == []
    assert "generated" in index


# ── Output shape ────────────────────────────────────────────────────────────


def test_rendered_index_is_valid_json_ending_in_a_newline(repo):
    write_doc(repo, "a.md", "# Alpha\n\nSome words here.\n")
    output = bdi.render_index(bdi.build_index(repo))
    assert output.endswith("\n")
    parsed = json.loads(output)
    assert parsed["docs"][0]["title"] == "Alpha"
    assert parsed["docs"][0]["words"] > 0


# ── main(): writing and checking ────────────────────────────────────────────


@pytest.fixture
def cli(repo, monkeypatch):
    """Run main() against the temp repo instead of the real one."""
    monkeypatch.setattr(bdi, "get_project_root", lambda: repo)
    return repo / bdi.INDEX_FILE


def test_main_writes_the_index(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    assert bdi.main([]) == 0
    assert json.loads(cli.read_text(encoding="utf-8"))["docs"][0]["title"] == "Alpha"


def test_main_is_idempotent_when_nothing_changed(cli, repo):
    # Rewriting just to bump `generated` makes the pre-commit hook report
    # "files were modified" on every run and hands CI an empty dirty diff.
    write_doc(repo, "a.md", "# Alpha\n")
    bdi.main([])
    first = cli.read_bytes()
    assert bdi.main([]) == 0
    assert cli.read_bytes() == first


def test_main_rewrites_when_a_document_changes(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    bdi.main([])
    write_doc(repo, "a.md", "# Alpha Renamed\n")
    assert bdi.main([]) == 0
    assert json.loads(cli.read_text(encoding="utf-8"))["docs"][0]["title"] == (
        "Alpha Renamed"
    )


def test_check_fails_when_the_index_is_missing(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    assert bdi.main(["--check"]) == 1


def test_check_fails_when_the_index_is_stale(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    bdi.main([])
    write_doc(repo, "b.md", "# Bravo\n")
    assert bdi.main(["--check"]) == 1


def test_check_passes_when_the_index_matches(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    bdi.main([])
    assert bdi.main(["--check"]) == 0


def test_check_fails_on_a_corrupt_index_instead_of_raising(cli, repo):
    write_doc(repo, "a.md", "# Alpha\n")
    cli.write_text("{ truncated", encoding="utf-8")
    assert bdi.main(["--check"]) == 1
