"""Tests for .github/scripts/append_commit.py"""
import pytest
import append_commit


COMMIT_DEFAULTS = {
    "COMMIT_SHA":       "abc1234def5678901234",
    "COMMIT_AUTHOR":    "Test User",
    "COMMIT_MESSAGE":   "Fix: something important",
    "COMMIT_TIMESTAMP": "2024-01-15T10:30:00Z",
    "COMMIT_URL":       "https://github.com/owner/repo/commit/abc1234",
    "BRANCH_NAME":      "main",
}


@pytest.fixture()
def commit_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    for key, val in COMMIT_DEFAULTS.items():
        monkeypatch.setenv(key, val)
    return tmp_path


def read_commits_md(tmp_path):
    return (tmp_path / "docs" / "commits.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------

def test_creates_docs_dir_and_file_when_missing(commit_env):
    append_commit.main()
    assert (commit_env / "docs" / "commits.md").exists()


def test_initial_file_contains_table_header(commit_env):
    append_commit.main()
    content = read_commits_md(commit_env)
    assert "| Datum |" in content
    assert "| Autor |" in content


# ---------------------------------------------------------------------------
# Append behaviour
# ---------------------------------------------------------------------------

def test_appends_short_sha(commit_env):
    append_commit.main()
    assert "abc1234" in read_commits_md(commit_env)


def test_appends_author(commit_env):
    append_commit.main()
    assert "Test User" in read_commits_md(commit_env)


def test_appends_message(commit_env):
    append_commit.main()
    assert "Fix: something important" in read_commits_md(commit_env)


def test_appends_branch(commit_env):
    append_commit.main()
    assert "`main`" in read_commits_md(commit_env)


def test_marker_stays_after_append(commit_env):
    append_commit.main()
    assert append_commit.MARKER in read_commits_md(commit_env)


def test_multiple_appends_preserve_order(commit_env, monkeypatch):
    append_commit.main()
    monkeypatch.setenv("COMMIT_SHA", "zzz9999aaa0000bbbb11")
    monkeypatch.setenv("COMMIT_MESSAGE", "Second commit")
    append_commit.main()

    content = read_commits_md(commit_env)
    assert content.index("abc1234") < content.index("zzz9999")


def test_appends_to_existing_file_with_custom_content(commit_env):
    docs = commit_env / "docs"
    docs.mkdir()
    (docs / "commits.md").write_text(
        "# Log\n\n| A | B |\n|---|---|\n| old | row |\n<!-- COMMITS_END -->\n",
        encoding="utf-8",
    )
    append_commit.main()
    content = read_commits_md(commit_env)
    assert "old | row" in content
    assert "abc1234" in content


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------

def test_pipe_in_message_is_escaped(commit_env, monkeypatch):
    monkeypatch.setenv("COMMIT_MESSAGE", "fix: a | b | c")
    append_commit.main()
    content = read_commits_md(commit_env)
    assert "fix: a | b | c" not in content
    assert "&#124;" in content


def test_pipe_in_author_is_escaped(commit_env, monkeypatch):
    monkeypatch.setenv("COMMIT_AUTHOR", "Name|With|Pipes")
    append_commit.main()
    content = read_commits_md(commit_env)
    assert "Name|With|Pipes" not in content
    assert "&#124;" in content


def test_multiline_message_uses_only_first_line(commit_env, monkeypatch):
    monkeypatch.setenv("COMMIT_MESSAGE", "Subject line\n\nBody paragraph")
    append_commit.main()
    content = read_commits_md(commit_env)
    assert "Subject line" in content
    assert "Body paragraph" not in content


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_missing_marker_raises(commit_env):
    docs = commit_env / "docs"
    docs.mkdir()
    (docs / "commits.md").write_text("# Log\n\nNo marker here.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="COMMITS_END"):
        append_commit.main()
