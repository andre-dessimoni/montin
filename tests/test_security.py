"""Tests for Security(...) hardening and the block_external offline guarantee."""

import dataclasses
import html as html_mod
import re

import pytest

from montin import Deck, Plugins, Security, SecurityError


def _render(deck):
    from montin.core.assembler import Assembler
    return Assembler(deck)._render()


def _deck(plugins=None, **security):
    d = Deck(title="X", plugins=plugins or [], security=Security(**security) if security else None)
    d.add_slide("S").add_text("hi")
    return d


# ---------------------------------------------------------------------------
# Default (light) hardening
# ---------------------------------------------------------------------------

def test_default_security_emits_light_hardening():
    html = _render(_deck())
    assert 'name="referrer" content="no-referrer"' in html
    assert "Permissions-Policy" in html
    # No CSP and no robots noindex unless asked for.
    assert "Content-Security-Policy" not in html
    assert "noindex" not in html


def test_noindex_opt_in():
    html = _render(_deck(noindex=True))
    assert 'content="noindex,nofollow"' in html


def test_custom_permissions_policy_string():
    html = _render(_deck(permissions_policy="geolocation=(self)"))
    assert 'content="geolocation=(self)"' in html


def test_permissions_policy_can_be_disabled():
    html = _render(_deck(permissions_policy=False))
    assert "Permissions-Policy" not in html


def test_no_referrer_can_be_disabled():
    html = _render(_deck(no_referrer=False))
    assert 'name="referrer"' not in html


# ---------------------------------------------------------------------------
# SRI on CDN plugins
# ---------------------------------------------------------------------------

def test_sri_adds_integrity_on_cdn_plugin():
    html = _render(_deck(plugins=[Plugins.Plotly(source="cdn")]))   # sri default True
    assert re.search(r'plotly-2\.35\.2\.min\.js"\s+integrity="sha384-', html)
    assert 'crossorigin="anonymous"' in html


def test_sri_off_drops_integrity():
    html = _render(_deck(plugins=[Plugins.Plotly(source="cdn")], sri=False))
    assert "integrity=" not in html


# ---------------------------------------------------------------------------
# block_external — the hard offline guarantee
# ---------------------------------------------------------------------------

def test_block_external_emits_strict_csp():
    html = _render(_deck(plugins=[Plugins.Plotly()], block_external=True))
    assert "Content-Security-Policy" in html
    # Attribute values are autoescaped (' -> &#39;); browsers decode them, so
    # compare against the unescaped document.
    unescaped = html_mod.unescape(html)
    assert "default-src 'none'" in unescaped
    assert "connect-src 'none'" in unescaped


def test_block_external_forces_bundled_and_has_no_external_loads():
    html = _render(_deck(plugins=[Plugins.Plotly()], block_external=True))
    # Plotly is inlined; no resource (script/link) loads from outside. A clickable
    # <a href> may remain — that's navigation, not a load.
    assert "cdn.plot.ly/plotly-2.35.2.min.js" not in html
    # No external <script src> / <link href> tags (string URLs inside the inlined
    # library body don't count — they never fetch, and the CSP blocks them anyway).
    assert not re.search(r'<script[^>]+src\s*=\s*["\']https?://', html)
    assert not re.search(r'<link[^>]+href\s*=\s*["\']https?://', html)


def test_block_external_rejects_explicit_cdn_plugin():
    deck = _deck(plugins=[Plugins.Plotly(source="cdn")], block_external=True)
    with pytest.raises(SecurityError, match="cdn"):
        _render(deck)


def test_block_external_catches_external_image():
    deck = Deck(title="X", security=Security(block_external=True))
    deck.add_slide("S").add_image("https://example.com/logo.png")
    with pytest.raises(SecurityError, match="example.com"):
        _render(deck)


def test_block_external_allows_navigation_links():
    # A clickable external <a href> is navigation, not a load — must be allowed.
    # (add_html is the raw-HTML path; add_text(markdown=False) escapes its input.)
    deck = Deck(title="X", security=Security(block_external=True))
    deck.add_slide("S").add_html('<a href="https://example.com">docs</a>')
    _render(deck)   # must not raise


def test_custom_csp_overrides_generated():
    html = _render(_deck(csp="default-src 'self'"))
    assert "content=\"default-src 'self'\"" in html_mod.unescape(html)


# ---------------------------------------------------------------------------
# Documentation contract: every field stays explained
# ---------------------------------------------------------------------------

def test_every_security_field_is_documented():
    # The whole point is that users can understand these; guard the docstring.
    assert Security.__doc__ and "block_external" in Security.__doc__
    for field in dataclasses.fields(Security):
        assert field.name in Security.__doc__, f"{field.name} missing from docstring"
