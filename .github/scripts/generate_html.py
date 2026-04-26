#!/usr/bin/env python3
"""
Generates docs/index.html from all *.md files in docs/.

- If docs/index.html does not yet exist: writes the complete page from the
  built-in template.
- If docs/index.html already exists: replaces only the nav and main sections
  (between the <!-- GENERATED:* --> markers), leaving the rest of the file
  (custom title, CSS overrides, extra scripts …) untouched.

Each Markdown file becomes one tab. commits.md is always first,
remaining files follow in alphabetical order.
"""
import glob
import os
import re

import markdown

DOCS_DIR = "docs"
OUTPUT   = "docs/index.html"

_MARKER_RE = re.compile(r"^<!--\s*COMMITS_(?:START|END)\s*-->\n?", re.MULTILINE)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def get_title(md_content: str, filepath: str) -> str:
    for line in md_content.splitlines():
        if line.strip().startswith("# "):
            return line.strip()[2:].strip()
    base = os.path.splitext(os.path.basename(filepath))[0]
    return base.replace("-", " ").replace("_", " ").title()


def convert(md_content: str) -> str:
    clean = _MARKER_RE.sub("", md_content)
    html  = markdown.markdown(
        clean,
        extensions=["tables", "fenced_code", "toc", "nl2br"],
    )
    # The markdown `tables` extension emits a phantom empty <tr> when a table
    # has no data rows (only a header + separator). Strip those rows.
    html = re.sub(r"<tr>\n(?:<td[^>]*></td>\n)+</tr>\n?", "", html)
    return html


def collect_tabs() -> list[dict]:
    md_files = sorted(glob.glob(f"{DOCS_DIR}/*.md"))
    md_files.sort(key=lambda f: (0 if os.path.basename(f) == "commits.md" else 1, f))
    tabs = []
    for path in md_files:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()
        tab_id = os.path.splitext(os.path.basename(path))[0]
        tabs.append(
            {
                "id":    tab_id,
                "title": get_title(content, path),
                "html":  convert(content),
            }
        )
    return tabs


# ---------------------------------------------------------------------------
# HTML building
# ---------------------------------------------------------------------------

def build_buttons(tabs: list[dict]) -> str:
    lines = []
    for i, tab in enumerate(tabs):
        active   = " active" if i == 0 else ""
        selected = "true" if i == 0 else "false"
        lines.append(
            f'        <button role="tab" class="tab-btn{active}" '
            f'data-tab="{tab["id"]}" aria-selected="{selected}">'
            f'{tab["title"]}</button>'
        )
    return "\n".join(lines)


def build_panels(tabs: list[dict]) -> str:
    parts = []
    for i, tab in enumerate(tabs):
        active = " active" if i == 0 else ""
        parts.append(
            f'        <section role="tabpanel" id="tab-{tab["id"]}" '
            f'class="tab-panel{active}">\n'
            f'{tab["html"]}\n'
            f'        </section>'
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Partial-update helper
# ---------------------------------------------------------------------------

def replace_section(html: str, name: str, content: str) -> str:
    """Replace the content between <!-- GENERATED:<name>_START/END --> markers."""
    start = f"<!-- GENERATED:{name}_START -->"
    end   = f"<!-- GENERATED:{name}_END -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{content}\n{end}"
    result, count = pattern.subn(replacement, html)
    if count == 0:
        raise ValueError(f"Markers for GENERATED:{name} not found in {OUTPUT}")
    return result


# ---------------------------------------------------------------------------
# Full-page template (used only when index.html does not yet exist)
# ---------------------------------------------------------------------------

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Docs</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>Project Docs</h1>
    </header>

    <nav class="tab-nav" role="tablist" aria-label="Dokumenten-Tabs">
<!-- GENERATED:NAV_START -->
TAB_BUTTONS_PLACEHOLDER
<!-- GENERATED:NAV_END -->
    </nav>

    <main>
<!-- GENERATED:MAIN_START -->
TAB_PANELS_PLACEHOLDER
<!-- GENERATED:MAIN_END -->
    </main>

    <footer>Generiert aus Markdown-Dateien &bull; aktualisiert bei jedem Push</footer>

    <script>
        const buttons = document.querySelectorAll('.tab-btn');
        const panels  = document.querySelectorAll('.tab-panel');

        function activate(id) {
            buttons.forEach(b => {
                const on = b.dataset.tab === id;
                b.classList.toggle('active', on);
                b.setAttribute('aria-selected', String(on));
            });
            panels.forEach(p => p.classList.toggle('active', p.id === 'tab-' + id));
            history.replaceState(null, '', '#' + id);
        }

        buttons.forEach(b => b.addEventListener('click', () => activate(b.dataset.tab)));

        // Restore tab from URL hash on load
        const hash = location.hash.slice(1);
        const initial = hash && document.getElementById('tab-' + hash)
            ? hash
            : (buttons[0] && buttons[0].dataset.tab);
        if (initial) activate(initial);
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    tabs = collect_tabs()
    if not tabs:
        print(f"No *.md files found in {DOCS_DIR}/ — nothing generated.")
        return

    nav_html  = build_buttons(tabs)
    main_html = build_panels(tabs)

    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r", encoding="utf-8") as fh:
            existing = fh.read()
        try:
            html = replace_section(existing, "NAV", nav_html)
            html = replace_section(html,     "MAIN", main_html)
        except ValueError as exc:
            print(f"WARNING: {exc} — falling back to full page regeneration.")
            html = PAGE_TEMPLATE.replace("TAB_BUTTONS_PLACEHOLDER", nav_html) \
                                 .replace("TAB_PANELS_PLACEHOLDER",  main_html)
    else:
        html = PAGE_TEMPLATE.replace("TAB_BUTTONS_PLACEHOLDER", nav_html) \
                             .replace("TAB_PANELS_PLACEHOLDER",  main_html)

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    titles = [t["title"] for t in tabs]
    print(f"Generated {OUTPUT}  ({len(tabs)} tab(s): {titles})")


if __name__ == "__main__":
    main()
