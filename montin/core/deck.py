"""
montin.core.deck
=================
Defines ``Deck``, ``Plugin``, ``SlideDefaults``, and ``CellDefaults``.
"""

from __future__ import annotations

import copy
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Hashable, Literal

from montin.cells import _UNSET
from montin.core.plugins import Plugin
from montin.core.security import Security
from montin.core.slide import Slide
from montin.core.theme_options import ThemeOptions


# ---------------------------------------------------------------------------
# Configurable defaults
# ---------------------------------------------------------------------------

@dataclass
class SlideDefaults:
    """Grid layout defaults applied to every :meth:`~Deck.add_slide` call.

    Any value set here acts as the fallback when the corresponding argument is
    omitted from ``add_slide()``. Per-call arguments always take precedence.

    Attributes:
        nrows: Number of grid rows (default ``1``).
        ncols: Number of grid columns (default ``1``).
        row_heights: CSS height for each row (e.g. ``["2fr", "1fr"]``).
            ``None`` distributes space evenly.
        col_widths: CSS width for each column (e.g. ``["300px", "1fr"]``).
            ``None`` distributes space evenly.
    """

    nrows:       int                      = 1
    ncols:       int                      = 1
    row_heights: list[int | str] | None   = None
    col_widths:  list[int | str] | None   = None


@dataclass
class CellDefaults:
    """Visual and behaviour defaults applied to every ``add_*()`` cell method.

    Any value set here acts as the fallback when the corresponding argument is
    omitted from a cell-creation call. Per-call arguments always take precedence.

    Attributes:
        overflow: Whether cell content is scrollable when it overflows
            (default ``True``).
        copy_button: Show a copy-to-clipboard button on the cell
            (default ``False``).
        expand_button: Show a fullscreen-expand button on the cell
            (default ``False``).
        transparent: Render the cell without a background card
            (default ``False``).
        halign: Horizontal alignment of cell content — ``"left"``,
            ``"center"``, or ``"right"`` (default ``"left"``).
        valign: Vertical alignment of cell content — ``"top"``,
            ``"middle"``, or ``"bottom"`` (default ``"top"``).
        fontscale: Multiplier applied to the cell's text size (default
            ``1.0``). Composes on top of the deck-wide ``fontsize_scale``.
    """

    overflow:      bool                                    = True
    copy_button:   bool                                    = False
    expand_button: bool                                    = False
    transparent:   bool                                    = False
    halign:        Literal["left", "center", "right"]      = "left"
    valign:        Literal["top", "middle", "bottom"]      = "top"
    fontscale:     float                                   = 1.0


# ---------------------------------------------------------------------------
# Deck
# ---------------------------------------------------------------------------

