"""Generates docs/_static/deck/layout.html — the embedded previews for the
"Layout" documentation section. Each slide has a stable slide_id so the docs can
deep-link to it from an <iframe src="...layout.html#grid-sizing"> block.

Run via `make.bat deck` (or any docs build). See docs/conf.py.
"""

from montin import CellDefaults, Deck, Sidebar, SlideDefaults, Stage

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

deck = Deck(
    fontsize_scale=FONTSCALE,
    title="Layout",
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
)

# -- Auto-placement (grid-basic) -------------------------------------------
s = deck.add_slide(
    "Auto-placement",
    subtitle="Cells fill the grid left-to-right, top-to-bottom",
    nrows=2, ncols=3,
    slide_id="grid-basic",
    cell_defaults=CellDefaults(halign="center", valign="middle"),
)
for label in ["A", "B", "C", "D", "E"]:
    s.add_text(f"### {label}")
s.add_text("### F", row=2, col=3)

# -- Column widths & row heights (grid-sizing) -----------------------------
s = deck.add_slide(
    "Column widths & row heights",
    subtitle='col_widths=["2fr", "1fr"], row_heights=["120px", "1fr"]',
    nrows=2, ncols=2,
    col_widths=["2fr", "1fr"],
    row_heights=["120px", "1fr"],
    slide_id="grid-sizing",
    cell_defaults=CellDefaults(halign="center", valign="middle"),
)
s.add_text("### 2fr × 120px")
s.add_text("### 1fr × 120px")
s.add_text("### 2fr × 1fr")
s.add_text("### 1fr × 1fr")

# -- Spanning cells (grid-spanning) ----------------------------------------
s = deck.add_slide(
    "Spanning cells",
    subtitle="colspan / rowspan stretch a cell across the grid",
    nrows=2, ncols=3,
    slide_id="grid-spanning",
)
s.add_text("### Wide header\n\n`colspan=2`", colspan=2,
           halign="center", valign="middle")
s.add_metric(value=42, label="KPI", col=3, row=1)
s.add_table(
    {"Col a": [1, 2, 3], "Col b": [4, 5, 6]},
    colspan=3, row=2, col=1,
    caption="A table spanning the full bottom row (colspan=3)",
)

# -- Layout templates (templates-results / templates-summary) --------------
slide_2x2 = SlideDefaults(ncols=2, nrows=2)
slide_2x1 = SlideDefaults(ncols=2, nrows=1)
centered  = CellDefaults(halign="center", valign="middle")

s = deck.add_slide(
    "Results", subtitle="slide_2x2 + centered cell template",
    slide_defaults=slide_2x2, cell_defaults=centered,
    slide_id="templates-results",
)
for i in range(s.nrows * s.ncols):
    s.add_text(f"### Cell {i}")

s = deck.add_slide(
    "Summary", subtitle="slide_2x1 — cell defaults fall back to global (left-aligned)",
    slide_defaults=slide_2x1,
    slide_id="templates-summary",
)
for i in range(s.nrows * s.ncols):
    s.add_text(f"Cell {i}")

deck.write("../../_static/deck/layout.html")
print("layout.html written")
