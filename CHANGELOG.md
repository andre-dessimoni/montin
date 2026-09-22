All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- **`ThemeOptions` — structured theme customization** passed as
  `Deck(theme_options=…)`. Nested option groups (`Header`, `Bars`, `Cells`,
  `Fonts`, `Footer`, `Watermark`, `Logo`) cover header style/colour, subtitle
  style, sidebar/toolbar colours, cell spacing/rounding, fonts, a per-slide
  footer (with `{page}`/`{total}`/`{title}` tokens), a text/image watermark, one
  or more logos (sidebar/toolbar/header/cover), and a switch to hide the
  "Made with Montin" credit. It sits between the theme and `custom_css` in the
  cascade. Logo/watermark images embed as data URIs (offline-safe under
  `Security(block_external=True)`). New `Deck.render_css()` / `Deck.export_css()`
  export the whole computed stylesheet to reuse via `custom_css`. Documented in
  the *Themes* guide with live examples.
- **Brand themes.** New built-in themes carry the Montin palette: **`montin`**
  (Sand background / Ink text / orange Accent) and **`ink`**, its dark
  counterpart (Ink background / Sand text). The original deep-navy-with-pink-red
  look is preserved as **`midnight`**. New *Themes* guide documents the built-ins,
  the CSS-variable system, and how to reskin a deck with `custom_css` or a custom
  theme folder.
- **Resilient rendering — `write(strict=False)` / `render(strict=False)`.** A
  cell that fails to render degrades to a visible error box (with the exception
  message) in its grid slot while every other slide is still written — for
  unattended batch jobs where one pathological figure must not cost the whole
  report. The default `strict=True` still raises.

### Changed
- **The default theme now matches the documentation site** (a clean light look —
  white content, grey sidebar, blue links, Inter/Sora), equivalent to `"docs"`.
  The previous default (brand Sand) moved to `theme="montin"`.
- **Slide-title underline spans the full header width** by default (the accent
  ruler now reaches the right margin instead of stopping at the title text).
- **Documentation-site themes.** `theme="docs"` and `theme="docs-dark"` render a
  deck to match the Montin documentation site (built with Furo) — white content
  with a grey sidebar / blue links in light, the `#131416` dark surface in dark,
  Inter body + Sora headings — so a report can sit visually alongside your docs.
- **Inline `custom_css` now works.** A CSS string passed to `Deck(custom_css=...)`
  is applied inline (it was silently dropped before, being coerced to a path);
  a path to a `.css` file still loads from disk.
- **Load a saved Plotly chart.** `slide.add_plotly(...)` now also accepts a path
  to an HTML file produced by `fig.write_html()`: the embedded figure JSON is
  extracted and rendered as a native interactive chart (not an iframe). Renders
  even when plotly is not installed (the figure is restored from the file).
- **Save & load (JSON).** Serialise a report's structure/data to JSON and load it
  back: `cell.export()` / `slide.export()` / `deck.export_slides(by_pos=…, by_key=…)`
  / `deck.export()`, and `slide.import_cell()` / `deck.import_slides()` /
  `Cell.from_file()` / `Slide.from_file()` / `Deck.from_file()`, plus the
  `to_dict()` / `from_dict()` helpers on `Cell`, `Slide`, and `Deck`. A reloaded
  object renders identically — and reloads even without the libraries that
  produced it (matplotlib/Plotly charts are restored from their rendered form).
  `embed=` toggles inline media vs. file references; `compress=` (or a `.gz`
  suffix) writes gzip, read back transparently. `Slide` and `Cell` are now
  importable from the top level (`from montin import Slide, Cell`).
- **Touchscreen gestures**: Sweeping change slides and pinching applies zoom.
- **Small screen friendly toolbar and sidebar**: Toolbar buttons now collapse in
  rows when it does not fit the screen space, and sidebar hides it top title.
- **Printing / PDF export**: The deck now prints (Ctrl+P / Save as PDF) with one
  slide per page and no sidebar or toolbar.
- **Vendored plugin libraries are declared entirely in `manifest.json`**
  (`assets`, `variants` and per-file `sri`). Adding a plugin now takes a `Plugin`
  subclass plus a manifest entry — the resolver and `scripts/update_vendor.py`
  need no changes.

### Fixed
- `add_tabulator(selectable=…)` and `spreadsheet_mode=True` sent their range
  selection and clipboard options to Tabulator as one-element arrays (stray
  trailing commas), breaking them.
- `Plugins.Tabulator(theme="auto")` now follows each theme's light/dark
  declaration (the new `theme.json`) instead of hard-coded theme names: light
  themes — including the new default — get the light table stylesheet, and
  `ink` / `midnight` / `docs-dark` get the dark one.
