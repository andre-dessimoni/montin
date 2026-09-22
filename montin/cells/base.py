"""
montin.cells.base
==================
Defines the _UNSET sentinel, CellParams, the abstract Cell base class,
and the @cell_method decorator. All concrete subtypes import from here.
"""

from __future__ import annotations

import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Callable, Literal, Hashable, cast

# Importing jinja2 and Slide only for type annotations, to avoid circular
# imports and heavy dependencies at runtime
if TYPE_CHECKING:
    import jinja2
    from typing import ParamSpec, TypeVar
    from montin.core.slide import Slide

    # Lets @cell_method preserve each add_* method's real signature (parameters
    # and concrete return type) for type checkers / editors, instead of
    # collapsing them to ``(...) -> Cell``. Type-checking only; under
    # ``from __future__ import annotations`` the annotations are never evaluated
    # at runtime, so ParamSpec is not needed on Python 3.9.
    _P = ParamSpec("_P")
    _R = TypeVar("_R", bound="Cell")


# ---------------------------------------------------------------------------
# Sentinel
# ---------------------------------------------------------------------------

class _UnsetType:
    """Singleton sentinel — indicates the argument was not passed by the 
    caller."""

    _instance: "_UnsetType | None" = None

    def __new__(cls) -> "_UnsetType":
        """Ensures only one instance of _UnsetType exists.
        
        Trying to create another instance will return the existing one.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "<UNSET>"


_UNSET = _UnsetType()


# ---------------------------------------------------------------------------
# CellParams
# ---------------------------------------------------------------------------

@dataclass
class CellParams:
    """
    Common parameters for all cells, already resolved by @cell_method
    (defaults applied, position determined, validation complete).
    """
    col:           int
    row:           int
    cell_id:       Hashable
    colspan:       int   = 1
    rowspan:       int   = 1
    caption:       str   = ""
    overflow:      bool  = True
    copy_button:   bool  = False
    expand_button: bool  = False
    transparent:   bool  = False
    halign:        Literal["left", "center", "right"] = "left"
    valign:        Literal["top", "middle", "bottom"] = "top"
    fontscale:     float = 1.0

# ---------------------------------------------------------------------------
# Cell — abstract base class
# ---------------------------------------------------------------------------

@dataclass
class RenderContext:
    """Write-time facts a cell needs to resolve its media in :meth:`Cell.finalize`.

    ``contents_dir`` / ``out_dir`` are ``None`` during notebook previews (there
    is no output file), in which case everything is inlined.
    """

    contents_dir: "Path | None"
    out_dir: "Path | None"
    self_contained: bool

    def key(self) -> tuple:
        """Hashable identity of this context.

        Lets ``finalize()`` implementations skip re-resolving media when called
        again with the *same* context (autosave re-renders the deck on every
        change) while still recomputing whenever the context differs (a preview
        inlines everything; the real write may save side files instead).
        """
        return (str(self.contents_dir), str(self.out_dir), self.self_contained)


class Cell(ABC):
    """
    Base class for all cells. Every concrete subtype must implement
    ``render()``, which returns the cell's HTML fragment.
    """

    def __init__(self, params: CellParams) -> None:
        self.params = params
        self._slide: "Slide | None" = None   # set by Slide._register_cell

    @abstractmethod
    def render(self, env: "jinja2.Environment") -> str:
        """Renders and returns the cell's HTML fragment."""
        ...

    def finalize(self, ctx: RenderContext) -> None:
        """Resolve this cell's media for the final output (inline data URIs
        and/or side files in the contents folder).

        Called by the Assembler once per render, before :meth:`render`. Must be
        **idempotent and context-independent**: a notebook preview may already
        have run it with a different context in the same session, so recompute
        from ``ctx`` rather than caching the first result. The default does
        nothing — only media-bearing cells override it.
        """

    def _asset_stem(self) -> str:
        """Filename stem for this cell's side files, unique within the deck."""
        from montin.utils import media

        sl = self._slide
        sid = sl.slide_id if sl is not None else "slide"
        return f"{media.sanitize_name(sid)}__{media.sanitize_name(self.params.cell_id)}"

    def _repr_html_(self) -> str:
        """Render an inline preview of this single cell for Jupyter notebooks.

        The cell is rendered on its own 1x1 chrome-free canvas. When the cell is
        attached to a deck its theme and plugins are reused; otherwise a default
        deck with all plugins is used so any cell type renders correctly.
        """
        from montin.core.assembler import Assembler
        from montin.core.slide import Slide
        from montin.utils.notebook import (
            CELL_PREVIEW_HEIGHT, iframe_srcdoc, preview_error,
        )
        try:
            src = getattr(self._slide, "parent", None)
            if src is not None:
                deck = src._preview_clone([])
            else:
                from montin.core.deck import Deck
                from montin.core.plugins import plugin_registry
                deck = Deck(
                    title="cell",
                    plugins=[cls() for cls in plugin_registry().values()],
                    show_sidebar=False,
                    show_toolbar=False,
                )

            slide = Slide(
                slide_id="_preview", title="", subtitle="", slide_type="slide",
                nrows=1, ncols=1, row_heights=None, col_widths=None, notes="",
                cell_defaults=deck.cell_defaults, parent=deck,
            )
            # Render this very cell at (1,1) so it fills the 1x1 preview canvas.
            saved = self.params
            self.params = replace(saved, col=1, row=1, colspan=1, rowspan=1)
            try:
                slide._cells = [self]
                slide._cell_map = {self.params.cell_id: self}
                deck._slides = [slide]
                deck._slide_map = {slide.slide_id: slide}
                html = Assembler(deck)._render()
            finally:
                self.params = saved
            return iframe_srcdoc(html, height=deck.preview_height or CELL_PREVIEW_HEIGHT)
        except Exception as exc:   # never break the notebook on a preview failure
            return preview_error(self, exc)

    @property
    def col(self) -> int:
        return self.params.col

    @property
    def row(self) -> int:
        return self.params.row

    @property
    def colspan(self) -> int:
        return self.params.colspan

    @property
    def rowspan(self) -> int:
        return self.params.rowspan

    # ------------------------------------------------------------------
    # Serialisation (see montin.io for the file envelope / compression)
    # ------------------------------------------------------------------

    def to_dict(self, embed: bool = True) -> dict:
        """Serialise this cell to a JSON-native dict (the *cell payload*).

        The dict carries ``cell_type`` (the class name, used by
        :meth:`from_dict` to pick the subtype), ``params`` (the resolved
        :class:`CellParams`), and ``content`` (type-specific data produced by
        :meth:`_to_content`).

        Args:
            embed: When ``True`` (default), image-bearing cells embed their data
                inline (base64); when ``False`` they keep file paths / URLs as
                references. Matplotlib / Plotly figures are always embedded.
        """
        from dataclasses import asdict

        return {
            "cell_type": type(self).__name__,
            "params": asdict(self.params),
            "content": self._to_content(embed=embed),
        }

    def _to_content(self, *, embed: bool = True) -> dict:
        """Type-specific serialisable data. Overridden by subclasses.

        The default (used by :class:`~montin.cells.misc.EmptyCell`) carries no
        extra data.
        """
        return {}

    def export(
        self,
        path: "str | Path",
        *,
        embed: bool = True,
        compress: bool | None = None,
    ) -> "Path":
        """Write this cell to a JSON file (``kind="cell"``); return the path.

        See :func:`montin.io.write_document` for ``compress`` semantics.
        """
        from montin.io import write_document

        return write_document(path, "cell", self.to_dict(embed=embed), compress=compress)

    @classmethod
    def from_dict(cls, data: dict) -> "Cell":
        """Reconstruct a cell from a :meth:`to_dict` payload.

        Dispatches on ``data["cell_type"]`` via the cell registry, so this can be
        called as ``Cell.from_dict(...)`` regardless of the concrete subtype.
        """
        from montin.cells._registry import CELL_REGISTRY
        from montin.exceptions import InvalidDataError

        cell_type = data.get("cell_type")
        target = CELL_REGISTRY.get(cell_type)
        if target is None:
            raise InvalidDataError(f"Unknown cell_type {cell_type!r} in cell document.")
        params = CellParams(**data["params"])
        return target._from_content(data.get("content", {}) or {}, params)

    @classmethod
    def _from_content(cls, content: dict, params: CellParams) -> "Cell":
        """Build an instance from ``content`` + ``params``. Overridden by
        subclasses; the default works for the no-extra-data case."""
        return cls(params=params)

    @classmethod
    def from_file(cls, path: "str | Path") -> "Cell":
        """Load a cell written by :meth:`export` (plain or gzipped)."""
        from montin.io import read_document

        _kind, payload = read_document(path, "cell")
        return cls.from_dict(payload)

    @classmethod
    def _raw_new(cls, params: CellParams) -> "Cell":
        """Create an instance *without* running its ``__init__``, then attach
        ``params``. Used by reload paths that restore post-construction state
        directly (e.g. an already-encoded figure) instead of re-running lossy or
        dependency-heavy construction work."""
        obj = cls.__new__(cls)
        Cell.__init__(obj, params)
        return obj


