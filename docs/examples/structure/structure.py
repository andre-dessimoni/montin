"""Generates docs/_static/deck/title-sections-example.html — the embedded preview for
the "Deck structure" documentation section. Mirrors the "Putting it together"
example in docs/sections/structure.md: a title slide, an auto-populated TOC, and
sections at two levels (some with inline TOCs), plus an untracked appendix.

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
    title="Q3 Platform Report",
    author="A. Dessimoni",
    date="2025-06-01",
    version="3.0",
    plugins=[Plugins.Mermaid()],
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
    theme='light',
)

# -- Title + table of contents ---------------------------------------------
deck.add_title("Q3 Platform Report", subtitle="Platform Engineering", 
               title_id="title")
deck.add_toc(toc_id="toc")

# -- Infrastructure (level 1) with two sub-sections ------------------------
deck.add_section("Infrastructure", section_id="section_lvl1a")

deck.add_section("Networking", level=2, section_id="section_lvl2aa")
slide = deck.add_slide("Network overview", nrows=1, ncols=2)
slide.add_metric(value="12 ms", label="Avg latency", delta=-3, lower_is_better=True)
slide.add_metric(value="99.98 %", label="Uptime", delta=+0.02)

deck.add_section("Storage", level=2, section_id="section_lvl2ab")
slide = deck.add_slide("Storage capacity", nrows=1, ncols=2)
slide.add_metric(value="4.2 TB", label="Used")
slide.add_metric(value="12 TB", label="Total")

# -- Model Performance (level 1) -------------------------------------------
deck.add_section("Model Performance", section_id="section_lvl1b")
slide = deck.add_slide("Latency benchmarks", nrows=1, ncols=2, col_widths=["55%", "45%"])
slide.add_table({
    "Model":     ["v2.1", "v2.2", "v3.0"],
    "p50 (ms)":  [41, 38, 29],
    "p99 (ms)":  [120, 110, 88],
})
slide.add_mermaid("""
flowchart LR
    R[Request] --> Q[Queue]
    Q --> W[Worker]
    W --> C[(Cache)]
    W --> M[Model]
    M --> Resp[Response]
""", caption="Serving path")

# -- Appendix: excluded from the TOC and with no inline TOC ----------------
deck.add_section("Appendix", add_to_toc=False, show_toc=False, section_id="section_lvl3c")
slide = deck.add_slide("Methodology", nrows=1, ncols=1)
slide.add_text(
    "### Methodology\n\n"
    "Benchmarks were run on the staging cluster over a 24 h window. "
    "This section is intentionally **excluded from the table of contents** "
    "(`add_to_toc=False`)."
)

deck.write("../../_static/deck/title-sections-example.html")
print("title-sections-example.html written")