- A notebook preview no longer prevents a later `write()` from saving
  `save_source=True` side files (the preview's inlined result was reused).

### Security
- **HTML autoescaping is on by default.** Titles, subtitles, captions, table
  values and other user data are HTML-escaped, so `<`, `>`, `&` and quotes
  render literally instead of breaking — or injecting into — the markup.
  `add_html()` remains the explicit raw-HTML path, and `add_text(markdown=False)`
  now escapes its input as documented. Slide ids are JSON-encoded inside the
  inline navigation handlers, and the Plotly figure JSON travels in a
  `<script type="application/json">` block with `<` / `>` escaped.

## [0.5.0] - 2026-06-22

### Added

- **Font scaling.** `Deck(fontsize_scale=…)` scales every font in the
  presentation — slide content and navigation chrome alike — by one factor,
  leaving spacing/layout untouched. Per-cell `slide.add_*(…, fontscale=…)` (and
  `CellDefaults(fontscale=…)`) scales a single cell's text and composes on top of
  the deck factor.
- **Interactive tables — `slide.add_tabulator()`** (new `Plugins.Tabulator()`),
  backed by the bundled [Tabulator](https://tabulator.info) library (MIT). Sort,
  filter, paginate, group, edit inline, and download (CSV/JSON). Takes the same
  inputs as `add_table` — and both now also accept a **path to a CSV/TSV file**.
  Per-column formatters/editors/calcs go through `columns=[...]`; the full
  Tabulator option set is reachable via `options={...}`. Two stock themes are
  vendored (light + dark); styling follows the deck theme automatically
  (`Plugins.Tabulator(theme="auto"|"light"|"dark")`). Works offline /
  under `Security(block_external=True)`.
- **Bundled (offline) plugins.** Each plugin can load from a CDN (`source="cdn"`,
  default) or be embedded in the report (`source="bundled"`) so it works with no
  network at all. Flip the whole deck with `Deck(plugin_source="bundled")`. The
  embedded libraries are vendored under `montin/static/vendor/<library>/` — each
  alongside its `LICENSE` (Plotly/Mermaid MIT, highlight.js BSD-3-Clause, MathJax
  Apache-2.0) — and refreshed by the dev script `scripts/update_vendor.py` (which
  fetches code + licenses, with a `--check` mode and an update log).
- **Per-plugin classes via the `Plugins` container** — `Plugins.Plotly()`,
  `Plugins.Mermaid(theme=...)`, `Plugins.Highlight(style=...)`,
  `Plugins.MathJax(output=...)` — each with its own typed options, plus
  `version=` / `url=` / `set_cdn()` to pin a version or point at a custom mirror.
- **`Security(...)` hardening**, passed as `Deck(security=...)`. Light hardening is
  on by default (`no-referrer`, `Permissions-Policy`, and Subresource-Integrity on
  CDN libraries). `block_external=True` is a hard offline guarantee: it forces all
  plugins to bundle, emits a strict Content-Security-Policy, and raises
  `SecurityError` if the rendered report still references any external resource.
  New docs: *Plugins* and *Security & offline use*.
- `notebook_unique=True` on `add_slide`/`add_title`/`add_section`/`add_toc` and
  every cell `add_*`: re-running the *same* Jupyter cell replaces the items it
  created instead of duplicating them — no manual id needed. Keys off the Jupyter
  cell id; warns (and falls back) in a script, errors in an interactive session
  that can't supply one.
- `Deck(preview_height=...)` to set the notebook `_repr_html_` iframe height,
  propagated to slide and cell previews.
- WebP support for images and figures: `to_webp=True` / `webp_quality=` on
  `add_image`, `add_matplotlib`, `add_image_slider` (requires the new optional
  `pillow` dependency: `pip install 'montin[image]'`).
- Contents folder: `Deck(contents_folder=...)` plus `save_source=True` on the
  media `add_*` (incl. `add_plotly`, which exports a standalone HTML). Saves
  assets to `_<report>_contents/` (created lazily). When the deck is
  self-contained the asset is still embedded *and* saved; otherwise the cell
  references the saved file.
- `add_image` and `add_image_slider` now accept matplotlib `Figure` objects
  (routed through the matplotlib pipeline).

### Changed

- **Optional-dependency extras now cover only what Montin itself imports.**
  `[full]` is `markdown-it-py` + `pillow`; the standalone `[plotly]` and
  `[pandas]` extras were removed. You build `Figure`/`DataFrame` objects yourself,
  so those libraries are already present when you call `add_plotly`/`add_table`/
  `add_matplotlib` — they're now pulled only by `[dev]` for the test suite.
- **`add_matplotlib` now defaults to `fmt="svg"`** (was `"png"`) — crisp, vector,
  infinitely zoomable. Use `fmt="webp"`/`to_webp=True` for dense plots where SVG
  gets large.
- Plotly charts now read the active theme's CSS variables for text/grid colours,
  fixing invisible chart text on light themes.
- Arrow-key / prev-next navigation now steps into a collapsed section (auto-
  expanding it) instead of skipping over it; search-filtered slides are still
  skipped.

### Fixed

- `add_*` cell methods now expose their real signatures to type checkers and
  editors (Pylance/pyright) instead of collapsing to `(...) -> Cell`. The
  `@cell_method` decorator is now signature-preserving (`ParamSpec`/`TypeVar`),
  so parameters and concrete return types show up in autocomplete and hovers.
- Title and section cover slides are now centered in fixed-size (`size=`) mode.
  The centering had relied on the `.slide` being the flex container, but in
  fixed-size mode that role moved to `.stage`, so covers rendered top-left;
  the cover now centers itself via `margin:auto`, working in both modes.

## [0.4.0] - 2026-06-17

### Changed (breaking)

- **Renamed the main class `HTMLSlides` → `Deck`** (no alias; update
  `from montin import HTMLSlides` to `from montin import Deck`). The internal
  module `montin.core.slides` moved to `montin.core.deck`.
- **Replaced the flat `Plugin(name, source)` with the `Plugins.*` classes.**
  Update `Plugin("plotly", "cdn")` to `Plugins.Plotly(source="cdn")` (or just
  `Plugins.Plotly()` — the default source is now `"cdn"`). `Plugin` remains as the
  shared base type. Added `Deck(plugin_source=...)` to set the default for all
  plugins at once.
- Repositioned the library toward **self-contained, interactive HTML reports for
  batch-generated data/ML output** (was framed as "HTML slideshows").
- Fixed `__version__` resolution, which previously looked up the wrong
  distribution name and always fell back to `0.0.0.dev`.

### Added

- `_repr_html_` on `Deck`, `Slide`, and `Cell` for inline previews in
  Jupyter notebooks: return a deck, slide, or cell as a cell's last expression to
  render it in a sandboxed iframe (slide/cell previews are chrome-free and reuse
  the deck's theme and plugins).
- Sidebar fold toolbar: Collapse all / Expand all / Collapse level / Expand level
  buttons (shown when `sidebar_collapsible_sections` is on). The level buttons
  fold/unfold one nesting layer per click.
- Sidebar search regex toggle (literal matching by default; click `.*` to switch
  to regex), with a hover tooltip of common regex patterns while in regex mode.
  The chosen mode is remembered across reloads.

### Changed

- Sidebar arrow-key / prev-next navigation now steps only over *visible* items,
  skipping slides hidden by an active search filter or a collapsed section.
- Slightly enlarged the section fold caret for legibility.

## [0.3.0] - 2026-06-15

### Added

- `title_id`, `section_id`, and `toc_id` parameters on `add_title`, `add_section`,
  and `add_toc`, mirroring `slide_id` — re-running a notebook cell replaces the
  slide in place instead of appending a duplicate. Overwriting a section also
  updates its table-of-contents entry in place rather than duplicating it.
- Fixed-size "stage" mode: pass `size=(width, height)` to `Deck` to render
  slides at fixed pixel dimensions, scaled with a CSS transform to fit the window
  — fonts, images, and layout scale together like a static PDF. Options:
  `scale_up` (allow growing past 1:1) and `keep_aspect_ratio` (uniform letterbox
  vs. stretch-to-fill). Modal and lightbox stay unscaled.
- `show_sidebar` and `show_toolbar` options on `Deck` (both default
  `True`). Disable them for clean single-slide / embeddable files — e.g. the
  slides shown inline in the documentation.
- `sidebar_collapsed` option on `Deck` (default `False`) to start with the
  sidebar collapsed while keeping it toggleable. A remembered toggle state takes
  precedence over this default.
- Sidebar navigation aids: a regex **search box** that live-filters slides
  (`sidebar_search`, default `True`; `sidebar_search_scope` of `"title"` /
  `"title_subtitle"` / `"content"`) and **collapsible sections** with a fold
  caret on section items (`sidebar_collapsible_sections`, default `True`).
  Collapsed state is remembered across reloads; an active search overrides it.

### Fixed

- Overwriting a slide or cell by id now truly replaces it **in place** (keeping
  its position in the deck / grid), as the documentation already described;
  previously the replacement was moved to the end.
- The sidebar slide list now shows a vertical scrollbar when it overflows
  instead of clipping items.

## [0.2.0] - 2026-06-14

### Added

- `slide_id` and `cell_id` arguments to avoid duplicating slides and cells while
  re-running code-cells on interactive Jupyter notebooks.
- `auto_save` and `auto_save_level` options to help creating presentations on 
  interactive Jupyter notebooks, without having to call `.write()` manually.
- `get_slide` to retrieve an slide.
- All cells now have a `__repr__` method to help identifying them.
- Refactored the title and TOC features