class Deck:
    """
    Main container for a report deck.

    Arguments:
        title (str):    The presentation title (required).
        author (str):   The presentation author (optional).
        date (str):     The presentation date (optional, defaults to today).
        version (str):  The presentation version (optional).
        theme (str): Name of the visual theme (default ``"default"``, which
            matches the documentation site — a clean light look; ``"docs"`` is an
            explicit alias, ``"docs-dark"`` its dark counterpart). Other built-ins:
            ``"montin"`` and ``"ink"`` (the brand Sand light / Ink dark look),
            ``"midnight"`` (the original navy + pink-red look), plus ``"light"``,
            ``"dark"``, ``"light-blue"``, ``"academic"`` and ``"sobrio"``. Each
            theme overrides the CSS colour variables on top of the always-loaded
            base; pair with ``custom_css`` for finer tweaks. See the *Themes*
            guide in the docs for the full list and how to build your own.
        theme_options (ThemeOptions | None): Structured customization on top of
            the ``theme`` — header style/colour, subtitle, bar colours, cell
            spacing/rounding, fonts, a footer, watermark, logo(s), and a switch to
            hide the "Made with Montin" credit. Grouped into nested dataclasses
            (``Header``, ``Bars``, ``Cells``, ``Fonts``, ``Footer``, ``Watermark``,
            ``Logo``). Sits between ``theme`` and ``custom_css`` in the cascade
            (overrides the theme; overridden by ``custom_css``). ``None`` (default)
            applies nothing. Use ``export_css()`` to save the resulting stylesheet.
        custom_css (str | Path | None): Optional path to a custom CSS file (or an
            inline CSS string) merged last, after the theme — the place to
            override the brand variables (``--color-accent`` etc.) or any rule.
        fontsize_scale (float): Multiplier applied to every font in the
            presentation — slide content and the navigation chrome (sidebar,
            toolbar, TOC, lightbox) alike (default ``1.0``). Spacing and layout
            are unaffected. Per-cell ``fontscale`` composes on top of this.
        self_contained (bool): Whether to produce a self-contained HTML file with 
            embedded assets (default: True).
        plugins (list[Plugin]): Optional JS libraries to include, declared via the
            ``Plugins`` container, e.g. ``[Plugins.Plotly(), Plugins.Mermaid()]``
            (default: ``[]``). Nothing is mandatory — declare only what you use.
        plugin_source (Literal['cdn', 'bundled']): Default loading mode for every
            plugin that doesn't set its own ``source`` (default: ``'cdn'``).
            ``'bundled'`` embeds the libraries for a report that works fully
            offline. A ``Security(block_external=True)`` forces ``'bundled'``.
        security (Security | None): Security / privacy hardening for the output
            (CSP, SRI, no-referrer, Permissions-Policy, ...). ``None`` (default)
            applies light, always-safe hardening; pass ``Security(...)`` to
            customise — notably ``block_external=True`` for a provably offline file.
        slide_defaults (SlideDefaults): Global defaults for slides (default: SlideDefaults()).
        cell_defaults (CellDefaults): Global defaults for cells (default: CellDefaults()).
        autosave (str | None): Optional filename to autosave after each change.
            Use it when iteratively building a presentation to live-preview in
            a browser. If building a large presentation, consider not using
            autosave to avoid excessive writes.
        autosave_level (Literal['slide', 'cell']): Whether to autosave after each
            slide change or cell change (default: 'slide').
            Use 'slide' on presentations with many cells to avoid excessive writes.
            Only relevant if autosave is set to a filename.
        size (tuple[int, int] | None): Fixed slide dimensions in pixels, e.g.
            ``(1366, 768)``. When set, slides become a fixed-size "stage" that is
            scaled with a CSS transform to fit the available area — every element
            (fonts, images, layout) scales together, just like a static PDF.
            When ``None`` (default) the layout is fluid and fills the window
            (current behaviour).
        scale_up (bool): When ``size`` is set, allow scaling beyond the native
            dimensions to fill larger screens. When ``False`` (default) the stage
            never grows past 1:1 — it only shrinks on smaller windows.
        keep_aspect_ratio (bool): When ``size`` is set and ``True`` (default), the
            stage scales uniformly and is letterboxed. When ``False`` the stage
            stretches to fill both dimensions independently (distorts content).
        show_sidebar (bool): Render the slide-navigation sidebar (default
            ``True``). Set to ``False`` for clean single-slide / embeddable files.
        show_toolbar (bool): Render the bottom navigation toolbar (default
            ``True``). Set to ``False`` for clean single-slide / embeddable files.
        sidebar_collapsed (bool): Start with the sidebar collapsed (default
            ``False``). The sidebar can still be toggled open via the toolbar
            button or the ``B`` key. Ignored when ``show_sidebar`` is ``False``.
            A previously remembered toggle state (from ``localStorage``) takes
            precedence over this default.
        sidebar_search (bool): Render a regex search box at the top of the sidebar
            that live-filters slides (default ``True``). Ignored when
            ``show_sidebar`` is ``False``.
        sidebar_search_scope (Literal['title', 'title_subtitle', 'content']):
            What the search regex matches against (default ``'title'``).
            ``'title'`` matches the sidebar title only; ``'title_subtitle'`` also
            matches the slide subtitle; ``'content'`` searches the slide's full
            rendered text. Note: with ``'content'``, Plotly/Mermaid bodies are not
            searchable until they have rendered in the browser.
        sidebar_collapsible_sections (bool): Show a caret on section items that
            folds/unfolds the slides under that section (default ``True``).
            Ignored when ``show_sidebar`` is ``False``.

    Example::

        deck = Deck(
            title="Q3 Report",
            author="J. Smith",
            theme="default",
            plugins=[Plugins.MathJax(), Plugins.Plotly()],
            slide_defaults=SlideDefaults(nrows=2, ncols=2),
            cell_defaults=CellDefaults(expand_button=True),
        )
        deck.add_title("Q3 Report")
        slide = deck.add_slide("Results")
        slide.add_metric(value=98.7, label="Efficiency")
        deck.write("q3-report")
    """

    def __init__(
        self,
        title:          str,
        author:         str                      = "",
        date:           str                      = "",
        version:        str                      = "",
        theme:          str                      = "default",
        theme_options:  ThemeOptions | None       = None,
        custom_css:     str | Path | None        = None,
        fontsize_scale: float                    = 1.0,
        self_contained: bool                     = True,
        plugins:        list[Plugin] | None      = None,
        plugin_source:  Literal['cdn', 'bundled'] = 'cdn',
        slide_defaults: SlideDefaults | None     = None,
        cell_defaults:  CellDefaults | None      = None,
        autosave:       str | None               = None,
        autosave_level: Literal['slide', 'cell'] = 'slide',
        size:              tuple[int, int] | None = None,
        scale_up:          bool                   = False,
        keep_aspect_ratio: bool                   = True,
        show_sidebar:      bool                   = True,
        show_toolbar:      bool                   = True,
        sidebar_collapsed: bool                   = False,
        sidebar_search:    bool                   = True,
        sidebar_search_scope: Literal['title', 'title_subtitle', 'content'] = 'title',
        sidebar_collapsible_sections: bool        = True,
        preview_height:    int | None             = None,
        contents_folder:   str | Path | None      = None,
        security:          Security | None         = None,
    ) -> None:
        self.title          = title
        self.author         = author
        self.date           = date or datetime.date.today().isoformat()
        self.version        = version
        self.theme          = theme
        self.theme_options  = theme_options
        # Kept as given (no blanket Path() coercion): the resolver decides
        # whether a str is a path to a .css file or inline CSS — coercing every
        # str to Path here made inline CSS strings silently unresolvable.
        self.custom_css     = custom_css
        self.fontsize_scale = fontsize_scale
        self.self_contained = self_contained
        # Fresh objects per deck — a shared default instance (or a caller's
        # list) mutated on one deck must never leak into another.
        self.plugins        = [copy.copy(p) for p in (plugins or [])]
        self.plugin_source  = plugin_source
        self.slide_defaults = slide_defaults if slide_defaults is not None else SlideDefaults()
        self.cell_defaults  = cell_defaults if cell_defaults is not None else CellDefaults()
        self.autosave       = autosave
        self.autosave_level = autosave_level
        self.size              = size
        self.scale_up          = scale_up
        self.keep_aspect_ratio = keep_aspect_ratio
        self.show_sidebar      = show_sidebar
        self.show_toolbar      = show_toolbar
        self.sidebar_collapsed = sidebar_collapsed
        self.sidebar_search        = sidebar_search
        self.sidebar_search_scope  = sidebar_search_scope
        self.sidebar_collapsible_sections = sidebar_collapsible_sections
        self.preview_height  = preview_height
        self.contents_folder = contents_folder
        self.security        = security or Security()

        self._slides:   list[Slide] = []
        self._slide_map: dict[Hashable, Slide] = {}
        self._sections: list[dict[str, Any]] = []   # for the automatic TOC
        self._slide_counter = 0
        # Per-Jupyter-cell counters for notebook_unique slide ids.
        self._nb_slide_state: dict = {}

    @property
    def _plugin_names(self) -> frozenset[str]:
        """Names of the currently declared plugins.

        Computed on demand so that mutating ``deck.plugins`` after construction
        (e.g. ``deck.plugins.append(Plugins.Plotly())``) is immediately visible
        to ``add_plotly`` & friends instead of raising PluginNotDeclaredError.
        """
        return frozenset(p.name for p in self.plugins)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def add_title(
        self,
        title:    str,
        subtitle: str = "",
        notes:    str = "",
        title_id: Hashable | None = None,
        notebook_unique: bool = False,
    ) -> Slide:
        """Add the cover/title slide.

        Args:
            title (str): Main heading.
            subtitle (str): Optional secondary text.
            notes (str): Presenter notes (not rendered on the slide).
            title_id: Stable identifier, like ``slide_id`` on ``add_slide``.
                Re-running with the same ``title_id`` replaces the title slide
                in place instead of appending a duplicate — useful in notebooks.

        Returns:
            The newly created :class:`~montin.core.slide.Slide`.
        """
        return self._make_slide(
            title=title,
            subtitle=subtitle,
            slide_type="title",
            nrows=1,
            ncols=1,
            row_heights=None,
            col_widths=None,
            notes=notes,
            slide_id=title_id,
            notebook_unique=notebook_unique,
        )

    def add_section(
        self,
        title:      str,
        subtitle:   str  = "",
        level:      int  = 1,
        add_to_toc: bool = True,
        show_toc:   bool = True,
        section_id: Hashable | None = None,
        notebook_unique: bool = False,
    ) -> Slide:
        """Add a section-divider slide.

        Args:
            title (str): Section heading.
            subtitle (str): Optional secondary text below the heading.
            level (int): Hierarchy depth (1 = top-level, 2 = sub-section, …).
                Higher levels are indented and visually dimmed in the sidebar.
            add_to_toc (bool): Whether to include this section in TOC slides and
                inline section TOCs (default ``True``).
            show_toc (bool): Whether to render an inline TOC on this slide
                highlighting the current section (default ``True``).
            section_id: Stable identifier, like ``slide_id`` on ``add_slide``.
                Re-running with the same ``section_id`` replaces the section (and
                its TOC entry) in place instead of appending a duplicate.

        Returns:
            The newly created :class:`~montin.core.slide.Slide`.
        """
        slide = self._make_slide(
            title=title,
            subtitle=subtitle,
            slide_type="section",
            nrows=1,
            ncols=1,
            row_heights=None,
            col_widths=None,
            notes="",
            slide_id=section_id,
            level=level,
            show_toc=show_toc,
            notebook_unique=notebook_unique,
        )
        if add_to_toc:
            entry = {
                "title":    title,
                "subtitle": subtitle,
                "level":    level,
                "slide_id": slide.slide_id,
            }
            idx = next(
                (i for i, s in enumerate(self._sections)
                 if s["slide_id"] == slide.slide_id),
                None,
            )
            if idx is None:
                self._sections.append(entry)
            else:
                self._sections[idx] = entry   # replace in place, preserve TOC order
        else:
            # A re-run that flips add_to_toc to False must drop any prior entry.
            self._sections = [
                s for s in self._sections if s["slide_id"] != slide.slide_id
            ]
        return slide

    def add_toc(
        self,
        title: str = "Table of Contents",
        auto:  bool = True,
        toc_id: Hashable | None = None,
        notebook_unique: bool = False,
    ) -> Slide:
        """Add a Table of Contents slide.

        The TOC is always populated at ``write()`` time so it reflects all
        sections in the deck regardless of call order.

        Args:
            title (str): Slide heading shown in the header bar.
            auto (bool): When ``True`` (default), the TOC is built automatically
                from all ``add_section()`` calls.  When ``False`` the slide
                is rendered with an empty TOC.
            toc_id: Stable identifier, like ``slide_id`` on ``add_slide``.
                Re-running with the same ``toc_id`` replaces the TOC slide in
                place instead of appending a duplicate.

        Returns:
            The newly created :class:`~montin.core.slide.Slide`.
        """
        slide = self._make_slide(
            title=title,
            subtitle="",
            slide_type="toc",
            nrows=1,
            ncols=1,
            row_heights=None,
            col_widths=None,
            notes="",
            slide_id=toc_id,
            notebook_unique=notebook_unique,
        )
        slide._auto_toc = auto  # type: ignore[attr-defined]
        return slide

    def add_slide(
        self,
        title:          str,
        subtitle:       str                      = "",
        nrows:          Any                      = _UNSET,
        ncols:          Any                      = _UNSET,
        row_heights:    list[int | str] | None   = _UNSET,
        col_widths:     list[int | str] | None   = _UNSET,
        notes:          str                      = "",
        slide_id:       Hashable | None          = None,
        slide_defaults: SlideDefaults | None     = None,
        cell_defaults:  CellDefaults | None      = None,
        notebook_unique: bool                    = False,
    ) -> Slide:
        """Add a standard content slide with an ``nrows x ncols`` cell canvas.

        Args:
            title (str): Slide heading shown in the header bar.
            subtitle (str): Optional secondary heading shown below the title.
            nrows (int): Number of grid rows. Falls back to ``slide_defaults.nrows``
                then ``self.slide_defaults.nrows`` when omitted.
            ncols (int): Number of grid columns. Same fallback chain as ``nrows``.
            row_heights (List[str,...]): Explicit heights for each row (CSS 
                values such as ``"1fr"`` or ``200``). ``None`` lets the grid 
                distribute space evenly. Falls back through the defaults 
                hierarchy when omitted.
            col_widths(List[str,...]): Explicit widths for each column. Same 
                semantics as ``row_heights``.
            notes: Presenter notes attached to this slide (not rendered in the
                slide itself).
            slide_id: Stable identifier for this slide. Auto-generated as
                ``"slide-<n>"`` when ``None``. Raises ``DuplicateSlideError``
                if the id is already in use.
            slide_defaults: Per-call override for grid defaults. Takes
                precedence over ``self.slide_defaults`` but is overridden by
                any explicitly supplied ``nrows`` / ``ncols`` / ``row_heights``
                / ``col_widths`` argument.
            cell_defaults: Per-call override for cell defaults. Takes
                precedence over ``self.cell_defaults`


        Returns:
            The newly created :class:`~montin.core.slide.Slide`.
        """
        sd = slide_defaults if slide_defaults is not None else self.slide_defaults
        return self._make_slide(
            title=title,
            subtitle=subtitle,
            slide_type="slide",
            nrows=sd.nrows             if nrows       is _UNSET else nrows,
            ncols=sd.ncols             if ncols       is _UNSET else ncols,
            row_heights=sd.row_heights if row_heights is _UNSET else row_heights,
            col_widths=sd.col_widths   if col_widths  is _UNSET else col_widths,
            notes=notes,
            slide_id=slide_id,
            cell_defaults=cell_defaults if cell_defaults is not None else self.cell_defaults,
            notebook_unique=notebook_unique,
        )


    def render(self, strict: bool = True):
        """Render the deck to its final HTML string.

        Args:
            strict: When ``True`` (default) any cell that fails to render
                raises and aborts the whole render. ``strict=False`` degrades a
                failing cell to a visible error box (with the exception message)
                and keeps every other slide — recommended for unattended batch
                jobs where one pathological figure must not cost the report.
        """
        from montin.core.assembler import Assembler

        assembler = Assembler(self, strict=strict)
        return assembler._render()

    def render_css(self) -> str:
        """Return the deck's merged stylesheet — exactly the CSS that lands in the
        ``<style>`` tag: default base → ``theme`` → ``theme_options`` →
        ``custom_css``.

        Note: this captures the *visual* theme (palette, header, bars, cells,
        fonts, hidden credit). The HTML-rendered ``theme_options`` features —
        footer text, watermark and logo elements — are content, not CSS, so they
        are driven by ``theme_options`` at render time and are not in this string.
        """
        from montin.utils.theme_resolver import ThemeResolver

        options_css = self.theme_options.to_css() if self.theme_options else None
        return ThemeResolver().resolve(self.theme, self.custom_css, options_css)

    def export_css(self, path: str | Path) -> Path:
        """Write :meth:`render_css` to a ``.css`` file and return the path.

        The saved stylesheet can be shared, hand-edited, and loaded back into any
        deck via ``Deck(custom_css=<path>)`` — since ``custom_css`` is last in the
        cascade it faithfully reproduces the look.
        """
        out = Path(path).with_suffix(".css")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.render_css(), encoding="utf-8")
        return out

    def write(
        self,
        filename:     str | Path | None = None,
        open_browser: bool = False,
        strict:       bool = True,
    ) -> Path:
        """Trigger the Assembler, write ``<filename>.html``, and return the Path.

        Args:
            filename: Output file. Defaults to ``autosave`` when set, else a
                name derived from the deck title.
            open_browser: Open the written file in the default browser.
            strict: When ``True`` (default) a failing cell aborts the write.
                ``strict=False`` renders it as a visible error box and keeps
                the rest of the deck — see :meth:`render`.
        """
        from montin.core.assembler import Assembler

        if (filename is None) and (self.autosave is not None):
            filename = self.autosave
        elif (filename is None) and (self.autosave is None):
            filename = self.title.replace(" ", "-")

        path = Path(filename).with_suffix(".html")
        assembler = Assembler(self, strict=strict)
        assembler.write(path)

        if open_browser:
            import webbrowser
            webbrowser.open(path.resolve().as_uri())

        return path

    def remove_slide(
            self,
            slide_id:Hashable
        ) -> None:
        """Remove a slide by its ID."""
        if slide_id not in self._slide_map:
            raise KeyError(f"No slide found with ID: {slide_id}")
        slide = self._slide_map.pop(slide_id)
        self._slides.remove(slide)
        # Drop any TOC registration so a removed section leaves the TOC too.
        self._sections = [s for s in self._sections if s["slide_id"] != slide_id]


    def get_slide(
        self,
        slide_id: Hashable,
    ):
        """Get a slide by its ID."""
        if slide_id not in self._slide_map:
            raise KeyError(
                f"No slide found with ID: {slide_id}. Available slide IDs:\n- "
                + '\n- '.join([f'{k}: {v}' for k, v in self._slide_map.items()])
                + '\n')
        return self._slide_map[slide_id]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _make_slide(
        self,
        title:       str,
        subtitle:    str,
        slide_type:  str,
        nrows:       int,
        ncols:       int,
        row_heights: list[int | str] | None,
        col_widths:  list[int | str] | None,
        notes:       str,
        slide_id:    Hashable | None = None,
        cell_defaults: CellDefaults | None = None,
        level:       int  = 1,
        show_toc:    bool = False,
        notebook_unique: bool = False,
    ) -> Slide:
        self._slide_counter += 1

        # An explicit id always wins. Otherwise notebook_unique derives a stable
        # id from the Jupyter cell (re-running replaces in place); failing that,
        # fall back to the auto-counter.
        if slide_id is None and notebook_unique:
            from montin.utils.notebook import notebook_unique_id
            slide_id = notebook_unique_id(self._nb_slide_state, "_nbslide")
        if slide_id is None:
            slide_id = f"_slide-{self._slide_counter}"

        slide = Slide(
            slide_id      = slide_id,
            title         = title,
            subtitle      = subtitle,
            slide_type    = slide_type,  # type: ignore[arg-type]
            nrows         = nrows,
            ncols         = ncols,
            row_heights   = row_heights,
            col_widths    = col_widths,
            notes         = notes,
            cell_defaults = cell_defaults,
            parent        = self,
            level         = level,
            show_toc      = show_toc,
        )
        # Overwrite an existing id in place (keep deck position); else append.
        if slide_id in self._slide_map:
            old = self._slide_map[slide_id]
            self._slides[self._slides.index(old)] = slide
        else:
            self._slides.append(slide)
        self._slide_map[slide_id] = slide

        if self.autosave:
            self.write(self.autosave)

        return slide

    def _attach_slide(self, slide: Slide, index: int | None = None) -> Slide:
        """Register an already-built ``Slide`` on this deck (used by the import /
        from_dict paths). Mirrors the tail of :meth:`_make_slide` but without
        creating the slide. A colliding ``slide_id`` is auto-renamed so an import
        never silently clobbers an existing slide.

        ``index`` is a position in ``_slides`` (``list.insert`` semantics);
        ``None`` appends. Does not autosave — callers decide when to write.
        """
        sid = slide.slide_id
        if sid in self._slide_map and self._slide_map[sid] is not slide:
            base, n = str(sid), 2
            candidate = f"{base}-imported"
            while candidate in self._slide_map:
                candidate = f"{base}-imported-{n}"
                n += 1
            slide.slide_id = candidate
            sid = candidate

        if index is None:
            self._slides.append(slide)
        else:
            self._slides.insert(index, slide)
        self._slide_map[sid] = slide
        self._slide_counter += 1
        return slide

    # ------------------------------------------------------------------
    # Serialisation (see montin.io for the file envelope / compression)
    # ------------------------------------------------------------------

    @staticmethod
    def _plugin_to_dict(plugin: Plugin) -> dict:
        from dataclasses import asdict

        return {"name": plugin.name, **asdict(plugin)}

    @staticmethod
    def _plugin_from_dict(data: dict) -> Plugin:
        from montin.core.plugins import plugin_registry

        fields = dict(data)
        target = plugin_registry().get(fields.pop("name", None), Plugin)
        return target(**fields)

    def to_dict(self, embed: bool = True, *, slides: list[Slide] | None = None) -> dict:
        """Serialise the deck's configuration and slides to a JSON-native dict.

        Args:
            embed: Passed through to each cell (embed image data inline, or keep
                references).
            slides: Restrict the serialised slides to this subset (used by
                :meth:`export_slides`). Defaults to every slide.
        """
        from dataclasses import asdict

        slides = self._slides if slides is None else slides
        custom_css = str(self.custom_css) if self.custom_css is not None else None
        contents_folder = str(self.contents_folder) if self.contents_folder is not None else None
        return {
            "title":          self.title,
            "author":         self.author,
            "date":           self.date,
            "version":        self.version,
            "theme":          self.theme,
            "theme_options":  self.theme_options.to_dict() if self.theme_options else None,
            "custom_css":     custom_css,
            "fontsize_scale": self.fontsize_scale,
            "self_contained": self.self_contained,
            "plugins":        [self._plugin_to_dict(p) for p in self.plugins],
            "plugin_source":  self.plugin_source,
            "slide_defaults": asdict(self.slide_defaults),
            "cell_defaults":  asdict(self.cell_defaults),
            "autosave":       self.autosave,
            "autosave_level": self.autosave_level,
            "size":           list(self.size) if self.size is not None else None,
            "scale_up":          self.scale_up,
            "keep_aspect_ratio": self.keep_aspect_ratio,
            "show_sidebar":      self.show_sidebar,
            "show_toolbar":      self.show_toolbar,
            "sidebar_collapsed": self.sidebar_collapsed,
            "sidebar_search":        self.sidebar_search,
            "sidebar_search_scope":  self.sidebar_search_scope,
            "sidebar_collapsible_sections": self.sidebar_collapsible_sections,
            "preview_height":  self.preview_height,
            "contents_folder": contents_folder,
            "security":        asdict(self.security),
            "slides":          [s.to_dict(embed=embed) for s in slides],
            "sections":        [dict(s) for s in self._sections],
        }

    def export(
        self,
        path: "str | Path",
        *,
        embed: bool = True,
        compress: bool | None = None,
    ) -> Path:
        """Write the whole deck to a JSON file (``kind="deck"``); return the path.

        See :func:`montin.io.write_document` for ``compress`` semantics.
        """
        from montin.io import write_document

        return write_document(path, "deck", self.to_dict(embed=embed), compress=compress)

    def export_slides(
        self,
        path: "str | Path",
        *,
        by_pos: "list[int] | range | None" = None,
        by_key: "list[Hashable] | None" = None,
        embed: bool = True,
        compress: bool | None = None,
    ) -> Path:
        """Write a selection of slides to a JSON file (``kind="slides"``).

        Args:
            path: Output file.
            by_pos: Positional indices (a list or ``range``) into ``slides``.
            by_key: Slide ids to look up in ``slide_map``.
            embed: Embed image data inline (``True``) or keep references.
            compress: gzip tri-state — see :func:`montin.io.write_document`.

        With neither ``by_pos`` nor ``by_key`` given, every slide is exported.
        When both are given the ``by_pos`` selection precedes the ``by_key`` one;
        selection order is preserved.
        """
        from montin.io import write_document

        selected = self._select_slides(by_pos, by_key)
        payload = [s.to_dict(embed=embed) for s in selected]
        return write_document(path, "slides", payload, compress=compress)

    def _select_slides(self, by_pos, by_key) -> list[Slide]:
        if by_pos is None and by_key is None:
            return list(self._slides)
        out: list[Slide] = []
        if by_pos is not None:
            out.extend(self._slides[i] for i in by_pos)
        if by_key is not None:
            out.extend(self._slide_map[k] for k in by_key)
        return out

    def import_slides(self, path: "str | Path", index: int = -1) -> list[Slide]:
        """Load slide(s) from a JSON file and insert them into this deck.

        Accepts both a single-slide file (``kind="slide"``) and a multi-slide
        file (``kind="slides"``). ``index`` is where the (first) slide lands in
        ``slides``: ``-1`` (default) appends at the end; any other value follows
        ``list.insert`` semantics, with subsequent slides kept in order after it.
        Colliding slide ids are auto-renamed. Returns the inserted slides.
        """
        from montin.io import read_document

        kind, payload = read_document(path, ("slide", "slides"))
        slide_dicts = [payload] if kind == "slide" else list(payload)

        n = len(self._slides)
        if index == -1:
            base = n
        elif index < 0:
            base = max(0, n + index + 1)
        else:
            base = min(index, n)

        new_slides: list[Slide] = []
        for offset, sd in enumerate(slide_dicts):
            slide = Slide.from_dict(sd, parent=self)
            self._attach_slide(slide, index=base + offset)
            new_slides.append(slide)

        if self.autosave:
            self.write(self.autosave)
        return new_slides

    @classmethod
    def from_dict(cls, data: dict) -> "Deck":
        """Reconstruct a whole deck from a :meth:`to_dict` payload."""
        sd = data.get("slide_defaults")
        cd = data.get("cell_defaults")
        deck = cls(
            title          = data["title"],
            author         = data.get("author", ""),
            date           = data.get("date", ""),
            version        = data.get("version", ""),
            theme          = data.get("theme", "default"),
            theme_options  = ThemeOptions.from_dict(data.get("theme_options")),
            custom_css     = data.get("custom_css"),
            fontsize_scale = data.get("fontsize_scale", 1.0),
            self_contained = data.get("self_contained", True),
            plugins        = [cls._plugin_from_dict(p) for p in data.get("plugins", [])],
            plugin_source  = data.get("plugin_source", "cdn"),
            slide_defaults = SlideDefaults(**sd) if sd else SlideDefaults(),
            cell_defaults  = CellDefaults(**cd) if cd else CellDefaults(),
            autosave       = data.get("autosave"),
            autosave_level = data.get("autosave_level", "slide"),
            size           = tuple(data["size"]) if data.get("size") else None,
            scale_up          = data.get("scale_up", False),
            keep_aspect_ratio = data.get("keep_aspect_ratio", True),
            show_sidebar      = data.get("show_sidebar", True),
            show_toolbar      = data.get("show_toolbar", True),
            sidebar_collapsed = data.get("sidebar_collapsed", False),
            sidebar_search        = data.get("sidebar_search", True),
            sidebar_search_scope  = data.get("sidebar_search_scope", "title"),
            sidebar_collapsible_sections = data.get("sidebar_collapsible_sections", True),
            preview_height  = data.get("preview_height"),
            contents_folder = data.get("contents_folder"),
            security        = Security(**data["security"]) if data.get("security") else None,
        )
        for sd in data.get("slides", []):
            deck._attach_slide(Slide.from_dict(sd, parent=deck))
        deck._sections = [dict(s) for s in data.get("sections", [])]
        return deck

    @classmethod
    def from_file(cls, path: "str | Path") -> "Deck":
        """Load a deck written by :meth:`export` (plain or gzipped)."""
        from montin.io import read_document

        _kind, payload = read_document(path, "deck")
        return cls.from_dict(payload)

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def slides(self) -> list[Slide]:
        return list(self._slides)

    @property
    def slide_map(self) -> dict[Hashable, Slide]:
        return dict(self._slide_map)

    @property
    def sections(self) -> list[dict]:
        """Read-only list of TOC-registered section metadata dicts."""
        return list(self._sections)

    def __repr__(self) -> str:
        return (
            f"Deck(title={self.title!r}, slides={len(self._slides)}, "
            f"theme={self.theme!r})"
        )

    # ------------------------------------------------------------------
    # Jupyter preview
    # ------------------------------------------------------------------

    def _preview_clone(
        self,
        slides: list[Slide],
        sections: list[dict[str, Any]] | None = None,
    ) -> "Deck":
        """Build a chrome-free deck cloning this deck's visual configuration.

        Used to render single-slide / single-cell previews through the normal
        pipeline (same theme, plugins, and stage settings) without the
        navigation sidebar or toolbar.

        Args:
            slides: Slide objects to place in the temporary deck.
            sections: Optional TOC section registry to carry over (for fidelity
                of section/TOC slide previews).

        Returns:
            A throwaway :class:`Deck` ready to pass to the Assembler.
        """
        clone = Deck(
            title=self.title,
            author=self.author,
            date=self.date,
            version=self.version,
            theme=self.theme,
            theme_options=self.theme_options,
            custom_css=self.custom_css,
            self_contained=self.self_contained,
            plugins=self.plugins,
            plugin_source=self.plugin_source,
            slide_defaults=self.slide_defaults,
            cell_defaults=self.cell_defaults,
            size=self.size,
            scale_up=self.scale_up,
            keep_aspect_ratio=self.keep_aspect_ratio,
            show_sidebar=False,
            show_toolbar=False,
            preview_height=self.preview_height,
            contents_folder=self.contents_folder,
            security=self.security,
        )
        clone._slides = list(slides)
        clone._slide_map = {s.slide_id: s for s in slides}
        clone._sections = list(sections) if sections else []
        return clone

    def _repr_html_(self) -> str:
        """Render an inline preview of the whole deck for Jupyter notebooks."""
        from montin.core.assembler import Assembler
        from montin.utils.notebook import (
            DECK_PREVIEW_HEIGHT, iframe_srcdoc, preview_error,
        )
        try:
            html = Assembler(self)._render()
            return iframe_srcdoc(html, height=self.preview_height or DECK_PREVIEW_HEIGHT)
        except Exception as exc:   # never break the notebook on a preview failure
            return preview_error(self, exc)
