"""Tests for Deck, Plugin, SlideDefaults, CellDefaults."""

import datetime
import re

import pytest

from montin import CellDefaults, Deck, Plugins, SlideDefaults
from montin.core.slide import Slide


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_title_stored():
    deck = Deck(title="My Deck")
    assert deck.title == "My Deck"


def test_date_auto_filled():
    deck = Deck(title="X")
    assert deck.date == datetime.date.today().isoformat()


def test_date_explicit():
    deck = Deck(title="X", date="2024-01-15")
    assert deck.date == "2024-01-15"


def test_plugins_stored():
    p1 = Plugins.Plotly(source="cdn")
    p2 = Plugins.Highlight(source="cdn")
    deck = Deck(title="X", plugins=[p1, p2])
    assert len(deck.plugins) == 2
    assert "plotly" in deck._plugin_names
    assert "highlight" in deck._plugin_names
    assert "mermaid" not in deck._plugin_names


def test_plugin_source_defaults_to_inherit():
    # An unset plugin source inherits the deck-wide default (cdn).
    assert Plugins.MathJax().source is None
    assert Deck(title="X").plugin_source == "cdn"


def test_slides_list_starts_empty():
    deck = Deck(title="X")
    assert deck.slides == []


def test_repr():
    deck = Deck(title="Rep", theme="default")
    r = repr(deck)
    assert "Rep" in r
    assert "default" in r


# ---------------------------------------------------------------------------
# add_title
# ---------------------------------------------------------------------------

def test_add_title_returns_slide():
    deck = Deck(title="X")
    s = deck.add_title("Cover")
    assert isinstance(s, Slide)
    assert s.slide_type == "title"


def test_add_title_appended():
    deck = Deck(title="X")
    deck.add_title("Cover")
    assert len(deck.slides) == 1


def test_add_title_grid_is_1x1():
    deck = Deck(title="X")
    s = deck.add_title("Cover")
    assert s.nrows == 1
    assert s.ncols == 1


# ---------------------------------------------------------------------------
# add_section
# ---------------------------------------------------------------------------

def test_add_section_type():
    deck = Deck(title="X")
    s = deck.add_section("Section 1")
    assert s.slide_type == "section"


def test_add_section_registers_in_sections():
    deck = Deck(title="X")
    deck.add_section("Intro", level=1)
    deck.add_section("Methods", level=2)
    assert len(deck.sections) == 2
    assert deck.sections[0]["title"] == "Intro"
    assert deck.sections[1]["level"] == 2


def test_add_section_slide_id_stored():
    deck = Deck(title="X")
    s = deck.add_section("Sec")
    assert deck.sections[0]["slide_id"] == s.slide_id


# ---------------------------------------------------------------------------
# add_toc
# ---------------------------------------------------------------------------

def test_add_toc_type():
    deck = Deck(title="X")
    t = deck.add_toc()
    assert t.slide_type == "toc"


def test_add_toc_auto_captures_sections(tmp_path):
    deck = Deck(title="X")
    deck.add_section("A")
    deck.add_section("B")
    toc = deck.add_toc(auto=True)
    deck.write(tmp_path / "out")
    assert len(toc._toc_entries) == 2
    assert toc._toc_entries[0]["title"] == "A"


def test_add_toc_auto_false_empty(tmp_path):
    deck = Deck(title="X")
    deck.add_section("A")
    toc = deck.add_toc(auto=False)
    deck.write(tmp_path / "out")
    assert toc._toc_entries == []


def test_add_toc_captures_all_sections(tmp_path):
    deck = Deck(title="X")
    deck.add_section("Before")
    toc = deck.add_toc(auto=True)
    deck.add_section("After")
    deck.write(tmp_path / "out")
    # TOC is populated at write() time — reflects all sections regardless of order
    assert len(toc._toc_entries) == 2


# ---------------------------------------------------------------------------
# add_slide
# ---------------------------------------------------------------------------

def test_add_slide_returns_slide():
    deck = Deck(title="X")
    s = deck.add_slide("Results")
    assert isinstance(s, Slide)
    assert s.slide_type == "slide"


def test_add_slide_uses_defaults():
    deck = Deck(title="X", slide_defaults=SlideDefaults(nrows=3, ncols=4))
    s = deck.add_slide("S")
    assert s.nrows == 3
    assert s.ncols == 4


def test_add_slide_overrides_defaults():
    deck = Deck(title="X", slide_defaults=SlideDefaults(nrows=3, ncols=4))
    s = deck.add_slide("S", nrows=1, ncols=2)
    assert s.nrows == 1
    assert s.ncols == 2


def test_slide_ids_increment():
    deck = Deck(title="X")
    s1 = deck.add_title("Cover")
    s2 = deck.add_slide("Slide 1")
    s3 = deck.add_slide("Slide 2")
    ids = [s1.slide_id, s2.slide_id, s3.slide_id]
    # Auto-generated ids carry a leading underscore to distinguish them from
    # user-supplied ids (see docs/sections/slide-ids.md).
    assert ids == ["_slide-1", "_slide-2", "_slide-3"]


def test_slides_property_returns_copy():
    deck = Deck(title="X")
    deck.add_slide("S")
    lst = deck.slides
    lst.append("fake")
    assert len(deck.slides) == 1  # original not mutated


# ---------------------------------------------------------------------------
# Overwrite by id — position preserved, no duplicates (Jupyter re-run)
# ---------------------------------------------------------------------------

def test_overwrite_slide_preserves_position():
    deck = Deck(title="X")
    deck.add_slide("A", slide_id="a")
    deck.add_slide("B", slide_id="b")
    deck.add_slide("C", slide_id="c")
    # Re-run the middle cell with new content.
    s = deck.add_slide("B updated", slide_id="b")
    ids = [sl.slide_id for sl in deck.slides]
    assert ids == ["a", "b", "c"]          # position kept, not moved to end
    assert len(deck.slides) == 3           # no duplicate
    assert deck.get_slide("b").title == "B updated"
    assert s is deck.get_slide("b")


def test_overwrite_title_by_id():
    deck = Deck(title="X")
    deck.add_title("Cover", title_id="cover")
    deck.add_title("Cover v2", title_id="cover")
    titles = [s for s in deck.slides if s.slide_type == "title"]
    assert len(titles) == 1
    assert titles[0].title == "Cover v2"


def test_overwrite_toc_by_id():
    deck = Deck(title="X")
    deck.add_toc(toc_id="toc")
    deck.add_toc(toc_id="toc")
    tocs = [s for s in deck.slides if s.slide_type == "toc"]
    assert len(tocs) == 1


def test_overwrite_section_dedups_toc():
    deck = Deck(title="X")
    deck.add_section("Alpha", section_id="s0")
    deck.add_section("Intro", section_id="i")
    deck.add_section("Beta", section_id="s2")
    # Re-run the Intro cell.
    deck.add_section("Intro renamed", section_id="i")
    sections = [s for s in deck.slides if s.slide_type == "section"]
    assert len(sections) == 3                      # no duplicate section slide
    assert [s["slide_id"] for s in deck.sections] == ["s0", "i", "s2"]  # TOC order kept
    intro = next(s for s in deck.sections if s["slide_id"] == "i")
    assert intro["title"] == "Intro renamed"


def test_section_add_to_toc_flip_removes_entry():
    deck = Deck(title="X")
    deck.add_section("Intro", section_id="i")
    assert any(s["slide_id"] == "i" for s in deck.sections)
    deck.add_section("Intro", section_id="i", add_to_toc=False)
    assert all(s["slide_id"] != "i" for s in deck.sections)


def test_remove_slide_purges_section_from_toc():
    deck = Deck(title="X")
    deck.add_section("Intro", section_id="i")
    deck.remove_slide("i")
    assert deck.sections == []


# ---------------------------------------------------------------------------
# Fixed-size (scaled stage) mode
# ---------------------------------------------------------------------------

def test_stage_defaults_to_none():
    deck = Deck(title="X")
    assert deck.stage is None


def test_stage_tuple_shorthand():
    from montin import Stage
    deck = Deck(title="X", stage=(1366, 768))
    assert isinstance(deck.stage, Stage)
    assert deck.stage.size == (1366, 768)
    assert deck.stage.scale_up is False
    assert deck.stage.keep_aspect_ratio is True


def test_fixed_size_markup(tmp_path):
    from montin import Stage
    deck = Deck(
        title="X", stage=Stage(size=(1280, 720), scale_up=True, keep_aspect_ratio=False)
    )
    deck.add_slide("S").add_text("hi")
    out = deck.write(tmp_path / "out")
    html = out.read_text(encoding="utf-8")
    assert "fixed-size" in _body_tag(html)
    assert 'data-width="1280"' in html
    assert 'data-height="720"' in html
    assert 'data-scale-up="true"' in html
    assert 'data-keep-aspect="false"' in html
    assert "--stage-w: 1280px" in html


def test_fluid_default_has_no_stage(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S").add_text("hi")
    out = deck.write(tmp_path / "out")
    html = out.read_text(encoding="utf-8")
    assert 'class="fixed-size"' not in html


def test_cover_centers_independent_of_flex_parent(tmp_path):
    # Regression: in fixed-size mode the flex container is .stage (the .slide is
    # display:block), so cover centering must live on .slide-cover itself
    # (margin:auto), not on the parent's align/justify. Otherwise section/title
    # cover slides render top-left when `size=` is set.
    deck = Deck(title="X", stage=(1280, 720))
    deck.add_section("My Section")
    out = deck.write(tmp_path / "out")
    html = out.read_text(encoding="utf-8")
    block = re.search(r"\.slide-cover\s*\{[^}]*\}", html)
    assert block is not None
    assert "margin: auto" in block.group(0)


# ---------------------------------------------------------------------------
# Chromeless modes (no sidebar / no toolbar)
# ---------------------------------------------------------------------------

def test_chrome_defaults_true():
    deck = Deck(title="X")
    assert deck.sidebar.show is True
    assert deck.show_toolbar is True


def test_default_renders_sidebar_and_toolbar(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert '<nav id="sidebar">' in html
    assert '<footer id="toolbar">' in html


def test_no_sidebar(tmp_path):
    deck = Deck(title="X", sidebar=False)
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert '<nav id="sidebar">' not in html
    assert 'id="sidebar-resize-handle"' not in html
    assert 'id="btn-sidebar"' not in html        # toggle button gone too
    assert "no-sidebar" in html                  # body class present
    assert '<footer id="toolbar">' in html       # toolbar still there


def test_no_toolbar(tmp_path):
    deck = Deck(title="X", show_toolbar=False)
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert '<footer id="toolbar">' not in html
    assert '<nav id="sidebar">' in html


def test_single_slide_chromeless(tmp_path):
    deck = Deck(
        title="X", sidebar=False, show_toolbar=False, stage=(960, 540)
    )
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert '<nav id="sidebar">' not in html
    assert '<footer id="toolbar">' not in html


def test_sidebar_collapsed_default_false():
    deck = Deck(title="X")
    assert deck.sidebar.collapsed is False


def _body_tag(html):
    i = html.find("<body")
    return html[i:html.find(">", i) + 1]


def test_sidebar_collapsed_adds_body_class(tmp_path):
    from montin import Sidebar
    deck = Deck(title="X", sidebar=Sidebar(collapsed=True))
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert "sb-collapsed" in _body_tag(html)
    assert '<nav id="sidebar">' in html        # sidebar still present (toggleable)
    assert 'id="btn-sidebar"' in html          # toggle button still present


def test_sidebar_collapsed_default_no_class(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert "sb-collapsed" not in _body_tag(html)


def test_sidebar_collapsed_ignored_without_sidebar(tmp_path):
    from montin import Sidebar
    deck = Deck(title="X", sidebar=Sidebar(collapsed=True, show=False))
    deck.add_slide("S").add_text("hi")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert "sb-collapsed" not in _body_tag(html)


# ---------------------------------------------------------------------------
# CellDefaults propagation
# ---------------------------------------------------------------------------

def test_cell_defaults_propagated(deck):
    deck2 = Deck(
        title="X",
        cell_defaults=CellDefaults(expand_button=True, overflow=False),
    )
    s = deck2.add_slide("S", nrows=1, ncols=1)
    cell = s.add_text("hello")
    assert cell.params.expand_button is True
    assert cell.params.overflow is False


def test_cell_default_overridden_per_call(deck):
    deck2 = Deck(
        title="X",
        cell_defaults=CellDefaults(expand_button=True),
    )
    s = deck2.add_slide("S", nrows=1, ncols=1)
    cell = s.add_text("hello", expand_button=False)
    assert cell.params.expand_button is False
