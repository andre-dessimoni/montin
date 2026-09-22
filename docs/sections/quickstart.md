# Quick start

## Installation

```bash
# Core only
pip install montin

# Adds Markdown rendering + WebP image conversion
pip install "montin[full]"
```

Charts and tables use libraries you already have — `add_plotly` needs `plotly`,
`add_table(df)` / `add_matplotlib` need `pandas` / `matplotlib`. Since you create
those objects yourself, install them as you normally would; Montin doesn't pin
them.

## Basic structure

Every report follows the same pattern:

```python

import plotly.express as px
from montin import Deck, Plugins

# 1. Create the deck
deck = Deck(
    title="Q2 Report",
    author="A. Dessimoni",
    plugins=[Plugins.Plotly(), Plugins.Mermaid()],
)

# 2. Add slides

deck = Deck(title="Template Report", autosave='example', 
                    autosave_level='cell', plugins=[Plugins.Mermaid(), Plugins.Plotly()])

# Trend chart + breakdown table
slide = deck.add_slide("Trends", nrows=1, ncols=2)

df = px.data.stocks()
fig = px.line(df, x="date", y=["GOOG", "AAPL"])
slide.add_plotly(fig, caption="Weekly close price")

slide.add_table({
    "Component":  ["Motor A", "Motor B", "Pump C",  "Valve D"],
    "Status":     ["OK",      "OK",      "Warning", "OK"],
    "Uptime (%)": [99.1,      97.8,      91.3,      98.6],
})


# KPIs + pipeline diagram
slide = deck.add_slide("Overview", nrows=2, ncols=3)

slide.add_metric(value=98.7, label="Efficiency (%)", delta=+2.3, delta_label="vs Q1")
slide.add_metric(value=142,  label="Incidents",       delta=-18,  lower_is_better=True)
slide.add_metric(value="4.8 s", label="Avg response time")

slide.add_mermaid("""
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


# 3. Generate the file
deck.write("report", open_browser=True)
```

This generates `report.html` — a single file with no external dependencies.

For a better view, click the &#x26F6; `Fullscreen (F)` button on the bottom toolbar.

```{raw} html
<iframe class="montin-embed" src="../_static/quick-start-report.html"
        loading="lazy" allowfullscreen></iframe>
```


## Cell grid

Each slide has a CSS Grid canvas of `nrows x ncols`. Cells are positioned
automatically from left to right, top to bottom.

```python
slide = deck.add_slide("Example", nrows=2, ncols=3)

# Spans columns 1 and 2 of row 1
slide.add_text("Wide text", colspan=2)

# Column 3 of row 1
slide.add_metric(value=42, label="KPI")

# Row 2, spans all 3 columns
slide.add_table(csv_data, colspan=3)
```

To position manually:

```python
slide.add_image("photo.png", col=2, row=1, rowspan=2)
```

## Preview in a notebook

In Jupyter, return a deck, slide, or cell as a cell's last expression to render
it inline — no file written. A single slide doubles as a **layout for cell
outputs**: drop a few cells on its grid and display it.

```python
slide = deck.add_slide("Run 42", nrows=1, ncols=2)
slide.add_metric(value=0.94, label="Accuracy", delta=+0.02)
slide.add_plotly(fig)
slide   # renders a laid-out mini-dashboard as the cell output
```

See [Live editing](live-editing.md) for more.

## Plugins

Some cell types require a plugin, declared via the `Plugins` container and passed
to `Deck(plugins=[...])`. Nothing is mandatory — declare only what you use.

| Plugin | Cells |
|---|---|
| `Plugins.Plotly()` | `add_plotly()` |
| `Plugins.Highlight()` | `add_code()` |
| `Plugins.Mermaid()` | `add_mermaid()` |
| `Plugins.MathJax()` | LaTeX in `add_text()` |

Each loads from a CDN by default; pass `source="bundled"` (or
`Deck(plugin_source="bundled")`) to embed them for a fully offline file. See
[Plugins](plugins.md) and [Security & offline use](security.md) for details.

## Common cell options

All `add_*` methods accept:

| Parameter | Type | Description |
|---|---|---|
| `colspan` | `int` | Number of columns spanned |
| `rowspan` | `int` | Number of rows spanned |
| `col`, `row` | `int` | Manual position (1-indexed) |
| `caption` | `str` | Caption below the cell |
| `overflow` | `bool` | Internal scroll when content overflows |
| `expand_button` | `bool` | Button to expand cell to full screen |
| `copy_button` | `bool` | Button to copy cell content |
| `transparent` | `bool` | Hide border and background |
| `halign` | `"left"`/`"center"`/`"right"` | Horizontal alignment of cell content |
| `valign` | `"top"`/`"middle"`/`"bottom"` | Vertical alignment of cell content |
| `fontscale` | `float` | Multiplier for this cell's text size (composes on top of the deck's `fontsize_scale`) |

