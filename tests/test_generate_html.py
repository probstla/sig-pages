"""Tests for .github/scripts/generate_html.py"""
import pytest
import generate_html


@pytest.fixture()
def docs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "docs"
    d.mkdir()
    return d


def read_html(tmp_path):
    return (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Creation from scratch
# ---------------------------------------------------------------------------

def test_creates_index_html_when_missing(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n\nContent\n")
    generate_html.main()
    assert (tmp_path / "docs" / "index.html").exists()


def test_full_template_contains_generated_markers(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()
    html = read_html(tmp_path)
    assert "<!-- GENERATED:NAV_START -->" in html
    assert "<!-- GENERATED:NAV_END -->" in html
    assert "<!-- GENERATED:MAIN_START -->" in html
    assert "<!-- GENERATED:MAIN_END -->" in html


def test_tab_button_rendered_for_md_file(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()
    assert 'data-tab="commits"' in read_html(tmp_path)


def test_tab_panel_rendered_for_md_file(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()
    assert 'id="tab-commits"' in read_html(tmp_path)


def test_no_phantom_empty_row_in_empty_table(docs, tmp_path):
    (docs / "commits.md").write_text(
        "# Commit Log\n\n| A | B |\n|---|---|\n<!-- COMMITS_START -->\n<!-- COMMITS_END -->\n"
    )
    generate_html.main()
    assert "<td></td>" not in read_html(tmp_path)


def test_table_rows_between_markers_rendered_as_tbody(docs, tmp_path):
    """Rows between COMMITS_START and COMMITS_END must land inside <tbody>, not as plain text."""
    (docs / "commits.md").write_text(
        "# Commit Log\n\n"
        "| Datum | Autor |\n"
        "|:------|:------|\n"
        "<!-- COMMITS_START -->\n"
        "| 2024-01-01 | Alice |\n"
        "| 2024-01-02 | Bob |\n"
        "<!-- COMMITS_END -->\n"
    )
    generate_html.main()
    html = read_html(tmp_path)
    assert "<tbody>" in html
    assert "<td" in html
    assert "Alice" in html
    assert "Bob" in html
    # rows must NOT fall through to a plain paragraph
    assert "| 2024-01-01 |" not in html


# ---------------------------------------------------------------------------
# Partial update — shell is preserved
# ---------------------------------------------------------------------------

def test_existing_title_is_preserved(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()

    # User customises the page title
    path = tmp_path / "docs" / "index.html"
    path.write_text(
        path.read_text().replace("<title>Project Docs</title>", "<title>My Docs</title>")
    )

    generate_html.main()
    assert "<title>My Docs</title>" in read_html(tmp_path)


def test_stylesheet_link_present(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()
    assert 'href="style.css"' in read_html(tmp_path)


def test_no_inline_style_block_in_generated_html(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()
    assert "<style>" not in read_html(tmp_path)


def test_new_tab_appears_after_adding_md_file(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    generate_html.main()

    (docs / "about.md").write_text("# About\n\nInfo here.\n")
    generate_html.main()

    html = read_html(tmp_path)
    assert 'data-tab="about"' in html
    assert 'id="tab-about"' in html


def test_removed_md_file_disappears_from_html(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    (docs / "temp.md").write_text("# Temporary\n")
    generate_html.main()
    assert 'data-tab="temp"' in read_html(tmp_path)

    (docs / "temp.md").unlink()
    generate_html.main()
    assert 'data-tab="temp"' not in read_html(tmp_path)


# ---------------------------------------------------------------------------
# Tab ordering
# ---------------------------------------------------------------------------

def test_commits_md_tab_always_first(docs, tmp_path):
    (docs / "zebra.md").write_text("# Zebra\n")
    (docs / "commits.md").write_text("# Commit Log\n")
    (docs / "about.md").write_text("# About\n")
    generate_html.main()

    html = read_html(tmp_path)
    assert html.index('data-tab="commits"') < html.index('data-tab="about"')
    assert html.index('data-tab="commits"') < html.index('data-tab="zebra"')


def test_non_commits_tabs_are_alphabetical(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    (docs / "zebra.md").write_text("# Zebra\n")
    (docs / "apple.md").write_text("# Apple\n")
    generate_html.main()

    html = read_html(tmp_path)
    assert html.index('data-tab="apple"') < html.index('data-tab="zebra"')


# ---------------------------------------------------------------------------
# Tab titles
# ---------------------------------------------------------------------------

def test_title_from_first_h1(docs, tmp_path):
    (docs / "page.md").write_text("# Custom Heading\n\nContent\n")
    generate_html.main()
    assert "Custom Heading" in read_html(tmp_path)


def test_title_fallback_to_capitalised_filename(docs, tmp_path):
    (docs / "my_page.md").write_text("No heading here.\n")
    generate_html.main()
    assert "My Page" in read_html(tmp_path)


def test_title_fallback_hyphen_filename(docs, tmp_path):
    (docs / "release-notes.md").write_text("Content without heading.\n")
    generate_html.main()
    assert "Release Notes" in read_html(tmp_path)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_no_md_files_produces_no_output(docs, tmp_path, capsys):
    generate_html.main()
    assert not (tmp_path / "docs" / "index.html").exists()
    assert "nothing generated" in capsys.readouterr().out


def test_fallback_to_full_regen_when_markers_missing(docs, tmp_path):
    (docs / "commits.md").write_text("# Commit Log\n")
    # Write a broken index.html without markers
    (tmp_path / "docs" / "index.html").write_text("<html><body>broken</body></html>")
    generate_html.main()
    html = read_html(tmp_path)
    assert "<!-- GENERATED:NAV_START -->" in html
    assert 'data-tab="commits"' in html


def test_replace_section_raises_on_missing_marker():
    with pytest.raises(ValueError, match="GENERATED:FOO"):
        generate_html.replace_section("<html>no markers</html>", "FOO", "content")
