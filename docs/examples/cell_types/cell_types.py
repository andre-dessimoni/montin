"""Generates docs/_static/deck/cell_types.html — one slide per cell type for
the "Cell types" documentation section. Each slide has a stable slide_id so the
docs deep-link to it (e.g. <iframe src="...cell_types.html#metric">). The slide
content mirrors the code snippets shown next to each iframe in cell-types.md.

Run via `make.bat deck` (or any docs build). See docs/conf.py.
"""

import plotly.express as px

from montin import Deck, Plugins, Sidebar, Stage

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

deck = Deck(
    fontsize_scale=FONTSCALE,
    title="Cell types",
    plugins=[
        Plugins.MathJax(),
        Plugins.Highlight(),
        Plugins.Plotly(),
        Plugins.Mermaid(),
    ],
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
)

# -- TextCell --------------------------------------------------------------
s = deck.add_slide("TextCell — add_text()", slide_id="text")
s.add_text(
    "### Title\n\nText with **bold**, *italic*, LaTeX: $E = mc^2$ "
    "and markdown list:\n\n"
    "- item 1\n - item 2\n - item 3\n   - item 3.1",
    markdown=True,
    caption="Source: internal report",
)

# -- MetricCell ------------------------------------------------------------
s = deck.add_slide("MetricCell — add_metric()", slide_id="metric", ncols=3)
s.add_metric(value=98.7, label="Efficiency (%)", delta=+2.3,
             delta_label="vs previous month")
s.add_metric(value=142, label="Incidents", delta=-18, lower_is_better=True,
             delta_label="vs previous month")
s.add_metric(value="4.8", label="NPS")

# -- TableCell -------------------------------------------------------------
s = deck.add_slide("TableCell — add_table()", slide_id="table")
s.add_table("""Component,Jan,Feb,Mar
Motor A,98.1,97.8,98.7
Motor B,94.3,95.1,96.2
Pump C,91.0,90.4,91.3""")

# -- ImageCell -------------------------------------------------------------
s = deck.add_slide("ImageCell — add_image()", slide_id="image")
s.add_image(
    "../example1/figs/s05c-isoq10-iso.webp",
    lightbox=True,
    caption="Fig. 1 — Click to open the lightbox (zoom / pan)",
)

# -- ImageSliderCell -------------------------------------------------------
s = deck.add_slide("ImageSliderCell — add_image_slider()", slide_id="image-slider")
s.add_image_slider(
    [
        "../example1/figs/c08c-isoq10-iso.webp",
        "../example1/figs/s05c-isoq10-iso.webp",
        "../example1/figs/s08c-isoq10-iso.webp",
    ],
    captions=["Original", "Strake a", "Strake b"],
    caption="Visual inspection — 3 samples (use the arrows)",
)

# -- ListCell --------------------------------------------------------------
s = deck.add_slide("ListCell — add_list()", slide_id="list", ncols=2)
s.add_list(
    ["Analysis", "Design", "Implementation", "Testing"],
    ordered=True,
    caption="Project phases",
)
s.add_list(
    ["Analysis", {"Design": ["UX", "Backend", "Database"]}, "Implementation"],
    caption="With sub-levels",
)

# -- CodeCell --------------------------------------------------------------
s = deck.add_slide("CodeCell — add_code()", slide_id="code")
s.add_code(
    "def hello():\n    return 'world'\n\n\nif __name__ == '__main__':\n"
    "    print(hello())",
    language="python",
    copy_button=True,
)

# -- PlotlyCell ------------------------------------------------------------
s = deck.add_slide("PlotlyCell — add_plotly()", slide_id="plotly")
fig = px.scatter(px.data.iris(), x="sepal_width", y="sepal_length", color="species")
s.add_plotly(fig, caption="Iris Dataset (interactive)")

# -- MermaidCell -----------------------------------------------------------
s = deck.add_slide("MermaidCell — add_mermaid()", slide_id="mermaid",
                     nrows=2, ncols=2, row_heights=["2fr", "1fr"])