## Global defaults

Use `CellDefaults` and `SlideDefaults` to avoid repetition:

```python
deck = Deck(
    title="...",
    slide_defaults=SlideDefaults(nrows=2, ncols=2),
    cell_defaults=CellDefaults(
        expand_button=True,
        overflow=True,
        transparent=False,
        halign="center",
        valign="middle",
        fontscale=1.0,
    ),
)
```

## Font scaling

Scale text without editing each cell or writing custom CSS:

- `Deck(fontsize_scale=…)` multiplies **every** font in the presentation —
  slide content *and* the navigation chrome (sidebar, toolbar, TOC, lightbox).
  Spacing and layout are unaffected.
- `fontscale` (per cell, or as a `CellDefaults` default) scales a single cell's
  text and **composes on top of** `fontsize_scale`.

```python
deck = Deck(title="Report", fontsize_scale=1.2)   # everything 20% larger
slide.add_text("Headline", fontscale=1.5)         # this cell: 1.2 × 1.5
```

## Fixed-size slides

By default the layout is fluid and fills the browser window. Pass `stage` to
pin slides to fixed pixel dimensions instead. The slide becomes a *stage* that
is scaled with a CSS transform to fit the available space — fonts, images, and
layout all scale together, so the result behaves like a static PDF page.

```python
from montin import Deck, Stage

deck = Deck(
    title="Report",
    stage=Stage(
        size=(1366, 768),          # 16:9 stage in pixels
        scale_up=False,            # don't grow past 1:1 on large screens (default)
        keep_aspect_ratio=True,    # uniform scale + letterbox (default)
    ),
)

deck = Deck(title="Report", stage=(1366, 768))   # shorthand, default options
```

| Option | Effect |
|---|---|
| `Stage(size=(w, h))` | Enables fixed-size mode. `Deck(stage=None)` (default) keeps the fluid layout |
| `Stage(scale_up=True)` | Allow the stage to grow beyond its native size to fill larger windows |
| `Stage(keep_aspect_ratio=False)` | Stretch to fill both dimensions independently (distorts content) |

This is also the recommended mode for embedding a deck in an `<iframe>`, since
the slide keeps a predictable aspect ratio regardless of the frame size.

## Single-slide / embeddable files

For a clean, minimal file — such as the slides embedded throughout this
documentation — hide the navigation sidebar and/or the bottom toolbar:

```python
deck = Deck(
    title="Demo",
    stage=(960, 540),
    sidebar=False,
    show_toolbar=False,
)
deck.add_slide("Just this slide").add_text("No chrome around me.")
```

With both hidden the slide fills the whole frame. Combine with `stage` for a
fixed aspect ratio that embeds cleanly in an `<iframe>`.

To keep the sidebar available but out of the way, start it collapsed instead of
hiding it — it can still be toggled open with the toolbar button or the `B` key:

```python
from montin import Deck, Sidebar

deck = Deck(title="Report", sidebar=Sidebar(collapsed=True))
```

## Sidebar navigation

For longer decks the sidebar has two navigation aids, both on by default:

- A **regex search box** at the top that live-filters slides as you type.
- **Collapsible sections** — a caret on each section item folds/unfolds the
  slides under it. Nested sub-sections fold with their parent, and the
  collapsed state is remembered across reloads.

```python
from montin import Deck, Sidebar

deck = Deck(
    title="Report",
    sidebar=Sidebar(
        search=True,                 # show the filter box (default)
        search_scope="title",        # "title" | "title_subtitle" | "content"
        collapsible_sections=True,   # show section carets (default)
    ),
)
```

| Option | Effect |
|---|---|
| `Sidebar(search=...)` | Show/hide the search box |
| `Sidebar(search_scope=...)` | What the regex matches: the title, title + subtitle, or the slide's full rendered text (`"content"`) |
| `Sidebar(collapsible_sections=...)` | Show/hide the fold carets on section items |

The search is case-insensitive and accepts full JavaScript regex (e.g.
`^Intro|results$`); an invalid pattern simply leaves the list unfiltered. While a
search is active it overrides collapsed sections, so a match is never hidden.
