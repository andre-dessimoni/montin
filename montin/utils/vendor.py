"""
montin.utils.vendor
====================
Resolves a declared :class:`~montin.core.plugins.Plugin` into the concrete
``<script>`` / ``<link>`` assets the template should emit, honouring the chosen
loading mode (CDN vs bundled) and the vendor ``manifest.json``.

The resolution is fully data-driven: each manifest entry declares its ``assets``
(with ``{version}`` / variant placeholders), its ``variants`` (the values
vendored for bundled mode, plus an optional montin-value -> upstream-file-name
``map``), and per-file ``sri`` hashes. Adding a plugin means adding a
:class:`Plugin` subclass and a manifest entry — no code here changes.

The :class:`~montin.core.assembler.Assembler` owns all file IO (reading the
inlined text, copying sidecar files); this module is pure given the manifest, so
it is straightforward to unit-test.

An *asset* is a plain dict the template renders directly:

    {"type": "js"|"css", "mode": "inline"|"src"|"copy",
     "path": Path,            # inline / copy: the vendored file on disk
     "filename": str,         # copy: target name next to the report
     "url": str,              # src: where the browser loads it from
     "integrity": str|None}   # src: SRI hash when we can vouch for the URL
"""

from __future__ import annotations

import json
import warnings
from functools import lru_cache
from pathlib import Path

from montin.utils.resource_loader import get_static


def vendor_dir() -> Path:
    """Folder holding the vendored libraries and their manifest."""
    return get_static("vendor")


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    """Parsed ``manifest.json`` (cached)."""
    return json.loads((vendor_dir() / "manifest.json").read_text(encoding="utf-8"))


def _vouchable(plugin, entry_version: str) -> bool:
    """Whether an SRI hash is valid for this plugin's resolved CDN URL.

    Only when the URL is the canonical one we hashed: no custom ``url`` and the
    default (vendored) version.
    """
    return plugin.url is None and (plugin.version in (None, entry_version))


def _resolve_variants(name: str, entry: dict, source: str, vars: dict) -> dict:
    """Validate / map the plugin-supplied variant values against the manifest.

    Bundled mode only ships the values in ``variants[var]["values"]`` — anything
    else warns and falls back to the default. An optional ``map`` translates the
    montin-facing value into the upstream file base name (e.g. Tabulator's
    ``dark`` -> ``tabulator_midnight``).
    """
    resolved = dict(vars)
    for var, spec in entry.get("variants", {}).items():
        value = resolved.get(var, spec["default"])
        mapping = spec.get("map")
        if source == "bundled" and value not in spec["values"]:
            warnings.warn(
                f"Plugin {name!r}: {var}={value!r} is not vendored for bundled "
                f"mode; using {spec['default']!r}. Vendored: {spec['values']}. "
                f"(Use source='cdn' for {value!r}.)",
                stacklevel=3,
            )
            value = spec["default"]
        if mapping is not None:
            value = mapping.get(value) or mapping[spec["default"]]
        resolved[var] = value
    return resolved


def resolve_plugin(plugin, *, source: str, self_contained: bool, sri: bool,
                   deck_theme: str | None = None) -> dict:
    """Resolve one plugin to ``{"name", "assets", "options"}``.

    Args:
        plugin: the declared :class:`Plugin` instance.
        source: the effective ``"cdn"`` or ``"bundled"`` (deck default / force
            already applied by the caller).
        self_contained: whether bundled assets are inlined (vs copied as sidecars).
        sri: whether to attach Subresource-Integrity hashes to CDN assets.
        deck_theme: the deck's theme name, forwarded to the plugin's
            ``template_vars`` (e.g. Tabulator resolves ``theme="auto"`` with it).
    """
    name = plugin.name
    entry = load_manifest()[name]
    version = plugin.version or entry["version"]

    if source == "bundled" and plugin.version not in (None, entry["version"]):
        warnings.warn(
            f"Plugin {name!r}: bundled mode ships version {entry['version']}, "
            f"ignoring version={plugin.version!r}. Use source='cdn' for a custom "
            f"version.",
            stacklevel=2,
        )

    vars = _resolve_variants(name, entry, source, plugin.template_vars(deck_theme))
    vouch = sri and _vouchable(plugin, entry["version"])
    lib_dir = vendor_dir() / name   # each library lives in its own subfolder

    assets: list[dict] = []
    for spec in entry["assets"]:
        filename = spec["file"].format(**vars)
        if source == "cdn":
            # A custom plugin.url replaces the library's script URL only; any
            # stylesheet still loads from its default CDN.
            if spec["type"] == "js" and plugin.url:
                url = plugin.url
            else:
                url = spec["cdn"].format(version=version, **vars)
            integrity = entry["sri"].get(filename) if vouch else None
            assets.append({"type": spec["type"], "mode": "src",
                           "url": url, "integrity": integrity})
        elif self_contained:
            assets.append({"type": spec["type"], "mode": "inline",
                           "path": lib_dir / filename})
        else:
            assets.append({"type": spec["type"], "mode": "copy",
                           "path": lib_dir / filename, "filename": filename})

    return {"name": name, "assets": assets, "options": plugin.init_options()}
