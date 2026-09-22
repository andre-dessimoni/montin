"""montin.cells.plotly — PlotlyCell"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from montin.cells.base import Cell, CellParams

if TYPE_CHECKING:
    import jinja2
    import plotly.graph_objects as go


class PlotlyCell(Cell):
    """
    Interactive Plotly figure embedded as JSON.
    The cell always clips; the chart resizes to fit it.
    Requires Plugins.Plotly().
    """

    def __init__(self, fig: "go.Figure", params: CellParams,
                 save_source: bool = False) -> None:
        super().__init__(params)
        self.fig      = fig
        self.save_source = save_source
        self.fig_json = self._serialize(fig)

    def _serialize(self, fig: "go.Figure") -> str:
        """Serialize the Figure to JSON for template injection."""
        try:
            return fig.to_json()
        except Exception as exc:
            from montin.exceptions import InvalidDataError
            raise InvalidDataError(f"Failed to serialize Plotly figure: {exc}") from exc

    def finalize(self, ctx) -> None:
        # No fig -> nothing to save (cell built from extracted JSON).
        if not self.save_source or ctx.contents_dir is None or self.fig is None:
            return
        if getattr(self, "_finalized_key", None) == ctx.key():
            return   # same context as the previous render — nothing changed
        try:
            ctx.contents_dir.mkdir(parents=True, exist_ok=True)
            self.fig.write_html(str(ctx.contents_dir / f"{self._asset_stem()}.html"))
            self._finalized_key = ctx.key()
        except Exception:
            pass   # never fail a write because a side artifact could not be saved

    def render(self, env: "jinja2.Environment") -> str:
        # The figure JSON travels in a <script type="application/json"> block
        # (not an HTML attribute, where every quote would inflate to &quot;).
        # < and > are \u-escaped so the payload can never close the tag early —
        # same technique as TabulatorCell._safe_json.
        fig_json_embed = (
            self.fig_json.replace("<", "\\u003c").replace(">", "\\u003e")
        )
        return env.get_template("cell_plotly.html").render(
            cell=self, fig_json_embed=fig_json_embed)

    @classmethod
    def from_html(
        cls, path: "str | Path", params: CellParams, *, save_source: bool = False
    ) -> "PlotlyCell":
        """Build a cell from a figure saved with ``fig.write_html(...)``.

        Extracts the embedded figure JSON from the HTML and reconstructs an
        interactive chart. When plotly is installed the figure is rebuilt via
        ``plotly.io.from_json`` (so ``save_source`` works exactly as for a live
        figure); otherwise the extracted JSON is used directly with no live
        ``Figure`` object.
        """
        html = Path(path).read_text(encoding="utf-8")
        fig_json = _extract_figure_json(html)
        try:
            import plotly.io as pio
        except ImportError:
            return cls._from_fig_json(fig_json, params, save_source=save_source)
        return cls(fig=pio.from_json(fig_json), params=params, save_source=save_source)

    @classmethod
    def _from_fig_json(
        cls, fig_json: str, params: CellParams, *, save_source: bool = False
    ) -> "PlotlyCell":
        """Build a cell straight from a figure-JSON string, without a live
        ``Figure`` (and without importing plotly)."""
        obj = cls._raw_new(params)
        obj.fig = None
        obj.save_source = save_source
        obj.fig_json = fig_json
        return obj

    def _to_content(self, *, embed: bool = True) -> dict:
        # fig_json is already a JSON string and is all the template needs.
        return {"fig_json": self.fig_json, "save_source": self.save_source}

    @classmethod
    def _from_content(cls, content, params):
        # Restore fig_json directly (no plotly import / re-serialisation needed).
        return cls._from_fig_json(
            content["fig_json"], params, save_source=content.get("save_source", False)
        )

    def __repr__(self) -> str:
        return (
            f"PlotlyCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


# ---------------------------------------------------------------------------
# Extracting a figure from a Plotly write_html() file
# ---------------------------------------------------------------------------
#
# A Plotly HTML file embeds the figure as a call of the form
#     Plotly.newPlot("<div-id>", [<data>], {<layout>}, {<config>})
# inside a <script>. We locate that call and pull out the data array and layout
# object, which together form the figure JSON PlotlyCell stores.
#
# The string "Plotly.newPlot(" also appears in the bundled plotly.js library
# (e.g. a "Plotly.newPlot(gd, data, layout, ...)" doc snippet), so we scan *all*
# occurrences and keep the first whose arguments actually parse as
# string / array / object — the library ones have identifier args and are
# skipped automatically.


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\r\n":
        i += 1
    return i


def _read_string(s: str, i: int) -> tuple[str, int]:
    """Read a quoted string starting at ``s[i]``; return (text, index-after)."""
    quote = s[i]
    j = i + 1
    while j < len(s):
        if s[j] == "\\":
            j += 2
            continue
        if s[j] == quote:
            return s[i : j + 1], j + 1
        j += 1
    raise ValueError("unterminated string literal")


def _read_bracketed(s: str, i: int) -> tuple[str, int]:
    """Read a balanced ``[...]`` / ``{...}`` starting at ``s[i]`` (string-aware)."""
    open_ch = s[i]
    close_ch = "]" if open_ch == "[" else "}"
    depth = 0
    in_str = False
    quote = ""
    j = i
    while j < len(s):
        c = s[j]
        if in_str:
            if c == "\\":
                j += 2
                continue
            if c == quote:
                in_str = False
        elif c in "\"'":
            in_str = True
            quote = c
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return s[i : j + 1], j + 1
        j += 1
    raise ValueError("unbalanced brackets")


def _read_token(s: str, i: int) -> tuple[str, int]:
    """Read one JSON value (string / array / object) starting near ``i``."""
    i = _skip_ws(s, i)
    if i >= len(s):
        raise ValueError("unexpected end of input")
    c = s[i]
    if c in "\"'":
        return _read_string(s, i)
    if c in "[{":
        return _read_bracketed(s, i)
    raise ValueError(f"expected a string, array, or object at position {i}")


def _expect_comma(s: str, i: int) -> int:
    i = _skip_ws(s, i)
    if i >= len(s) or s[i] != ",":
        raise ValueError("expected ',' between Plotly.newPlot arguments")
    return i + 1


def _extract_figure_json(html: str) -> str:
    """Return the figure JSON (``{"data": ..., "layout": ...}``) from a Plotly
    ``write_html`` file. Raises ``InvalidDataError`` when none is found."""
    from montin.exceptions import InvalidDataError

    marker = "Plotly.newPlot("
    pos = html.find(marker)
    while pos != -1:
        fig_json = _parse_newplot_call(html, pos + len(marker))
        if fig_json is not None:
            return fig_json
        pos = html.find(marker, pos + 1)

    raise InvalidDataError(
        "No Plotly figure found in the HTML file (expected a "
        "'Plotly.newPlot(...)' call written by fig.write_html())."
    )


def _parse_newplot_call(html: str, i: int) -> "str | None":
    """Parse the arguments of one ``Plotly.newPlot(`` occurrence (``i`` points
    just after the ``(``). Returns the figure JSON, or ``None`` if these
    arguments aren't a figure (e.g. a library code snippet with identifier args
    or a malformed extraction)."""
    try:
        div_id, i = _read_token(html, i)    # the target <div> id (a string)
        i = _expect_comma(html, i)
        data, i = _read_token(html, i)      # the trace data array
        i = _expect_comma(html, i)
        layout, i = _read_token(html, i)    # the layout object
    except ValueError:
        return None
    if div_id[0] not in "\"'" or data[0] != "[" or layout[0] != "{":
        return None
    try:
        # Validate and normalise (rejects a malformed extraction).
        return json.dumps(json.loads(f'{{"data": {data}, "layout": {layout}}}'))
    except json.JSONDecodeError:
        return None