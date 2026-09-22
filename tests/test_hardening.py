"""Tests for the architecture-review hardening pass: autoescape (data
integrity / XSS), resilient rendering (strict=False), dynamic plugin
declaration, isolated defaults, and preview/write idempotency."""

import dataclasses

import pytest

from montin import CellDefaults, Deck, Plugins, SlideDefaults
from montin.exceptions import CellPlacementError


def _render(deck, **kw):
    from montin.core.assembler import Assembler
    return Assembler(deck, **kw)._render()


# ---------------------------------------------------------------------------
# Autoescape: user data with <, >, &, quotes must render faithfully
# ---------------------------------------------------------------------------

def test_titles_and_table_values_are_escaped(tmp_path):
    deck = Deck(title="A & B <Campaign>")
    s = deck.add_slide("AoA <5deg & M>0.8", subtitle='cases "a" & \'b\'')
    s.add_table({"x < y": ["a<b", "c&d"]})
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    # Raw user angle brackets must never reach the markup...
    assert "<Campaign>" not in html
    assert "AoA <5deg" not in html
    assert "<td>a<b</td>" not in html
    # ...their escaped forms must (content preserved, not dropped).
    assert "A &amp; B &lt;Campaign&gt;" in html
    assert "AoA &lt;5deg &amp; M&gt;0.8" in html
    assert "a&lt;b" in html
    assert "c&amp;d" in html


def test_slide_id_with_quote_is_js_safe(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S", slide_id="it's-a-trap")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    # The id lands in single-quoted onclick handlers via tojson, so the raw
    # apostrophe never appears inside them (it is '-escaped).
    assert "goToSlide(\"it\\u0027s-a-trap\")" in html


def test_add_html_is_the_raw_escape_hatch(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S").add_html("<b class='k'>bold</b>")
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert "<b class='k'>bold</b>" in html


def test_add_text_plain_mode_escapes(tmp_path):
    deck = Deck(title="X")
    deck.add_slide("S").add_text("<script>alert(1)</script>", markdown=False)
    html = deck.write(tmp_path / "out").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ---------------------------------------------------------------------------
# Resilient rendering (strict=False)
# ---------------------------------------------------------------------------

class _BoomCell:
    """Minimal Cell stand-in whose render always fails."""


def _add_failing_cell(slide):
    cell = slide.add_text("ok")

    def boom(env):
        raise RuntimeError("pathological figure")

    cell.render = boom
    return cell


def test_strict_default_raises(tmp_path):
    deck = Deck(title="X")
    _add_failing_cell(deck.add_slide("S"))
    with pytest.raises(RuntimeError, match="pathological figure"):
        deck.write(tmp_path / "out")


def test_strict_false_degrades_to_error_box(tmp_path):
    deck = Deck(title="X")
    s1 = deck.add_slide("Bad")
    _add_failing_cell(s1)
    s2 = deck.add_slide("Good")
    s2.add_text("survivor")
    with pytest.warns(UserWarning, match="failed to render"):
        html = deck.write(tmp_path / "out", strict=False).read_text(encoding="utf-8")
    assert "cell-error" in html
    assert "pathological figure" in html
    assert "survivor" in html          # the rest of the deck still rendered


# ---------------------------------------------------------------------------
# Plugins can be declared after construction (dynamic _plugin_names)
# ---------------------------------------------------------------------------

def test_plugin_appended_after_init_is_seen():
    deck = Deck(title="X")
    slide = deck.add_slide("S")
    deck.plugins.append(Plugins.Mermaid())
    slide.add_mermaid("flowchart LR\n A --> B")   # must not raise


# ---------------------------------------------------------------------------
# Placement: half-specified positions fail early
# ---------------------------------------------------------------------------

def test_col_without_row_raises(deck):
    s = deck.add_slide("S", nrows=2, ncols=2)
    with pytest.raises(CellPlacementError, match="col= was given without row="):
        s.add_text("x", col=2)


# ---------------------------------------------------------------------------
# Default objects are not shared across decks
# ---------------------------------------------------------------------------

def test_default_objects_are_not_shared_between_decks():
    d1 = Deck(title="A")
    d2 = Deck(title="B")
    d1.cell_defaults.fontscale = 9.9
    d1.slide_defaults.nrows = 7
    d1.sidebar.collapsed = True
    assert d2.cell_defaults.fontscale == CellDefaults().fontscale
    assert d2.slide_defaults.nrows == SlideDefaults().nrows
    assert Deck(title="C").sidebar.collapsed is False


def test_plugin_instances_are_copied_per_deck():
    p = Plugins.MathJax()
    d1 = Deck(title="A", plugins=[p])
    d1.plugins[0].set_cdn("https://intranet.local/mathjax.js")
    d2 = Deck(title="B", plugins=[p])
    assert d2.plugins[0].url is None   # d1's mutation did not leak


# ---------------------------------------------------------------------------
# Render is idempotent: a preview must not contaminate a later write
# ---------------------------------------------------------------------------

def test_preview_then_write_still_saves_side_files(tmp_path):
    img = tmp_path / "pic.png"
    # Tiny valid PNG (1x1, pre-encoded).
    img.write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c62f8cfc0f01f000500fe02fe0d774d310000000049454e"
        "44ae426082"))
    deck = Deck(title="X")
    deck.add_slide("S").add_image(str(img), save_source=True)
    _render(deck)                                    # preview: inlines everything
    out = deck.write(tmp_path / "report")            # real write afterwards
    contents = out.parent / "_report_contents"
    saved = list(contents.glob("*.png")) if contents.exists() else []
    assert saved, "save_source side file must be written even after a preview"


def test_dataclass_module_stays_documented():
    # Guard: the grouped Deck options keep their user-facing docstrings.
    from montin import Sidebar, Stage
    for cls in (Stage, Sidebar):
        assert cls.__doc__
        for field in dataclasses.fields(cls):
            assert field.name in cls.__doc__, f"{field.name} missing in {cls.__name__} doc"
