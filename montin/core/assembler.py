"""
montin.core.assembler
=======================
Consumes a populated ``Deck`` instance and writes the final .html file.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import jinja2
from functools import lru_cache
from importlib.resources import files as _res_files

from montin.exceptions import SecurityError
from montin.utils.theme_resolver import ThemeResolver
from montin.utils.vendor import resolve_plugin

if TYPE_CHECKING:
    from montin.core.deck import Deck

# Resource-loading external URLs that must not appear when
# Security(block_external=True). We match things the browser *fetches* — `src=`
# (script/img/iframe/source/...), stylesheet `<link href>`, and CSS url()/@import
# — but deliberately NOT bare `<a href>` navigation links (clicking one is
# user-initiated and transfers no data on load). Trusted inlined library code is
# stripped before scanning (see _assert_no_external).
_RESOURCE_URL_RES = (
    re.compile(r"""\bsrc\s*=\s*["'](https?://[^"']+)""", re.I),
    re.compile(r"""<link\b[^>]*\bhref\s*=\s*["'](https?://[^"']+)""", re.I),
    re.compile(r"""(?:url\(\s*["']?|@import\s+["'])(https?://[^"')\s]+)""", re.I),
)


def _templates_dir() -> Path:
    return Path(str(_res_files("montin.templates")))


def _static_dir() -> Path:
    return Path(str(_res_files("montin.static")))


#: Deck JS modules, concatenated in this order into the inlined <script>.
#: ``state`` must come first (creates the Montin namespace) and ``boot`` last
#: (runs init once every module has registered). See montin/static/js/README.md.
MAIN_JS_MODULES = [
    "state", "toolbar", "stage", "zoom", "navigation", "keyboard", "view",
    "lightbox", "slider", "sidebar", "copy", "charts", "touch", "boot",
]


@lru_cache(maxsize=1)
def _read_main_js() -> str:
    """Concatenate the deck JS modules (montin/static/js) into one script.

    Cached: the modules are immutable package assets, and autosave re-renders
    the deck on every change — re-reading 14 files from disk each time is
    wasted IO. (Restart the process to pick up edits during development.)
    """
    js_dir = _static_dir() / "js"
    parts: list[str] = []
    for name in MAIN_JS_MODULES:
        path = js_dir / f"{name}.js"
        if path.exists():
            parts.append(f"/* --- js/{name}.js --- */")
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


