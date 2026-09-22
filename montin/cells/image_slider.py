"""montin.cells.image_slider — ImageSliderCell"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from montin.cells.base import Cell, CellParams

if TYPE_CHECKING:
    import jinja2


class ImageSliderCell(Cell):
    """
    Image carousel with prev/next buttons.
    Clicking an image opens the lightbox with zoom/pan.
    Slider images also appear as lightbox thumbnails.
    """

    _DEFAULT_OVERFLOW = False

    def __init__(
        self,
        sources: list,
        captions: list[str],
        params: CellParams,
        to_webp: bool = False,
        webp_quality: int | None = None,
        save_source: bool = False,
    ) -> None:
        super().__init__(params)
        self.sources = sources            # paths / urls / base64 / matplotlib Figures
        self.captions = captions
        self.to_webp = to_webp
        self.webp_quality = webp_quality
        self.save_source = save_source
        self.resolved_srcs: list[str] = []  # filled by Assembler

    def finalize(self, ctx) -> None:
        from montin.utils import media
        if getattr(self, "_finalized_key", None) == ctx.key():
            return   # same context as the previous render — nothing changed
        stem = self._asset_stem()
        self.resolved_srcs = [
            media.resolve_image_source(
                s, to_webp=self.to_webp, quality=self.webp_quality,
                save_source=self.save_source, contents_dir=ctx.contents_dir,
                out_dir=ctx.out_dir, stem=(f"{stem}__{i}" if i else stem),
                self_contained=ctx.self_contained)
            for i, s in enumerate(self.sources)
        ]
        self._finalized_key = ctx.key()

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_image_slider.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        from montin.io import embed_image_source

        # Figures have no external source, so they are embedded even in reference
        # mode; other sources are embedded only when embed=True.
        sources = [
            embed_image_source(s, to_webp=self.to_webp, quality=self.webp_quality)
            if (embed or hasattr(s, "savefig"))
            else str(s)
            for s in self.sources
        ]
        return {
            "sources": sources,
            "captions": list(self.captions),
            "to_webp": self.to_webp,
            "webp_quality": self.webp_quality,
            "save_source": self.save_source,
        }

    @classmethod
    def _from_content(cls, content, params):
        return cls(
            sources=content.get("sources", []),
            captions=content.get("captions", []),
            params=params,
            to_webp=content.get("to_webp", False),
            webp_quality=content.get("webp_quality"),
            save_source=content.get("save_source", False),
        )

    def __repr__(self) -> str:
        return (
            f"ImageSliderCell(ID={self.params.cell_id!r}, sources={self.sources!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )

