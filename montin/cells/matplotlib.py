"""montin.cells.matplotlib — MatplotlibCell"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from montin.cells.base import Cell, CellParams

if TYPE_CHECKING:
    import matplotlib.figure
    import jinja2


class MatplotlibCell(Cell):
    """
    Matplotlib figure embedded as an image.

    The figure is encoded at construction time — its bytes are snapshotted, so
    modifications made after ``add_matplotlib`` have no effect.

    Parameters
    ----------
    fig:
        A ``matplotlib.figure.Figure`` instance.
    dpi:
        Rendering resolution in dots per inch (raster formats only).
    fmt:
        ``"svg"`` (default) embeds an inline, infinitely-zoomable vector image —
        crisp and usually compact for typical plots (dense scatter/heatmaps can
        get large; use ``"webp"`` there). ``"webp"`` embeds a lossless-by-default
        WebP (requires Pillow; falls back to PNG). ``"png"`` embeds a PNG.
    lightbox:
        Open in fullscreen lightbox on click.
    webp_quality:
        WebP quality (1–100); ``None`` => lossless. Only used for ``fmt="webp"``.
    save_source:
        Also write the encoded figure into the deck's contents folder (see the
        Assembler). When the deck is not self-contained the cell points at that
        file instead of embedding inline.
    """

    def __init__(
        self,
        fig: "matplotlib.figure.Figure",
        dpi: int,
        fmt: Literal["svg", "png", "webp"],
        lightbox: bool,
        params: CellParams,
        webp_quality: int | None = None,
        save_source: bool = False,
    ) -> None:
        super().__init__(params)
        self.lightbox = lightbox
        self.fmt = fmt
        self.fig = fig
        self.save_source = save_source

        from montin.utils.media import data_uri
        payload, mime, ext, is_text = self._encode(fig, dpi, fmt, webp_quality)
        # Snapshot for the contents folder (raw file bytes), and the inline form.
        self._payload: bytes = payload
        self._mime: str = mime
        self._ext: str = ext
        self.is_svg: bool = is_text
        self.resolved_src: str = ""   # filled by the Assembler for folder mode
        if is_text:
            self.src = payload.decode("utf-8")       # inline <svg>…</svg>
        else:
            self.src = data_uri(payload, mime)       # data: URI for <img>

    @staticmethod
    def _encode(fig, dpi, fmt, quality):
        from montin.utils.media import figure_to_payload
        try:
            return figure_to_payload(fig, fmt, dpi, quality)
        except Exception as exc:
            from montin.exceptions import InvalidDataError
            raise InvalidDataError(f"Failed to encode matplotlib figure: {exc}") from exc

    def finalize(self, ctx) -> None:
        if getattr(self, "_finalized_key", None) == ctx.key():
            return   # same context as the previous render — nothing changed
        # Recompute from the current context — a preview may have run earlier.
        self.resolved_src = ""
        if self.save_source and ctx.contents_dir is not None:
            from montin.utils import media
            written = media.write_asset(
                ctx.contents_dir, self._asset_stem(), self._ext, self._payload)
            if not ctx.self_contained:
                self.resolved_src = media.rel_url(written, ctx.out_dir)
        self._finalized_key = ctx.key()

    def render(self, env: "jinja2.Environment") -> str:
        # Inline SVG only when we are embedding it (not pointing at a saved file).
        if self.is_svg and not self.resolved_src:
            return env.get_template("cell_matplotlib_svg.html").render(cell=self)
        return env.get_template("cell_matplotlib.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        # The live Figure cannot be reconstructed; we persist the already-encoded
        # image (always embedded — there is no external source to reference).
        import base64

        return {
            "payload_b64": base64.b64encode(self._payload).decode("ascii"),
            "mime": self._mime,
            "ext": self._ext,
            "is_svg": self.is_svg,
            "fmt": self.fmt,
            "lightbox": self.lightbox,
            "save_source": self.save_source,
        }

    @classmethod
    def _from_content(cls, content, params):
        # Rebuild from the encoded payload without re-running _encode — so a saved
        # report reloads (and re-renders) on a machine without matplotlib.
        import base64

        from montin.utils.media import data_uri

        obj = cls._raw_new(params)
        obj.lightbox = content.get("lightbox", True)
        obj.fmt = content.get("fmt", "svg")
        obj.fig = None
        obj.save_source = content.get("save_source", False)
        obj._payload = base64.b64decode(content["payload_b64"])
        obj._mime = content["mime"]
        obj._ext = content["ext"]
        obj.is_svg = content.get("is_svg", obj._ext == "svg")
        obj.resolved_src = ""
        if obj.is_svg:
            obj.src = obj._payload.decode("utf-8")
        else:
            obj.src = data_uri(obj._payload, obj._mime)
        return obj

    def __repr__(self) -> str:
        return (f"MatplotlibCell(ID={self.params.cell_id!r}, fmt={self.fmt!r}) "
                f"at row={self.params.row}, col={self.params.col})")
