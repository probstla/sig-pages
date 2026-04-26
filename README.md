# sig-pages

Automatisierte GitHub-Pages-Dokumentation via GitHub Actions. Bei jedem Push auf `main` wird der Commit-Log aktualisiert, alle Markdown-Dateien in eine interaktive HTML-Seite konvertiert und auf GitHub Pages deployt.

## Ablauf

```mermaid
flowchart TD
    A([Push auf main]) --> B{Workflow-Auslöser}
    B -->|push| C[append_commit.py]
    B -->|workflow_dispatch| E[generate_html.py]

    C --> C1{Schutzprüfung}
    C1 -->|Autor = github-actions\noder #nopagesupdate| Z([Abbruch])
    C1 -->|Normaler Commit| C2[Commit-Metadaten lesen\nGitHub Actions Umgebungsvariablen]
    C2 --> C3[Zeile an docs/commits.md anhängen\nvor COMMITS_END-Marker einfügen]
    C3 --> E

    E --> E1[Alle .md-Dateien aus docs/ lesen]
    E1 --> E2[Markdown → HTML konvertieren\nmit Tables, Code, TOC-Extensions]
    E2 --> E3{docs/index.html\nvorhanden?}
    E3 -->|Nein| E4[Vollständige HTML-Seite\nerstellen]
    E3 -->|Ja, Marker vorhanden| E5[Partielles Update\nNav + Inhalt ersetzen,\nAnpassungen behalten]
    E3 -->|Ja, Marker fehlen| E4
    E4 --> F
    E5 --> F

    F[docs/ committen & pushen\nmit #nopagesupdate-Tag]
    F --> G[deploy-Job]
    G --> H[docs/ als Artifact hochladen]
    H --> I([GitHub Pages live])
```

## Projektstruktur

```
sig-pages/
├── .github/
│   ├── scripts/
│   │   ├── append_commit.py   # Schreibt Commit-Zeile in docs/commits.md
│   │   └── generate_html.py   # Konvertiert .md-Dateien → docs/index.html
│   └── workflows/
│       └── pages.yml          # CI/CD-Workflow
├── docs/
│   ├── commits.md             # Automatisch gepflegter Commit-Log
│   ├── index.html             # Generierte Tab-Seite
│   └── style.css              # GitHub-Dark-Theme-Styles
├── tests/                     # pytest-Tests für beide Skripte
└── pyproject.toml
```

## Schutz vor Endlosschleifen

Der Workflow überspringt `append_commit.py`, wenn:
- der Commit-Autor `github-actions[bot]` ist, oder
- die Commit-Nachricht `#nopagesupdate` enthält.

Dadurch wird verhindert, dass der automatische Commit einen weiteren Workflow-Lauf auslöst.

## Lokale Entwicklung

```bash
# Abhängigkeiten installieren
uv sync

# Tests ausführen
uv run pytest

# HTML manuell generieren
uv run python .github/scripts/generate_html.py
```
