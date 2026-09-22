"""
montin.utils.theme_resolver
==============================
Resolves and merges CSS files per component following the hierarchy:
  1. default/
  2. user-chosen theme
  3. custom_css provided via Python
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from montin.utils.resource_loader import (
    get_theme_file, theme_file_exists, get_available_themes)

#: CSS components recognised by the theme system.
CSS_COMPONENTS = [
    "image",
    "layout",
    "slide",
    "table",
    "tabulator",
    "list",
    "toc",
    "code",
    "metric",
    "toolbar",
]


@lru_cache(maxsize=None)
def _theme_base_css(theme: str) -> str:
    """The merged ``default -> theme`` component CSS for ``theme``.

    Cached: theme files are immutable package assets, and autosave re-renders
    the deck on every change — re-reading ~10 CSS files from disk each time is
    wasted IO. Only the per-deck layers (theme_options / custom_css) vary, and
    those are merged uncached in :meth:`ThemeResolver.resolve`.
    """
    from montin.exceptions import ThemeNotFoundError

    parts: list[str] = []
    for component in CSS_COMPONENTS:
        filename = f"{component}.css"

        # 1. default
        default_path = get_theme_file("default", filename)
        if default_path.exists():
            parts.append(f"/* --- default/{filename} --- */")
            parts.append(default_path.read_text(encoding="utf-8"))

        # 2. chosen theme (overrides if present)
        if theme != "default":
            theme_dir = get_theme_file(theme, "layout.css").parent
            if not theme_dir.exists():
                raise ThemeNotFoundError(
                    f"Theme '{theme}' not found. "
                    f"Expected folder: {theme_dir}"
                    f"\nAvailable themes:\n-"
                    + '\n-'.join([f.name for f in get_available_themes()])
                )
            if theme_file_exists(theme, filename):
                parts.append(f"/* --- {theme}/{filename} --- */")
                parts.append(
                    get_theme_file(theme, filename).read_text(encoding="utf-8")
                )
    return "\n".join(parts)


class ThemeResolver:
    def resolve(
        self,
        theme: str,
        custom_css: Path | None = None,
        options_css: str | None = None,
    ) -> str:
        """
        Returns a single CSS string with all components merged.
        Hierarchy: default → theme → theme_options → custom_css.

        ``options_css`` is the CSS emitted by ``ThemeOptions.to_css()``; it is
        placed after the theme and before ``custom_css`` so structured options
        override the theme but ``custom_css`` still wins.
        """
        parts: list[str] = [_theme_base_css(theme)]

        # 3. structured theme_options (override the theme, below custom_css).
        if options_css:
            parts.append("/* --- theme_options --- */")
            parts.append(options_css)

        # 4. user custom_css — a path to a .css file, or an inline CSS string.
        # Never cached: the file may be hand-edited between autosave writes.
        custom = self._load_custom_css(custom_css)
        if custom:
            parts.append("/* --- custom_css --- */")
            parts.append(custom)

        return "\n".join(parts)

    @staticmethod
    def _load_custom_css(custom_css: "str | Path | None") -> str | None:
        """Resolve ``custom_css`` to CSS text.

        A ``Path`` (or a ``str`` naming an existing file) is read from disk; any
        other ``str`` is treated as inline CSS. Guarded so a multi-line CSS
        string — never a valid path — doesn't raise while probing the filesystem.
        """
        if custom_css is None:
            return None
        if isinstance(custom_css, Path):
            return custom_css.read_text(encoding="utf-8") if custom_css.exists() else None
        try:
            path = Path(custom_css)
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except (OSError, ValueError):
            pass  # e.g. an inline CSS string is not a filesystem path
        return custom_css
