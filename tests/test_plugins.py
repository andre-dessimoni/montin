"""Tests for plugin declaration and missing-plugin errors."""

import pathlib

import pytest

from montin import Deck, Plugins
from montin.exceptions import PluginNotDeclaredError

_PLUGIN_BY_NAME = {
    "plotly": Plugins.Plotly,
    "mermaid": Plugins.Mermaid,
    "highlight": Plugins.Highlight,
    "mathjax": Plugins.MathJax,
    "tabulator": Plugins.Tabulator,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def deck_without_plugins():
    return Deck(title="Test", plugins=[])


def deck_with(*names):
    return Deck(title="Test", plugins=[_PLUGIN_BY_NAME[n](source="cdn") for n in names])


# ---------------------------------------------------------------------------
# add_code — requires "highlight"
# ---------------------------------------------------------------------------

def test_add_code_without_highlight_raises():
    deck = deck_without_plugins()
    s = deck.add_slide("S", nrows=1, ncols=1)
    with pytest.raises(PluginNotDeclaredError, match="(?i)highlight"):
        s.add_code("print('hi')", language="python")


def test_add_code_with_highlight_succeeds():
    deck = deck_with("highlight")
    s = deck.add_slide("S", nrows=1, ncols=1)
    cell = s.add_code("x = 1", language="python")
    assert cell.language == "python"


# ---------------------------------------------------------------------------
# add_mermaid — requires "mermaid"
# ---------------------------------------------------------------------------

def test_add_mermaid_without_plugin_raises():
    deck = deck_without_plugins()
    s = deck.add_slide("S", nrows=1, ncols=1)
    with pytest.raises(PluginNotDeclaredError, match="(?i)mermaid"):
        s.add_mermaid("flowchart LR\n  A --> B")


def test_add_mermaid_with_plugin_succeeds():
    deck = deck_with("mermaid")
    s = deck.add_slide("S", nrows=1, ncols=1)
    cell = s.add_mermaid("flowchart LR\n  A --> B")
    assert "A --> B" in cell.diagram


# ---------------------------------------------------------------------------
# add_plotly — requires "plotly"
# ---------------------------------------------------------------------------

def test_add_plotly_without_plugin_raises():
    px = pytest.importorskip("plotly.express")
    deck = deck_without_plugins()
    s = deck.add_slide("S", nrows=1, ncols=1)
    fig = px.scatter(x=[1], y=[1])
    with pytest.raises(PluginNotDeclaredError, match="(?i)plotly"):
        s.add_plotly(fig)


def test_add_plotly_with_plugin_succeeds():
    px = pytest.importorskip("plotly.express")
    deck = deck_with("plotly")
    s = deck.add_slide("S", nrows=1, ncols=1)
    fig = px.scatter(x=[1, 2], y=[3, 4])
    cell = s.add_plotly(fig)
    assert cell is not None


# ---------------------------------------------------------------------------
# Other plugins don't interfere
# ---------------------------------------------------------------------------

def test_having_mermaid_does_not_satisfy_highlight():
    deck = deck_with("mermaid")
    s = deck.add_slide("S", nrows=1, ncols=1)
    with pytest.raises(PluginNotDeclaredError, match="(?i)highlight"):
        s.add_code("x = 1")


def test_error_message_mentions_method_name():
    deck = deck_without_plugins()
    s = deck.add_slide("S", nrows=1, ncols=1)
    with pytest.raises(PluginNotDeclaredError, match="add_code"):
        s.add_code("x = 1")


# ---------------------------------------------------------------------------
# Plugin asset resolution (CDN vs bundled, version/url overrides, options)
# ---------------------------------------------------------------------------

from montin.utils.vendor import load_manifest, resolve_plugin   # noqa: E402


def _only(plugin, **kw):
    kw.setdefault("self_contained", True)
    kw.setdefault("sri", True)
    return resolve_plugin(plugin, **kw)["assets"]


def test_cdn_emits_src_with_sri():
    (a,) = _only(Plugins.Plotly(), source="cdn")
    assert a["mode"] == "src"
    assert "plotly-2.35.2.min.js" in a["url"]
    assert a["integrity"].startswith("sha384-")


def test_cdn_without_sri_has_no_integrity():
    (a,) = _only(Plugins.Plotly(), source="cdn", sri=False)
    assert a["integrity"] is None


def test_bundled_self_contained_inlines_file():
    (a,) = _only(Plugins.Plotly(), source="bundled")
    assert a["mode"] == "inline"
    assert a["path"].name == "plotly.min.js"


def test_bundled_not_self_contained_copies_file():
    (a,) = _only(Plugins.Plotly(), source="bundled", self_contained=False)
    assert a["mode"] == "copy"
    assert a["filename"] == "plotly.min.js"


def test_cdn_custom_version_in_url_drops_sri():
    (a,) = _only(Plugins.Plotly(version="2.30.0"), source="cdn")
    assert "plotly-2.30.0.min.js" in a["url"]
    assert a["integrity"] is None   # we only vouch for the vendored version


def test_cdn_custom_url_used_verbatim():
    (a,) = _only(Plugins.Plotly(url="https://intranet.local/plotly.js"), source="cdn")
    assert a["url"] == "https://intranet.local/plotly.js"
    assert a["integrity"] is None


def test_mathjax_output_selects_file():
    (svg,) = _only(Plugins.MathJax(output="svg"), source="cdn")
    (chtml,) = _only(Plugins.MathJax(output="chtml"), source="cdn")
    assert "tex-svg.js" in svg["url"]
    assert "tex-chtml.js" in chtml["url"]   # chtml is CDN-only


def test_mathjax_chtml_falls_back_to_svg_when_bundled():
    # Only svg is vendored; bundled chtml warns and uses svg.
    with pytest.warns(UserWarning, match="not vendored"):
        (a,) = _only(Plugins.MathJax(output="chtml"), source="bundled")
    assert a["path"].name == "tex-svg.js"


def test_highlight_style_selects_css():
    css, js = _only(Plugins.Highlight(style="github"), source="cdn")
    assert css["type"] == "css" and "styles/github.min.css" in css["url"]
    assert js["type"] == "js"


def test_highlight_unvendored_style_falls_back_when_bundled():
    with pytest.warns(UserWarning, match="not vendored"):
        css, _js = _only(Plugins.Highlight(style="monokai"), source="bundled")
    assert css["path"].name == "github-dark.min.css"


# --- Tabulator ---

def test_tabulator_cdn_emits_css_and_js_with_sri():
    css, js = _only(Plugins.Tabulator(), source="cdn")
    assert css["type"] == "css" and css["mode"] == "src"
    assert "tabulator-tables@6.3.1" in css["url"]
    assert css["integrity"].startswith("sha384-")
    assert js["type"] == "js" and "tabulator.min.js" in js["url"]
    assert js["integrity"].startswith("sha384-")


def test_tabulator_theme_auto_uses_deck_theme():
    # "auto" follows the theme's own theme.json metadata ({"dark": true|false}),
    # not its name: every dark theme gets the midnight sheet, every light theme
    # (whatever it is called) gets the light sheet.
    def _auto_css(deck_theme):
        return resolve_plugin(
            Plugins.Tabulator(), source="cdn", self_contained=True, sri=True,
            deck_theme=deck_theme)["assets"][0]

    for theme in ("dark", "docs-dark", "ink", "midnight"):
        assert "tabulator_midnight.min.css" in _auto_css(theme)["url"], theme
    for theme in ("light", "default", "docs", "academic", "light-blue",
                  "montin", "sobrio"):
        assert "css/tabulator.min.css" in _auto_css(theme)["url"], theme
    # An unknown/custom theme without theme.json defaults to the light sheet.
    assert "css/tabulator.min.css" in _auto_css("my-custom-theme")["url"]


def test_tabulator_theme_explicit_overrides_deck_theme():
    (css, _js) = resolve_plugin(
        Plugins.Tabulator(theme="light"), source="cdn", self_contained=True,
        sri=True, deck_theme="dark")["assets"]
    assert "css/tabulator.min.css" in css["url"]


def test_tabulator_bundled_inlines_css_and_js():
    css, js = _only(Plugins.Tabulator(theme="dark"), source="bundled")
    assert css["mode"] == "inline" and css["path"].name == "tabulator_midnight.min.css"
    assert js["mode"] == "inline" and js["path"].name == "tabulator.min.js"


# ---------------------------------------------------------------------------
# Deck-level plugin_source default + per-plugin override
# ---------------------------------------------------------------------------

def _render(deck):
    from montin.core.assembler import Assembler
    return Assembler(deck)._render()


def test_default_source_is_cdn():
    deck = Deck(title="X", plugins=[Plugins.Plotly()])
    deck.add_slide("S").add_text("x")
    html = _render(deck)
    assert "cdn.plot.ly/plotly-2.35.2" in html


def test_deck_plugin_source_bundled_inlines_all():
    deck = Deck(title="X", plugin_source="bundled", plugins=[Plugins.Plotly()])
    deck.add_slide("S").add_text("x")
    html = _render(deck)
    assert "cdn.plot.ly/plotly-2.35.2" not in html   # no CDN <script src>
    assert len(html) > 3_000_000   # plotly inlined


def test_per_plugin_source_overrides_deck_default():
    deck = Deck(title="X", plugin_source="bundled", plugins=[Plugins.Plotly(source="cdn")])
    deck.add_slide("S").add_text("x")
    html = _render(deck)
    assert "cdn.plot.ly/plotly-2.35.2" in html


def test_bundled_sidecar_writes_file(tmp_path):
    deck = Deck(title="X", self_contained=False, plugin_source="bundled",
                plugins=[Plugins.Plotly()])
    deck.add_slide("S").add_text("x")
    out = deck.write(tmp_path / "report")
    html = out.read_text(encoding="utf-8")
    sidecar = tmp_path / "_report_contents" / "plotly.min.js"
    assert sidecar.exists()
    assert "plotly.min.js" in html


# ---------------------------------------------------------------------------
# Vendor manifest integrity (guards packaging) + updater --check
# ---------------------------------------------------------------------------

def test_every_manifest_file_exists_on_disk():
    # Driven by the same assets/variants declarations the resolver and the
    # vendor updater use, so a new plugin or variant is covered automatically.
    import importlib.util
    from montin.utils.vendor import vendor_dir
    spec = importlib.util.spec_from_file_location(
        "update_vendor",
        pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_vendor.py",
    )
    update_vendor = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(spec and update_vendor)
    m = load_manifest()
    vdir = vendor_dir()
    checked = 0
    for lib, entry in m.items():
        if not isinstance(entry, dict):
            continue
        for _url, fname in update_vendor.iter_vendored_files(entry):
            assert (vdir / lib / fname).exists(), f"missing vendored file: {lib}/{fname}"
            assert fname in entry["sri"], f"missing sri for: {lib}/{fname}"
            checked += 1
    assert checked >= 8   # sanity: the loop actually visited the bundles


def test_every_library_ships_its_license():
    # Attribution: each vendored library keeps its LICENSE next to its code.
    from montin.utils.vendor import vendor_dir
    m = load_manifest()
    vdir = vendor_dir()
    for name, entry in m.items():
        if not isinstance(entry, dict):
            continue
        for lic in entry.get("licenses", []):
            assert (vdir / name / lic["file"]).exists(), \
                f"missing license: {name}/{lic['file']}"


def test_update_vendor_check_passes():
    import importlib.util
    from pathlib import Path
    script = Path(__file__).resolve().parent.parent / "scripts" / "update_vendor.py"
    spec = importlib.util.spec_from_file_location("update_vendor", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main(["--check"]) == 0
