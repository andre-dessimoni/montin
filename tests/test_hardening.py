"""Tests for the architecture-review hardening pass: autoescape (data
integrity / XSS), resilient rendering (strict=False), dynamic plugin
declaration, isolated defaults, and preview/write idempotency."""

from montin import Deck


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
