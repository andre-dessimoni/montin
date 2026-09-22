"""Generates docs/_static/quick-start-report.html — the embedded preview for the
"Basic structure" example in the Quick start docs. Kept in sync (by hand) with the
illustrative code block in docs/sections/quickstart.md.

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
    title="Q2 Report",
    author="A. Dessimoni",
    plugins=[Plugins.Plotly(), Plugins.Mermaid()],
    stage=Stage(size=(1280, 720), scale_up=True),
    sidebar=Sidebar(collapsed=True),
)

# -- KPIs + pipeline diagram -----------------------------------------------
slide = deck.add_slide("Overview", nrows=2, ncols=3)
slide.add_metric(value=98.7, label="Efficiency (%)", delta=+2.3, delta_label="vs Q1")
slide.add_metric(value=142, label="Incidents", delta=-18, lower_is_better=True)
slide.add_metric(value="4.8 s", label="Avg response time")
slide.add_mermaid("""
gantt
    title Delivery timeline
    dateFormat YYYY-MM-DD
    section Build
        Design       :a1, 2014-01-01, 30d
        Implement    :after a1, 20d
    section Ship
        QA           :2014-02-12, 12d
        Release      :24d
""", colspan=2, row=2, col=1)

# -- Trend chart + breakdown table -----------------------------------------
slide = deck.add_slide("Trends", nrows=1, ncols=2)

df = px.data.stocks()
fig = px.line(df, x="date", y=["GOOG", "AAPL"])
slide.add_plotly(fig, caption="Weekly close price")

slide.add_table({
    "Component":  ["Motor A", "Motor B", "Pump C",  "Valve D"],
    "Status":     ["OK",      "OK",      "Warning", "OK"],
    "Uptime (%)": [99.1,      97.8,      91.3,      98.6],
})

deck.write("../../_static/quick-start-report.html")
print("quick-start-report.html written")
