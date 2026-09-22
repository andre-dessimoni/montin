"""Generates docs/_static/deck/links.html — three slides for the "Links"
documentation section. Each slide has a stable slide_id so Markdown links inside
add_text() can point at it with [text](#slide_id): slides 1 and 2 link to each
other, and slide 3 links out to an external website.

Run via `make.bat deck` (or any docs build). See docs/conf.py.
"""

from montin import Deck, Sidebar, Stage

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

deck = Deck(
    fontsize_scale=FONTSCALE,
    title="Links",
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
)

# -- Slide 1 — internal link to slide 2 -----------------------------------
s = deck.add_slide("Introduction", slide_id="intro")
s.add_text(
    "### Welcome\n\n"
    "A report can link between its own slides. The link below points at the "
    "slide whose `slide_id` is `details`:\n\n"
    "[Go to the Details slide &rarr;](#details)",
    caption="Internal link — [text](#slide_id)",
)

# -- Slide 2 — internal link back to slide 1 ------------------------------
s = deck.add_slide("Details", slide_id="details")
s.add_text(
    "### Details\n\n"
    "This slide links back to where we started:\n\n"
    "[&larr; Back to the Introduction](#intro)",
    caption="Internal link — [text](#slide_id)",
)

# -- Slide 3 — external link ----------------------------------------------
s = deck.add_slide("Resources", slide_id="resources")
s.add_text(
    "### Resources\n\n"
    "Markdown links to external pages work too — for example, a link to "
    "[Google](https://www.google.com).",
    caption="External link — [text](https://…)",
)

deck.write("../../_static/deck/links.html")
print("links.html written")