class Assembler:
    def __init__(self, deck: "Deck", strict: bool = True) -> None:
        self.deck = deck
        self.strict = strict
        self._env = self._build_jinja_env()
        self._output_path: Path | None = None   # set by write(); None during previews
        # Cells whose media finalization failed under strict=False — they render
        # as visible error boxes instead of killing the whole deck.
        self._failed_cells: dict[int, Exception] = {}

    def write(self, path: Path) -> None:
        self._output_path = Path(path)
        html = self._render()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")

    # ------------------------------------------------------------------
    # Media finalization (WebP conversion + contents-folder saving)
    # ------------------------------------------------------------------

    def _contents_dir(self) -> Path | None:
        """Folder for saved assets, or ``None`` during previews (no output path).

        Resolved to ``deck.contents_folder`` (relative to the output file when
        not absolute), else ``<output_dir>/_<output_stem>_contents``. The folder
        itself is created lazily, only when an asset is actually written.
        """
        out = self._output_path
        if out is None:
            return None
        cf = self.deck.contents_folder
        if cf is not None:
            cf = Path(cf)
            return cf if cf.is_absolute() else out.parent / cf
        return out.parent / f"_{out.stem}_contents"

    def _finalize_media(self) -> None:
        """Run every cell's :meth:`Cell.finalize` with the current write context.

        Media resolution is polymorphic — the Assembler knows no concrete cell
        types, so a new media-bearing cell only implements ``finalize()``.
        """
        from montin.cells.base import RenderContext

        ctx = RenderContext(
            contents_dir=self._contents_dir(),
            out_dir=self._output_path.parent if self._output_path else None,
            self_contained=self.deck.self_contained,
        )
        for slide in self.deck._slides:
            for cell in slide._cells:
                try:
                    cell.finalize(ctx)
                except Exception as exc:
                    if self.strict:
                        raise
                    self._failed_cells[id(cell)] = exc

    def _build_jinja_env(self) -> jinja2.Environment:
        # Autoescape is ON: user data (titles, table values, captions, ...) is
        # HTML-escaped by default. Trusted, pre-rendered content (markdown HTML,
        # inlined JS/CSS, sanitised JSON) is marked with `| safe` in the
        # templates — unsafe injection is a visible opt-in, never the default.
        return jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(_templates_dir())),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # ------------------------------------------------------------------
    # Plugin asset resolution (CDN vs bundled) + security view-model
    # ------------------------------------------------------------------

    def _effective_source(self, plugin) -> str:
        """The "cdn"/"bundled" mode for ``plugin`` after defaults and security.

        ``block_external`` forces bundling; an *explicit* ``source="cdn"`` under
        ``block_external`` is a contradiction and raises.
        """
        source = plugin.source or self.deck.plugin_source
        if self.deck.security.block_external:
            if plugin.source == "cdn":
                raise SecurityError(
                    f"Plugin {plugin.name!r} is source='cdn' but "
                    f"Security(block_external=True) forbids external traffic. "
                    f"Drop the source override or set source='bundled'."
                )
            return "bundled"
        return source

    def _resolve_plugins(self) -> tuple[list[dict], dict]:
        """Resolve every declared plugin to template assets + init options.

        Returns ``(plugin_assets, plugin_opts)`` where ``plugin_assets`` is the
        ordered list of ``<script>``/``<link>`` descriptors and ``plugin_opts``
        maps a plugin name to its init options (e.g. mermaid theme).
        """
        sec = self.deck.security
        assets: list[dict] = []
        opts: dict = {}
        for plugin in self.deck.plugins:
            source = self._effective_source(plugin)
            resolved = resolve_plugin(
                plugin, source=source,
                self_contained=self.deck.self_contained, sri=sec.sri,
                deck_theme=self.deck.theme,
            )
            for asset in resolved["assets"]:
                assets.append(self._materialize_asset(asset))
            if resolved["options"]:
                opts[resolved["name"]] = resolved["options"]
        return assets, opts

    def _materialize_asset(self, asset: dict) -> dict:
        """Turn a resolved asset into one ready for the template.

        ``inline`` reads the vendored text; ``copy`` writes a sidecar file next
        to the report and references it (falling back to inline when there is no
        output path, e.g. during a notebook preview); ``src`` passes through.
        """
        mode = asset["mode"]
        if mode == "src":
            return asset

        if mode == "inline":
            return {"type": asset["type"], "mode": "inline",
                    "text": self._inline_text(asset)}

        # mode == "copy": bundled + not self_contained
        contents_dir = self._contents_dir()
        if contents_dir is None:   # preview (no output path) — inline instead
            return {"type": asset["type"], "mode": "inline",
                    "text": self._inline_text(asset)}
        contents_dir.mkdir(parents=True, exist_ok=True)
        dest = contents_dir / asset["filename"]
        shutil.copyfile(asset["path"], dest)
        rel = os.path.relpath(dest, self._output_path.parent).replace(os.sep, "/")
        return {"type": asset["type"], "mode": "src", "url": f"./{rel}" if not rel.startswith(".") else rel,
                "integrity": None}

    @staticmethod
    def _inline_text(asset: dict) -> str:
        """Read a vendored file for inlining, neutralising any ``</script>`` that
        would otherwise close the embedding tag early (defensive; current vendored
        bundles contain none)."""
        text = Path(asset["path"]).read_text(encoding="utf-8")
        if asset["type"] == "js":
            text = re.sub(r"</(script)", r"<\\/\1", text, flags=re.I)
        return text

    def _security_context(self) -> dict:
        """Flatten ``deck.security`` into the head-tag values the template needs."""
        sec = self.deck.security
        return {
            "csp":                sec.csp_content(),
            "permissions_policy": sec.permissions_policy_content(),
            "no_referrer":        sec.no_referrer,
            "noindex":            sec.noindex,
        }

    def _assert_no_external(self, html: str, trusted: list[str]) -> None:
        """Raise if ``block_external`` is on but the report would *fetch* an
        external resource on load.

        ``trusted`` holds the inlined library / main.js bodies, which are stripped
        before scanning: their internal URL *strings* are data, not loads, and are
        already neutralised by the strict CSP. Everything else — theme/custom CSS,
        cell content, images — is scanned for real resource URLs.
        """
        if not self.deck.security.block_external:
            return
        # Locate each trusted block's span instead of str.replace-ing it out —
        # replace copies the whole (potentially huge) document once per block.
        spans: list[tuple[int, int]] = []
        for block in trusted:
            if block:
                start = html.find(block)
                if start != -1:
                    spans.append((start, start + len(block)))
        hits = sorted({
            m.group(1)
            for rgx in _RESOURCE_URL_RES
            for m in rgx.finditer(html)
            if not any(s <= m.start() < e for s, e in spans)
        })
        if hits:
            raise SecurityError(
                "Security(block_external=True) but the report still loads "
                "external resources:\n  " + "\n  ".join(hits) +
                "\nEmbed them (self_contained=True / bundled plugins) or remove them."
            )

    def _encode_theme_image(self, src) -> str | None:
        """Resolve a logo/watermark image to a data URI (self-contained) or leave
        it as a path/URL. An external URL under ``block_external`` is caught later
        by :meth:`_assert_no_external`."""
        if src is None:
            return None
        if self.deck.self_contained:
            from montin.utils.image_encoder import encode
            try:
                return encode(src)
            except FileNotFoundError:
                return str(src)
        return str(src)

    def _theme_options_context(self) -> dict | None:
        """Flatten ``deck.theme_options`` into the template view-model for the
        rendered features (watermark, logos, footer, credit). Images are encoded
        here; colours/sizes come from ``ThemeOptions.to_css()``."""
        from montin.core.theme_options import _len

        opts = self.deck.theme_options
        if opts is None:
            return None

        wm = None
        if opts.watermark and (opts.watermark.text or opts.watermark.image):
            w = opts.watermark
            img = self._encode_theme_image(w.image) if w.image else None
            wm = {
                "mode":     "image" if img else "text",
                "text":     w.text or "",
                "img":      img,
                "position": w.position,
                "tiled":    w.position == "tiled" and img is not None,
            }

        logos: dict[str, list] = {"sidebar": [], "toolbar": [], "header": [], "cover": []}
        for lg in opts.logos():
            logos.setdefault(lg.placement, []).append({
                "img":    self._encode_theme_image(lg.image) if lg.image else None,
                "text":   lg.text or "",
                "height": _len(lg.height),
                "link":   lg.link,
            })

        return {
            "watermark": wm,
            "logos":     logos,
            "footer":    opts.footer,
            "credit":    opts.credit,
        }

    def _render_cell(self, cell) -> str:
        """Render one cell. Under ``strict=False`` a failing cell degrades to a
        visible error box (grid position preserved) instead of aborting the
        whole deck — one pathological figure in a 200-slide batch report must
        not cost the other 199 slides."""
        exc = self._failed_cells.get(id(cell))
        if exc is None:
            try:
                return cell.render(self._env)
            except Exception as render_exc:
                if self.strict:
                    raise
                exc = render_exc

        import html as _html
        import warnings
        warnings.warn(
            f"strict=False: cell {cell!r} failed to render and was replaced by "
            f"an error box: {exc}", stacklevel=2)
        p = cell.params
        return (
            f'<div class="cell cell-error" style="'
            f'grid-column: {p.col} / span {p.colspan}; '
            f'grid-row: {p.row} / span {p.rowspan};">'
            f'<div class="cell-body">'
            f'<p class="cell-error-title">&#9888; This cell failed to render</p>'
            f'<pre class="cell-error-detail">{_html.escape(repr(cell))}\n'
            f'{_html.escape(f"{type(exc).__name__}: {exc}")}</pre>'
            f'</div></div>'
        )

    def _render(self) -> str:
        deck = self.deck

        # CSS — theme merge (default → theme → theme_options → custom_css)
        options_css = deck.theme_options.to_css() if deck.theme_options else None
        css = ThemeResolver().resolve(deck.theme, deck.custom_css, options_css)

        # ThemeOptions rendered-feature view-model (watermark/logos/footer/credit)
        theme_ctx = self._theme_options_context()

        # Main JS — concatenated from the per-feature modules in montin/static/js
        main_js = _read_main_js()

        # Resolve media srcs (and optionally write assets to the contents folder)
        self._finalize_media()

        # Resolve plugin assets (CDN vs bundled) and security head-tag values
        plugin_assets, plugin_opts = self._resolve_plugins()
        security_ctx = self._security_context()

        # Build full TOC from registered sections
        toc_entries = [
            {
                "title":    s["title"],
                "subtitle": s.get("subtitle", ""),
                "level":    s["level"],
                "slide_id": s["slide_id"],
            }
            for s in deck._sections
        ]

        # Render cells + inject TOC entries per slide
        rendered_slides = []
        for slide in deck._slides:
            entries_for_template: list[dict] = []

            if slide.slide_type == "toc":
                auto = getattr(slide, "_auto_toc", True)
                slide._toc_entries = toc_entries if auto else []
                entries_for_template = list(slide._toc_entries)

            elif slide.slide_type == "section" and slide.show_toc and toc_entries:
                current_id = slide.slide_id
                current_idx = next(
                    (i for i, e in enumerate(toc_entries) if e["slide_id"] == current_id),
                    -1,
                )
                slide._toc_entries = toc_entries
                entries_for_template = [
                    {
                        **e,
                        "is_current":  i == current_idx,
                        "is_past":     i < current_idx,
                        "is_upcoming": i > current_idx,
                    }
                    for i, e in enumerate(toc_entries)
                ]

            rendered_cells = [self._render_cell(cell) for cell in slide._cells]
            rendered_slides.append({
                "slide":          slide,
                "rendered_cells": rendered_cells,
                "toc_entries":    entries_for_template,
            })

        # Per-slide footer text (fills {page}/{total}/{title} tokens). Done here so
        # it is static in the HTML — correct in print and fixed-size modes.
        if theme_ctx and theme_ctx["footer"] is not None:
            total = len(rendered_slides)
            for i, item in enumerate(rendered_slides, start=1):
                item["footer_text"] = deck.theme_options.footer_text_for(
                    i, total, item["slide"].title
                )

        html = self._env.get_template("base.html").render(
            deck=deck,
            rendered_slides=rendered_slides,
            css=css,
            main_js=main_js,
            plugins=deck.plugins,
            plugin_names=deck._plugin_names,
            plugin_assets=plugin_assets,
            plugin_opts=plugin_opts,
            security=security_ctx,
            theme_options=theme_ctx,
        )
        trusted = [a["text"] for a in plugin_assets if a.get("mode") == "inline"]
        trusted.append(main_js)
        self._assert_no_external(html, trusted)
        return html
