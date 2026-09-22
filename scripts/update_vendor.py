#!/usr/bin/env python
"""
update_vendor.py — refresh the bundled (vendored) plugin libraries.

montin can embed Plotly / Mermaid / highlight.js / MathJax directly into a
report so it works with no network at all (``source="bundled"``). Those minified
files live in ``montin/static/vendor/`` and are described by ``manifest.json``.

This dev-only script reads the version pins in ``manifest.json``, downloads each
library from its CDN, writes the files into the vendor folder, computes the
Subresource-Integrity (sha384) hashes, writes them back into the manifest, prunes
any orphaned ``.js`` / ``.css`` no longer referenced, and appends a dated line to
``UPDATE_LOG.md``.

Filenames are intentionally version-free (the version lives in the manifest and
the log), so a version bump overwrites the same file instead of leaving the old
one behind to rot in git history and the wheel.

Usage:
    python scripts/update_vendor.py            # download + refresh hashes
    python scripts/update_vendor.py --check    # verify manifest <-> disk only

To bump a version, edit the ``version`` (or ``vendored_styles``) in
``manifest.json`` and re-run without ``--check``.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "montin" / "static" / "vendor"
MANIFEST = VENDOR_DIR / "manifest.json"
UPDATE_LOG = VENDOR_DIR / "UPDATE_LOG.md"

_UA = {"User-Agent": "montin-vendor-updater/1.0 (+https://github.com/andre-dessimoni/montin)"}


def _sri(data: bytes) -> str:
    """Subresource-Integrity string (``sha384-<base64>``) for ``data``."""
    digest = hashlib.sha384(data).digest()
    return "sha384-" + base64.b64encode(digest).decode("ascii")


def _download(url: str) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (trusted CDN URLs)
        return resp.read()


def iter_vendored_files(entry: dict):
    """Yield ``(url, filename)`` for every vendored file of one library entry.

    Driven entirely by the entry's ``assets`` + ``variants`` declarations, so a
    new plugin (or a new vendored variant) needs no change here. An asset with a
    ``variant`` expands to one file per vendored value, mapped through the
    variant's optional ``map`` to the upstream file base name.
    """
    version = entry["version"]
    for asset in entry["assets"]:
        var = asset.get("variant")
        if var is None:
            substitutions = [{}]
        else:
            spec = entry["variants"][var]
            mapping = spec.get("map") or {}
            substitutions = [{var: mapping.get(v, v)} for v in spec["values"]]
        for subs in substitutions:
            yield (asset["cdn"].format(version=version, **subs),
                   asset["file"].format(**subs))


def _code_jobs(manifest: dict) -> list[tuple[str, Path, list[str]]]:
    """Flatten the manifest into ``(url, dest, sri_path)`` library-file jobs.

    ``dest`` is the file's path inside its per-library subfolder (e.g.
    ``vendor/plotly/plotly.min.js``); the URL carries the pinned version.
    ``sri_path`` is the manifest key path (``[name, "sri", filename]``) where
    the hash is stored.
    """
    jobs: list[tuple[str, Path, list[str]]] = []
    for name, entry in manifest.items():
        if not isinstance(entry, dict):
            continue
        for url, fname in iter_vendored_files(entry):
            jobs.append((url, VENDOR_DIR / name / fname, [name, "sri", fname]))
    return jobs


def _license_jobs(manifest: dict) -> list[tuple[str, Path]]:
    """``(url, dest)`` jobs for each library's LICENSE / NOTICE file(s)."""
    jobs: list[tuple[str, Path]] = []
    for name, entry in manifest.items():
        if not isinstance(entry, dict):
            continue
        for lic in entry.get("licenses", []):
            url = lic["url"].format(version=entry["version"])
            jobs.append((url, VENDOR_DIR / name / lic["file"]))
    return jobs


def _set_nested(manifest: dict, path: list[str], value: str) -> None:
    node = manifest
    for key in path[:-1]:
        node = node.setdefault(key, {})
    node[path[-1]] = value


def _get_nested(manifest: dict, path: list[str]):
    node: object = manifest
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _vendored_code_files() -> list[Path]:
    """Every ``.js`` / ``.css`` currently on disk under the vendor folder."""
    return [f for f in VENDOR_DIR.rglob("*") if f.suffix in (".js", ".css")]


def _prune_orphans(wanted: set[Path]) -> list[str]:
    """Delete vendored ``.js`` / ``.css`` files no longer referenced by a job.

    Called after the wanted files are (re)written, so a version bump, a removed
    style/output, or the old flat layout never leaves a stale file behind. Also
    removes any directory left empty afterwards (license files are kept).
    """
    removed: list[str] = []
    for f in _vendored_code_files():
        if f not in wanted:
            f.unlink()
            removed.append(str(f.relative_to(VENDOR_DIR)))
    for d in sorted(VENDOR_DIR.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    return removed


def check(manifest: dict) -> int:
    """Verify each vendored file exists, its bytes match the recorded SRI, and
    each library's licence file is present — all offline.

    Catches a forgotten ``update_vendor.py`` run (missing/stale file), a
    hand-edited manifest hash, a missing licence, or a leftover orphan.
    """
    problems: list[str] = []
    code = _code_jobs(manifest)
    wanted = {dest for _u, dest, _s in code}
    for _url, dest, sri_path in code:
        rel = dest.relative_to(VENDOR_DIR)
        recorded = _get_nested(manifest, sri_path)
        if not dest.exists():
            problems.append(f"file missing: {rel}")
        elif not recorded:
            problems.append(f"sri missing: {'/'.join(sri_path)}")
        elif _sri(dest.read_bytes()) != recorded:
            problems.append(f"sri mismatch (stale file or edited hash): {rel}")
    for _url, dest in _license_jobs(manifest):
        if not dest.exists():
            problems.append(f"license missing: {dest.relative_to(VENDOR_DIR)}")
    for f in _vendored_code_files():
        if f not in wanted:
            problems.append(f"orphan file: {f.relative_to(VENDOR_DIR)}")
    if problems:
        print("vendor check FAILED:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"vendor check OK ({len(code)} files, hashes match; licences present).")
    return 0


def update(manifest: dict) -> int:
    code = _code_jobs(manifest)
    versions: dict[str, str] = {}
    for url, dest, sri_path in code:
        print(f"  v {dest.relative_to(VENDOR_DIR)}  <-  {url}")
        data = _download(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        _set_nested(manifest, sri_path, _sri(data))
        versions[sri_path[0]] = manifest[sri_path[0]]["version"]

    for url, dest in _license_jobs(manifest):
        print(f"  L {dest.relative_to(VENDOR_DIR)}  <-  {url}")
        data = _download(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

    removed = _prune_orphans({dest for _u, dest, _s in code})

    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"- **{stamp}** -- " + ", ".join(
        f"{name} {ver}" for name, ver in sorted(versions.items())
    )
    if not UPDATE_LOG.exists():
        UPDATE_LOG.write_text(
            "# Vendored library update log\n\n"
            "Each entry records a run of `scripts/update_vendor.py` and the "
            "library versions it fetched.\n\n",
            encoding="utf-8",
        )
    with UPDATE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    print(f"\nUpdated {len(code)} files. Logged: {line}")
    if removed:
        print("Pruned orphans: " + ", ".join(removed))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify manifest <-> disk without downloading")
    args = ap.parse_args(argv)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return check(manifest) if args.check else update(manifest)


if __name__ == "__main__":
    sys.exit(main())
