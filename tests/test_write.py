"""End-to-end tests: Deck.write() generates correct HTML output."""

import pytest

from montin import CellDefaults, Deck, Plugins, Sidebar, SlideDefaults


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def minimal_deck(**kwargs):
    return Deck(title="Test Report", **kwargs)


# ---------------------------------------------------------------------------
# File generation
# ---------------------------------------------------------------------------

def test_write_creates_file(tmp_path):
    deck = minimal_deck()
    deck.add_title("Cover")
    out = deck.write(tmp_path / "report", open_browser=False)
    assert out.exists()
    assert out.suffix == ".html"


def test_write_returns_path_object(tmp_path):
    from pathlib import Path
    deck = minimal_deck()
    deck.add_title("Cover")
    out = deck.write(tmp_path / "out", open_browser=False)
    assert isinstance(out, Path)


def test_write_adds_html_suffix(tmp_path):
    deck = minimal_deck()
    deck.add_title("X")
    out = deck.write(tmp_path / "deck", open_browser=False)
    assert out.name == "deck.html"


def test_write_does_not_double_suffix(tmp_path):
    deck = minimal_deck()
    deck.add_title("X")
    out = deck.write(tmp_path / "deck.html", open_browser=False)
    assert out.name == "deck.html"


# ---------------------------------------------------------------------------
# Content correctness
# ---------------------------------------------------------------------------

def test_output_contains_title(tmp_path):
    deck = minimal_deck()
    deck.add_title("My Unique Title XYZ")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "My Unique Title XYZ" in html


def test_output_contains_slide_title(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("Results Dashboard", nrows=1, ncols=1)
    s.add_text("Some content")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Results Dashboard" in html


def test_output_contains_section_title(tmp_path):
    deck = minimal_deck()
    deck.add_section("Introduction")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Introduction" in html


def test_output_is_valid_html_skeleton(tmp_path):
    deck = minimal_deck()
    deck.add_title("X")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html or "<html" in html


def test_output_contains_cell_caption(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_metric(value=42, label="KPI", caption="Unique Caption 12345")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Unique Caption 12345" in html


# ---------------------------------------------------------------------------
# Multiple slides
# ---------------------------------------------------------------------------

def test_output_contains_all_slide_titles(tmp_path):
    deck = minimal_deck()
    deck.add_title("Cover Slide")
    deck.add_section("Section One")
    s = deck.add_slide("Data Slide", nrows=1, ncols=2)
    s.add_metric(value=1, label="A")
    s.add_metric(value=2, label="B")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Cover Slide" in html
    assert "Section One" in html
    assert "Data Slide" in html


# ---------------------------------------------------------------------------
# Cell types in output
# ---------------------------------------------------------------------------

def test_table_csv_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_table("Name,Score\nAlice,95\nBob,87")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Alice" in html
    assert "Score" in html


def test_text_cell_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_text("Unique text content ABCDE")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Unique text content ABCDE" in html


def test_list_cell_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_list(["Step alpha", "Step beta", "Step gamma"])
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Step alpha" in html


def test_toc_entries_in_output(tmp_path):
    deck = minimal_deck()
    deck.add_section("Chapter One")
    deck.add_section("Chapter Two")
    deck.add_toc()
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "Chapter One" in html
    assert "Chapter Two" in html


# ---------------------------------------------------------------------------
# Plugin-dependent cells
# ---------------------------------------------------------------------------

def test_code_cell_in_output(tmp_path):
    deck = Deck(title="T", plugins=[Plugins.Highlight(source="cdn")])
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_code("x = 42", language="python")
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    assert "x = 42" in html


def test_halign_center_class_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_text("centered", halign="center")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert "cell-halign-center" in html


def test_valign_middle_class_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_metric(value=99, label="KPI", valign="middle")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert "cell-valign-middle" in html


def test_default_halign_left_class_in_output(tmp_path):
    deck = minimal_deck()
    s = deck.add_slide("S", nrows=1, ncols=1)
    s.add_text("default")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert "cell-halign-left" in html
    assert "cell-valign-top" in html


def test_plotly_cell_in_output(tmp_path):
    px = pytest.importorskip("plotly.express")
    deck = Deck(title="T", plugins=[Plugins.Plotly(source="cdn")])
    s = deck.add_slide("S", nrows=1, ncols=1)
    fig = px.scatter(x=[1, 2], y=[3, 4], title="Scatter XYZ")
    s.add_plotly(fig)
    out = deck.write(tmp_path / "out", open_browser=False)
    html = out.read_text(encoding="utf-8")
    # Plotly embeds JSON with the figure data
    assert "Scatter XYZ" in html


# ---------------------------------------------------------------------------
# Sidebar search & collapsible sections
# ---------------------------------------------------------------------------

def test_sidebar_feature_defaults():
    deck = Deck(title="T")
    assert deck.sidebar.search is True
    assert deck.sidebar.search_scope == "title"
    assert deck.sidebar.collapsible_sections is True


def test_sidebar_search_and_caret_in_output(tmp_path):
    deck = minimal_deck()
    deck.add_section("Intro")
    s = deck.add_slide("Data", nrows=1, ncols=1)
    s.add_text("x")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-search"' in html
    assert "filterSidebar(" in html
    assert 'data-sb-search-scope="title"' in html
    assert "sidebar-caret" in html
    assert "onclick='toggleSection(event" in html
    assert 'data-type="section"' in html


def test_sidebar_search_scope_content(tmp_path):
    deck = minimal_deck(sidebar=Sidebar(search_scope="content"))
    deck.add_title("X")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'data-sb-search-scope="content"' in html


def test_sidebar_search_disabled(tmp_path):
    deck = minimal_deck(sidebar=Sidebar(search=False))
    deck.add_title("X")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-search"' not in html


def test_sidebar_collapsible_sections_disabled(tmp_path):
    deck = minimal_deck(sidebar=Sidebar(collapsible_sections=False))
    deck.add_section("Intro")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    # The inline caret onclick must be gone (the JS function definition remains).
    assert "onclick='toggleSection(event" not in html
    assert "sidebar-caret-spacer" in html   # section falls back to the spacer


def test_sidebar_search_absent_when_no_sidebar(tmp_path):
    deck = minimal_deck(sidebar=False)
    deck.add_title("X")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-search"' not in html
    assert '<nav id="sidebar">' not in html


def test_sidebar_regex_toggle_and_tooltip(tmp_path):
    deck = minimal_deck()
    deck.add_slide("Data", nrows=1, ncols=1).add_text("x")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-regex-toggle"' in html
    assert "toggleRegexMode(" in html
    assert 'id="sidebar-regex-tip"' in html


def test_sidebar_regex_toggle_absent_when_search_off(tmp_path):
    deck = minimal_deck(sidebar=Sidebar(search=False))
    deck.add_slide("Data", nrows=1, ncols=1).add_text("x")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-regex-toggle"' not in html


def test_sidebar_fold_bar_present(tmp_path):
    deck = minimal_deck()
    deck.add_section("Intro")
    deck.add_slide("Data", nrows=1, ncols=1).add_text("x")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-fold-bar"' in html
    assert "collapseAllSections(" in html
    assert "expandAllSections(" in html
    assert "collapseLevel(" in html
    assert "expandLevel(" in html


def test_sidebar_fold_bar_absent_when_collapsible_off(tmp_path):
    deck = minimal_deck(sidebar=Sidebar(collapsible_sections=False))
    deck.add_section("Intro")
    html = deck.write(tmp_path / "out", open_browser=False).read_text(encoding="utf-8")
    assert 'id="sidebar-fold-bar"' not in html