s.add_mermaid("""
---
title: Simple sample
---
stateDiagram-v2
    [*] --> Still
    Still --> [*]
    Still --> Moving
    Moving --> Still
    Moving --> Crash
    Crash --> [*]
""")
s.add_mermaid("""
pie showData
    title Key elements in Product X
    "Calcium" : 42.96
    "Potassium" : 50.05
    "Magnesium" : 10.01
    "Iron" : 5
""")
s.add_mermaid("""
gantt
    title A Gantt Diagram
    dateFormat YYYY-MM-DD
    section Section
        A task          :a1, 2014-01-01, 30d
        Another task    :after a1, 20d
    section Another
        Task in Another :2014-01-12, 12d
        another task    :24d
""", colspan=2, row=2, col=1)

# -- HtmlCell --------------------------------------------------------------
s = deck.add_slide("HtmlCell — add_html()", slide_id="html")
s.add_html("""
<style>
@keyframes tsa-pulse { 0%,100%{transform:scale(1);opacity:1} 50%{transform:scale(1.18);opacity:.6} }
@keyframes tsa-glow  { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,0)} 50%{box-shadow:0 0 0 4px rgba(239,68,68,.22)} }
@keyframes tsa-slide { 0%{left:-40%} 100%{left:100%} }
.tsa-live { display:inline-block; animation:tsa-pulse 2s ease-in-out infinite; }
.tsa-crit { animation:tsa-glow 1.6s ease-in-out infinite; }
.tsa-bar  { position:relative; height:4px; margin-top:6px; border-radius:2px; background:#fecaca; overflow:hidden; }
.tsa-bar::after { content:""; position:absolute; top:0; left:-40%; width:40%; height:100%;
                  border-radius:2px; background:#ef4444; animation:tsa-slide 1.3s ease-in-out infinite; }
</style>
<div style="padding:1rem; display:flex; flex-direction:column; gap:0.75rem;
            font-family:sans-serif;">
  <div style="display:flex; gap:0.75rem; align-items:flex-start; padding:0.85rem 1rem;
              background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px;">
    <span class="tsa-live" style="font-size:1.2rem">&#x2705;</span>
    <div>
      <div style="font-weight:600; color:#15803d">Deploy v2.4.1 — successful</div>
      <div style="font-size:0.82rem; color:#166534">All regions live · 0 errors detected</div>
    </div>
  </div>
  <div style="display:flex; gap:0.75rem; align-items:flex-start; padding:0.85rem 1rem;
              background:#fffbeb; border:1px solid #fde68a; border-radius:8px;">
    <span style="font-size:1.2rem">&#x26A0;&#xFE0F;</span>
    <div>
      <div style="font-weight:600; color:#b45309">Node 3 — memory at 87%</div>
      <div style="font-size:0.82rem; color:#92400e">Consider scaling or restarting</div>
    </div>
  </div>
  <div class="tsa-crit" style="display:flex; gap:0.75rem; align-items:flex-start; padding:0.85rem 1rem;
              background:#fef2f2; border:1px solid #fecaca; border-radius:8px;">
    <span style="font-size:1.2rem">&#x1F534;</span>
    <div style="flex:1">
      <div style="font-weight:600; color:#b91c1c">DB timeout — us-east-1</div>
      <div style="font-size:0.82rem; color:#991b1b">Failover in progress · ETA 3 min</div>
      <div class="tsa-bar"></div>
    </div>
  </div>
</div>
""")

# -- IframeCell ------------------------------------------------------------
s = deck.add_slide("IframeCell — add_iframe()", slide_id="iframe")
s.add_iframe(
    "https://www.openstreetmap.org/export/embed.html?bbox=-46.50%2C-23.41%2C-45.63%2C-22.99&layer=mapnik",
    caption="Embedded interactive map (requires an internet connection)",
)

# -- EmptyCell -------------------------------------------------------------
s = deck.add_slide("EmptyCell — add_empty()", slide_id="empty", nrows=2, ncols=2)
s.add_metric(value=42, label="KPI", rowspan=2)   # col 1, rows 1-2
s.add_text("Text")                               # col 2, row 1
s.add_empty()                                    # col 2, row 2 — reserved space

deck.write("../../_static/deck/cell_types.html")
print("cell_types.html written")