# ---------------------------------------------------------------------------
# @cell_method — decorator
# ---------------------------------------------------------------------------

#: Layout/style parameters shared by the ``add_*`` methods, with the neutral
#: fallback used when a method does not declare the parameter at all.
#: For parameters a method *does* declare, the default in its signature is the
#: single source of truth (``_UNSET`` defers to the slide's ``CellDefaults``).
_COMMON_PARAM_FALLBACKS: dict = {
    "col":           None,
    "row":           None,
    "colspan":       1,
    "rowspan":       1,
    "caption":       "",
    "overflow":      _UNSET,
    "copy_button":   _UNSET,
    "expand_button": _UNSET,
    "transparent":   _UNSET,
    "halign":        _UNSET,
    "valign":        _UNSET,
    "fontscale":     _UNSET,
}


def cell_method(fn: "Callable[_P, _R]") -> "Callable[_P, _R]":
    """
    Decorator applied to all ``add_*`` methods of ``Slide``.

    Responsibilities (in order):
    1. Extract the common layout/style parameters, using each method's own
       signature as the single source of truth for their defaults
    2. Merge with CellDefaults (replace _UNSET with the global default)
    3. Resolve cell_id and position (col/row) if not provided
    4. Validate col/row within canvas range (1-indexed)
    5. Validate colspan/rowspan within canvas bounds
    6. Detect collision with already-allocated cells
    7. Call the decorated method to construct the cell
    8. Register occupied positions on the Slide's internal map
    9. Ensure the return value is a Cell instance
    10. Autosave if Slide.parent.autosave_level == 'cell'

    ``cell_id`` and ``notebook_unique`` are decorator-level extras accepted by
    every ``add_*`` method (they identify the cell, they don't style it), so
    they are consumed here without appearing in each signature.
    """
    import inspect

    # Defaults come from the decorated method's signature — never from a
    # parallel table here that could drift out of sync with it. A common
    # parameter absent from the signature is not accepted from callers
    # (TypeError from fn) and falls back to its neutral value.
    sig_defaults = {
        name: param.default
        for name, param in inspect.signature(fn).parameters.items()
        if name in _COMMON_PARAM_FALLBACKS
    }

    @functools.wraps(fn)
    def wrapper(slide: "Slide", *args: Any, **kwargs: Any) -> Cell:
        # --- 1. Extract common parameters (signature-driven) ---
        common = {name: kwargs.pop(name, default)
                  for name, default in sig_defaults.items()}
        for name, fallback in _COMMON_PARAM_FALLBACKS.items():
            common.setdefault(name, fallback)

        col      = common["col"]
        row      = common["row"]
        colspan  = common["colspan"]
        rowspan  = common["rowspan"]
        caption  = common["caption"]

        overflow      = common["overflow"]
        copy_button   = common["copy_button"]
        expand_button = common["expand_button"]
        transparent   = common["transparent"]
        halign        = common["halign"]
        valign        = common["valign"]
        fontscale     = common["fontscale"]
        cell_id         = kwargs.pop("cell_id",         _UNSET)
        notebook_unique = kwargs.pop("notebook_unique", False)

        # An explicit cell_id always wins. Otherwise, notebook_unique derives a
        # stable id from the Jupyter cell (so re-running replaces in place);
        # failing that, fall back to the per-slide auto-counter.
        if cell_id is _UNSET:
            cell_id = None
            if notebook_unique:
                from montin.utils.notebook import notebook_unique_id
                cell_id = notebook_unique_id(slide._nb_cell_state, "_nbcell")
            if cell_id is None:
                cell_id = f'_cell-{slide._next_cell_id}'
                slide._next_cell_id += 1

        # --- 2. Merge with CellDefaults ---
        cd = slide._cell_defaults
        if overflow      is _UNSET:
            overflow      = cd.overflow
        if copy_button   is _UNSET:
            copy_button   = cd.copy_button
        if expand_button is _UNSET:
            expand_button = cd.expand_button
        if transparent   is _UNSET:
            transparent   = cd.transparent
        if halign is _UNSET:
            halign = cd.halign
        if valign is _UNSET:
            valign = cd.valign
        if fontscale is _UNSET:
            fontscale = cd.fontscale

        # --- 3. Resolve position ---
        # If cell_id already exists, we treat this as an update to an existing cell,
        # so we keep the same grid position AND list position, replacing the content.
        _overwrite_idx = None
        if cell_id in slide.cell_map:
            _overwrite_idx = slide._cells.index(slide.cell_map[cell_id])
            slide.remove_cell(cell_id=cell_id, _caller_is_cell_method=True)

        col, row = slide._resolve_position(col, row, colspan, rowspan)

        # --- 4-6. Validate ---
        _validate_placement(slide, col, row, colspan, rowspan)

        # --- 7. Build cell ---
        kwargs["_params"] = CellParams(
            col=col, row=row, cell_id=cell_id,
            colspan=colspan, rowspan=rowspan,
            caption=caption,
            overflow=overflow,
            copy_button=copy_button,
            expand_button=expand_button,
            transparent=transparent,
            halign=halign,
            valign=valign,
            fontscale=fontscale,
        )
        cell = cast("Callable[..., Cell]", fn)(slide, *args, **kwargs)

        # --- 8-9. Register and validate return ---
        if not isinstance(cell, Cell):
            raise TypeError(
                f"{fn.__name__} must return a Cell instance, "
                f"but returned {type(cell).__name__}"
            )

        slide._register_cell(cell, cell_id=cell_id, index=_overwrite_idx)

        # --- 10. Autosave if level cell
        if slide.parent.autosave and slide.parent.autosave_level == 'cell':
            slide.parent.write(slide.parent.autosave)

        return cell

    # The wrapper deliberately reshapes the signature (it consumes the cell
    # kwargs and injects _params), so cast it back to fn's signature so callers
    # and editors see each add_* method's real parameters and return type.
    return cast("Callable[_P, _R]", wrapper)


def _validate_placement(
    slide: "Slide",
    col: int, row: int,
    colspan: int, rowspan: int,
) -> None:
    from montin.exceptions import CellPlacementError

    nrows, ncols = slide.nrows, slide.ncols

    if not (1 <= col <= ncols):
        raise CellPlacementError(f"col={col} out of canvas range (1-{ncols})")
    if not (1 <= row <= nrows):
        raise CellPlacementError(f"row={row} out of canvas range (1-{nrows})")
    if col + colspan - 1 > ncols:
        raise CellPlacementError(f"col={col} + colspan={colspan} exceeds ncols={ncols}")
    if row + rowspan - 1 > nrows:
        raise CellPlacementError(f"row={row} + rowspan={rowspan} exceeds nrows={nrows}")

    for r in range(row, row + rowspan):
        for c in range(col, col + colspan):
            if slide._occupied[r - 1][c - 1]:
                raise CellPlacementError(
                    f"Position (row={r}, col={c}) is already occupied by another cell"
                )
