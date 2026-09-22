"""Generates docs/_static/deck/tabulator.html — one slide per Tabulator feature
for the "Interactive tables" documentation section. Each slide has a stable
slide_id so the docs deep-link to it (e.g. <iframe src="...tabulator.html#formatters">).

Run via `make.bat deck` (or any docs build). See docs/conf.py.
"""

from montin import Deck, Plugins, Sidebar, Stage

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

deck = Deck(
    fontsize_scale=FONTSCALE,
    title="Interactive tables",
    plugins=[Plugins.Tabulator()],
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
)

data = {
    "Product":  ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"],
    "Category": ["Tools", "Tools", "Parts", "Parts", "Parts", "Tools"],
    "Revenue":  [12000, 8400, 15300, 4200, 9800, 6100],
    "Margin":   [62, 48, 71, 33, 55, 40],
    "Rating":   [4, 3, 5, 2, 4, 3],
    "Reviewed": [True, False, True, False, False, True],
}

# -- Basics: sort + per-header filtering -----------------------------------
s = deck.add_slide("TabulatorCell — add_tabulator()", slide_id="tabulator")
s.add_tabulator(
    data,
    header_filter=True,
    caption="Click a header to sort; type in a header to filter",
)

# -- Formatters & column calculations --------------------------------------
s = deck.add_slide("Formatters & calculations", slide_id="formatters")
s.add_tabulator(
    data,
    columns=[
        {"title": "Revenue", "formatter": "money",
         "formatterParams": {"symbol": "$", "precision": 0}, "bottomCalc": "sum"},
        {"title": "Margin", "formatter": "progress",
         "formatterParams": {"min": 0, "max": 100, "legend": True},
         "bottomCalc": "avg"},
        {"title": "Rating", "formatter": "star", "formatterParams": {"stars": 5}},
        {"title": "Reviewed", "formatter": "tickCross"},
    ],
    caption="money / progress / star / tickCross formatters, with sum & avg calcs",
)

# -- Grouping & pagination -------------------------------------------------
s = deck.add_slide("Grouping & pagination", slide_id="grouping")
s.add_tabulator(
    data,
    group_by="Category",
    pagination=4,
    columns=[
        {"title": "Revenue", "formatter": "money",
         "formatterParams": {"symbol": "$", "precision": 0}},
    ],
    caption="Grouped by Category, 4 rows per page",
)

# -- Inline editing & row selection ----------------------------------------
s = deck.add_slide("Editing & selection", slide_id="editing")
s.add_tabulator(
    data,
    selectable=True,
    columns=[
        {"title": "Reviewed", "formatter": "tickCross", "editor": True},
        {"title": "Margin", "editor": "number"},
    ],
    caption="Tick 'Reviewed' or edit 'Margin' inline; click rows to select",
)

# -- Download --------------------------------------------------------------
s = deck.add_slide("Download", slide_id="download")
s.add_tabulator(
    data,
    download=["csv", "json"],
    caption="Use the download buttons (top-right) to export CSV / JSON",
)

deck.write("../../_static/deck/tabulator.html")
print("tabulator.html written")
