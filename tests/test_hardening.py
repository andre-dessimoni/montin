"""Tests for the architecture-review hardening pass: autoescape (data
integrity / XSS), resilient rendering (strict=False), dynamic plugin
declaration, isolated defaults, and preview/write idempotency."""

import pytest

from montin import Deck


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
