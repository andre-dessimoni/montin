"""montin.cells.image — ImageCell"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from montin.cells.base import Cell, CellParams

if TYPE_CHECKING:
    import jinja2


class ImageCell(Cell):
    """
    Image with lightbox (zoom/pan) and thumbnails for all images on the slide.
    Accepts a local path, URL, or base64 string.
    """

    def __init__(
        self,
        source: str | Path,
        lightbox: bool,
        params: CellParams,
        to_webp: bool = False,
        webp_quality: int | None = None,
        save_source: bool = False,
    ) -> None:
        super().__init__(params)
        self.lightbox = lightbox
        self.to_webp = to_webp
        self.webp_quality = webp_quality
        self.save_source = save_source
        # Resolve relative path against the caller's cwd immediately,
        # before the cwd can change. URLs and base64 strings are left as-is.
        s = str(source)
        if not s.startswith(("http://", "https://", "data:")) and not _looks_like_base64(s):
            self.source = Path(s).resolve()
        else:
            self.source = s
        self.resolved_src: str = ""  # filled by Assembler before render

    def finalize(self, ctx) -> None:
        from montin.utils import media
        if getattr(self, "_finalized_key", None) == ctx.key():
            return   # same context as the previous render — nothing changed
        self.resolved_src = media.resolve_image_source(
            self.source, to_webp=self.to_webp, quality=self.webp_quality,
            save_source=self.save_source, contents_dir=ctx.contents_dir,
            out_dir=ctx.out_dir, stem=self._asset_stem(),
            self_contained=ctx.self_contained)
        self._finalized_key = ctx.key()

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_image.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        if embed:
            from montin.io import embed_image_source

            source = embed_image_source(
                self.source, to_webp=self.to_webp, quality=self.webp_quality
            )
        else:
            # Reference mode: keep the path / URL as text (breaks if it moves).
            source = str(self.source)
        return {
            "source": source,
            "lightbox": self.lightbox,
            "to_webp": self.to_webp,
            "webp_quality": self.webp_quality,
            "save_source": self.save_source,
        }

    @classmethod
    def _from_content(cls, content, params):
        return cls(
            source=content["source"],
            lightbox=content.get("lightbox", True),
            params=params,
            to_webp=content.get("to_webp", False),
            webp_quality=content.get("webp_quality"),
            save_source=content.get("save_source", False),
        )

    def __repr__(self) -> str:
        return (
            f"ImageCell(ID={self.params.cell_id!r}, source={str(self.source)!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


def _looks_like_base64(s: str) -> bool:
    import re
    return len(s) > 64 and bool(re.fullmatch(r"[A-Za-z0-9+/=\n]+", s))
