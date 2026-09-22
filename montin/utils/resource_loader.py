"""
montin.utils.resource_loader
==============================
Locates package assets (templates, themes, static) via importlib.resources.
Works correctly in both installed and editable (pip install -e) modes.
"""

from __future__ import annotations

from pathlib import Path

try:
    from importlib.resources import files  # Python 3.9+
except ImportError:  # pragma: no cover
    from importlib_resources import files  # type: ignore[no-redef]


def get_template(name: str) -> Path:
    return Path(str(files("montin.templates").joinpath(name)))


def get_theme_file(theme: str, filename: str) -> Path:
    return Path(str(files("montin.themes").joinpath(theme, filename)))


def get_static(name: str) -> Path:
    return Path(str(files("montin.static").joinpath(name)))


def theme_file_exists(theme: str, filename: str) -> bool:
    p = get_theme_file(theme, filename)
    return p.exists()

def get_available_themes() -> list:
    return list(filter(
        lambda f: f.is_dir() and not str(f.name).startswith('_'),
        Path(str(files("montin.themes"))).glob('*')
    ))


def theme_is_dark(theme: str) -> bool:
    """Whether ``theme`` declares itself dark in its ``theme.json`` metadata.

    Every built-in theme ships a ``theme.json`` with ``{"dark": true|false}``.
    A theme without the file (or with malformed JSON) is treated as light —
    the majority case — so plugin stylesheets that follow the deck theme
    (e.g. Tabulator's ``theme="auto"``) never key off hardcoded theme names.
    """
    import json

    p = get_theme_file(theme, "theme.json")
    if not p.exists():
        return False
    try:
        return bool(json.loads(p.read_text(encoding="utf-8")).get("dark", False))
    except (OSError, ValueError):
        return False
