"""Generates the embedded previews for the "Themes" documentation section:

* ``theme_<name>.html`` — one file per built-in theme (the theme gallery), each
  rendering the same sample deck so themes can be compared like-for-like.
* ``themeopts_*.html`` — focused ``ThemeOptions`` demos (header styles + a fully
  branded deck) deep-linked from the docs via ``<iframe src="...#demo">``.

Because a theme and its ``ThemeOptions`` apply to the whole deck, each example is
its own file (unlike the per-slide layout examples). Written into
``docs/_static/deck/``; run via ``make.bat deck`` / any docs build. See conf.py.
"""

from montin import (
    Bars, Cells, Deck, Fonts, Footer, Header, Logo, Sidebar, Stage,
    ThemeOptions, Watermark,
)

# --- Standardized docs settings (docs/script-settings.yaml) -----------------
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from _docs_settings import FONTSCALE

OUT = "../../_static/deck"
LOGO = "../../_static/montin-logo-vertical.svg"   # real image logo for the branded demo

# Built-in themes shown in the gallery (default == docs, so docs is omitted).
GALLERY = [
    ("default",    "The default — documentation-site light"),
    ("docs-dark",  "Documentation site, dark"),
    ("montin",     "Brand Sand (light)"),
    ("ink",        "Brand Ink (dark)"),
    ("midnight",   "The original navy + pink-red"),
    ("light",      "Neutral light"),
    ("dark",       "Charcoal (VS Code-like)"),
    ("light-blue", "Soft blue light"),
    ("academic",   "Serif, paper-like"),
    ("sobrio",     "Minimalist, borderless"),
]


def _new(title, theme, **kw):
    return Deck(
        title=title,
        theme=theme,
        fontsize_scale=FONTSCALE,
        stage=Stage(size=(1280, 720), scale_up=True),
        sidebar=Sidebar(collapsed=True),
        **kw,
    )


def _sample(deck, cover_subtitle):
    """Populate a deck with a cover + one representative content slide (#demo)."""
    deck.add_title(deck.title, subtitle=cover_subtitle)
    s = deck.add_slide(
        "Quarterly results",
        subtitle="A representative content slide",
        nrows=2, ncols=3,
        slide_id="demo",
    )
    s.add_metric(value=98.7, label="Efficiency (%)", delta=2.3)
    s.add_metric(value=142, label="Defects", delta=-18)
    s.add_metric(value="4.8", label="NPS", delta=0.4)
    s.add_text(
        "### Highlights\n"
        "- Throughput up **12%**\n"
        "- Two incidents, both resolved\n"
        "- Link to the [dashboard](https://example.com)",
        colspan=1,
    )
    s.add_table(
        {"Run": [1, 2, 3], "Score": [0.91, 0.88, 0.94], "Status": ["ok", "ok", "ok"]},
        colspan=2, caption="Latest runs",
    )
    return deck


# --- Theme gallery ----------------------------------------------------------
for name, subtitle in GALLERY:
    deck = _new(f"Theme: {name}", name)
    _sample(deck, subtitle)
    deck.write(f"{OUT}/theme_{name}.html")
    print(f"theme_{name}.html written")


# --- ThemeOptions: header styles (compared side by side in the docs) --------
for style in ("ruler", "background", "gradient"):
    deck = _new(
        f"Header: {style}", "montin",
        theme_options=ThemeOptions(header=Header(style=style, color="#E07A3F")),
    )
    _sample(deck, f'header=Header(style="{style}")')
    deck.write(f"{OUT}/themeopts_header_{style}.html")
    print(f"themeopts_header_{style}.html written")


# --- ThemeOptions: a fully branded deck (the flagship example) --------------
branded = _new(
    "ACME Analytics", "montin",
    theme_options=ThemeOptions(
        header=Header(style="gradient", color="#E07A3F", subtitle_style="italic"),
        bars=Bars(sidebar="#0f1f2e", toolbar="#0f1f2e", text="#e9ecef"),
        cells=Cells(gap=16, radius=12, shadow=True),
        fonts=Fonts(family="Georgia, 'Times New Roman', serif"),
        footer=Footer(text="ACME Analytics · Confidential · {title} · {page}/{total}",
                      align="right"),
        watermark=Watermark(text="CONFIDENTIAL", position="center", opacity=0.06),
        logo=Logo(image=LOGO, placement="header", height=28),
        credit=True,
    ),
)
_sample(branded, "One ThemeOptions object: header, bars, footer, watermark, logo")
branded.write(f"{OUT}/themeopts_branded.html")
print("themeopts_branded.html written")
