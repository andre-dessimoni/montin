"""montin.cells.tabulator — TabulatorCell (interactive tables via Tabulator.js)"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any, Literal

from montin.cells.base import Cell, CellParams
from montin.utils.tabular import normalize_table_data

if TYPE_CHECKING:
    import jinja2
    import pandas as pd

_NON_FIELD = re.compile(r"[^0-9a-zA-Z_]+")


def _safe_fields(headers: list[str]) -> list[str]:
    """Turn headers into unique Tabulator field keys (``[A-Za-z0-9_]``).

    Tabulator treats ``.`` in a field as nested-data access, so headers are
    sanitised to safe keys while the original text is kept as the column title.
    """
    fields: list[str] = []
    seen: set[str] = set()
    for i, h in enumerate(headers):
        base = _NON_FIELD.sub("_", str(h)).strip("_") or f"col{i}"
        if base[0].isdigit():
            base = f"c_{base}"
        field, n = base, 2
        while field in seen:
            field, n = f"{base}_{n}", n + 1
        seen.add(field)
        fields.append(field)
    return fields


def _safe_json(obj: Any) -> str:
    """Embed-safe JSON for a ``<script type="application/json">`` block.

    ``<`` / ``>`` are escaped to their ``\\uXXXX`` form so the JSON can never
    contain ``</script>`` (or ``<!--``) and close the tag early; the result is
    still valid JSON, so ``JSON.parse`` restores the original text.
    """
    return (
        json.dumps(obj, default=str)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


class TabulatorCell(Cell):
    """Interactive table cell rendered via Tabulator.js.

    Do not instantiate directly — use :meth:`montin.core.slide.Slide.add_tabulator`,
    which documents every option (this class takes the same keyword arguments).
    Requires ``Plugins.Tabulator()`` on the deck.
    """

    def __init__(
        self,
        data: "dict[str, Any] | list[list[Any]] | pd.DataFrame | str | None",
        params: CellParams,
        *,
        sheets: "dict[str, Any] | None" = None,
        columns: list[dict] | None = None,
        options: dict | None = None,
        layout: str = "fitColumns",
        responsive: bool = False,
        pagination: int | None = None,
        selectable: bool | int = False,
        group_by: str | list[str] | None = None,
        header_filter: bool = False,
        frozen_columns: list[str] | None = None,
        frozen_rows: int | None = None,
        movable_columns: bool = True,
        header_sort: bool | None = None,
        row_numbers: bool = False,
        spreadsheet_mode: bool = False,
        persistence: bool = False,
        download: list[str] | None = None,
        height: str | int | None = None,
        index: bool = False,
        separator: Literal["auto", ",", "\t"] = "auto",
        tabulator_config: dict | None = None,
    ) -> None:
        super().__init__(params)

        self.download = [d.lower() for d in (download or [])
                         if d.lower() in ("csv", "json")]
        self._options = options or {}

        # ---- Multi-sheet path (sheets=) ------------------------------------
        if sheets is not None:
            if data is not None:
                raise ValueError("pass either 'data' or 'sheets', not both")
            sheet_list = []
            for i, (sheet_name, sheet_data) in enumerate(sheets.items()):
                hdrs, srows = normalize_table_data(
                    sheet_data, separator=separator, index=index)
                raw_rows = [[str(h) for h in hdrs]] + srows
                slug = (re.sub(r"[^a-z0-9]+", "-", sheet_name.lower()).strip("-")
                        or f"s{i}")
                sheet_list.append({
                    "title": sheet_name,
                    "key": slug,
                    "rows": len(raw_rows) + 2,
                    "columns": len(hdrs) + 2,
                    "data": raw_rows,
                })
            config: dict[str, Any] = {
                "height": height or "100%",
                "spreadsheet": True,
                "spreadsheetSheets": sheet_list,
                "spreadsheetSheetTabs": True,
                "spreadsheetColumnDefinition": {
                    "editor": "input" if spreadsheet_mode else False},
                "headerSort": False,
                "movableColumns": False,
            }
            if spreadsheet_mode:
                config["headerSort"] = header_sort if header_sort is not None else False
                config["selectableRange"] = 1
                config["selectableRangeColumns"] = True
                config["selectableRangeRows"] = True
                config["selectableRangeClearCells"] = True
                config["clipboard"] = True
                config["clipboardCopyStyled"] = False
                config["clipboardCopyConfig"] = {
                    "rowHeaders": False, "columnHeaders": False}
                config["clipboardCopyRowRange"] = "range"
                config["clipboardPasteParser"] = "range"
                config["clipboardPasteAction"] = "range"
            elif header_sort is not None:
                config["headerSort"] = header_sort
            if row_numbers:
                config["rowHeader"] = {
                    "field": "_id",
                    "hozAlign": "center",
                    "headerSort": False,
                    "frozen": True,
                    "formatter": "rownumGlobal",
                }
            if tabulator_config is not None:
                config.update(tabulator_config)
            self.headers = []
            self._persistence = False
            self._config = config
            return

        # ---- Single-sheet path (data=) ------------------------------------
        if data is None:
            raise ValueError("pass either 'data' (single table) or 'sheets' (multi-sheet)")

        headers, rows = normalize_table_data(data, separator=separator, index=index)
        self.headers = headers
        fields = _safe_fields(headers)
        title_to_field = {str(h): f for h, f in zip(headers, fields)}

        self._persistence = persistence

        rows_data = [dict(zip(fields, r)) for r in rows]

        # Auto columns, then merge user column defs by field (or by title).
        cols = [{"title": str(h), "field": f} for h, f in zip(headers, fields)]
        by_field = {c["field"]: c for c in cols}
        for raw in (columns or []):
            spec = dict(raw)
            key = spec.get("field") or title_to_field.get(spec.get("title", ""))
            if key in by_field:
                by_field[key].update({k: v for k, v in spec.items() if k != "field"})
            else:                          # extra column not present in the data
                cols.append(spec)
                if spec.get("field"):
                    by_field[spec["field"]] = spec

        if header_filter:
            for c in cols:
                c.setdefault("headerFilter", "input")
        for name in (frozen_columns or []):
            field = name if name in by_field else title_to_field.get(name)
            if field in by_field:
                by_field[field]["frozen"] = True

        config: dict[str, Any] = {
            "data": rows_data,
            "layout": layout,
            "movableColumns": movable_columns,
            "renderHorizontal": "virtual",
        }
        if cols:
            config["columns"] = cols
        else:
            config["autoColumns"] = True
        if responsive:
            config["responsiveLayout"] = "collapse"
        if pagination:
            config["pagination"] = True
            config["paginationSize"] = int(pagination)
            config["paginationCounter"] = "rows"
            config["paginationSizeSelector"] = True
            config["height"] = "100%"
        if height is not None:
            config["height"] = height
        if selectable:
            config["selectableRows"] = selectable
            config["selectableRange"] = True
            config["selectableRangeColumns"] = True
            config["selectableRangeRows"] = True
        if header_sort is not None:
            config["headerSort"] = header_sort
        if spreadsheet_mode:
            if header_sort is None:
                config["headerSort"] = False
            config["selectableRange"] = 1
            config["selectableRangeColumns"] = True
            config["selectableRangeRows"] = True
            config["selectableRangeClearCells"] = True
            config["clipboard"] = True
            config["clipboardCopyStyled"] = False
            config["clipboardCopyConfig"] = {
                "rowHeaders": False,
                "columnHeaders": False,
            }
            config["clipboardCopyRowRange"] = "range"
            config["clipboardPasteParser"] = "range"
            config["clipboardPasteAction"] = "range"
            config["columnDefaults"] = {
                "headerSort": False,
                "resizable": "header",
            }
        if row_numbers:
            num_digits = len(str(len(rows))) if rows else 1
            rn_width = max(36, num_digits * 10 + 16)
            config["rowHeader"] = {
                "resizable": False,
                "frozen": True,
                "width": rn_width,
                "minWidth": rn_width,
                "hozAlign": "center",
                "formatter": "rownumGlobal",
                "cssClass": "range-header-col",
            }
        if group_by:
            config["groupBy"] = _map_fields(group_by, title_to_field)
        if frozen_rows:
            config["frozenRows"] = int(frozen_rows)
        if tabulator_config is not None:
            config.update(tabulator_config)

        self._config = config

    # ------------------------------------------------------------------

    def _dom_id(self) -> str:
        """DOM id for the table element, unique within the deck.

        Derived from the slide id + cell id, since the cell id alone resets per
        slide (so every slide's first table would otherwise share one id).
        """
        sl = self._slide
        raw = f"{sl.slide_id}-{self.params.cell_id}" if sl is not None else str(self.params.cell_id)
        return "tab-" + (_NON_FIELD.sub("-", raw).strip("-") or "cell")

    def _persistence_id(self) -> str:
        """Stable id so remembered state doesn't collide across reports/slides.

        A short hash of the column structure is folded in so that changing the
        table's columns yields a new id — otherwise Tabulator would restore a
        saved layout that no longer matches the data and render it broken.
        """
        parts: list[str] = []
        sl = self._slide
        if sl is not None:
            parts.append(str(getattr(sl.parent, "title", "")))
            parts.append(str(sl.slide_id))
        parts.append(str(self.params.cell_id))
        struct = json.dumps(self._config.get("columns", "auto"), sort_keys=True, default=str)
        parts.append(hashlib.sha1(struct.encode("utf-8")).hexdigest()[:8])
        return "/".join(p for p in parts if p)

    def _build_config(self) -> dict:
        config = dict(self._config)
        if self._persistence:
            config["persistence"] = True
            config["persistenceID"] = self._persistence_id()
        config.update(self._options)   # the escape hatch always wins
        return config

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_tabulator.html").render(
            cell=self, dom_id=self._dom_id(),
            config_json=_safe_json(self._build_config()))

    def _to_content(self, *, embed: bool = True) -> dict:
        # The full Tabulator config (table data + UI options) is already a
        # JSON-native tree; restore it verbatim rather than re-deriving it from
        # the original constructor kwargs.
        from montin.io import json_safe

        return {
            "config": json_safe(self._config),
            "headers": list(self.headers),
            "download": list(self.download),
            "options": json_safe(self._options),
            "persistence": self._persistence,
        }

    @classmethod
    def _from_content(cls, content, params):
        obj = cls._raw_new(params)
        obj._config = content.get("config", {})
        obj.headers = content.get("headers", [])
        obj.download = content.get("download", [])
        obj._options = content.get("options", {})
        obj._persistence = content.get("persistence", False)
        return obj

    def __repr__(self) -> str:
        return (
            f"TabulatorCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


def _map_fields(value: "str | list[str]", title_to_field: dict[str, str]):
    """Map a header name (or list of them) to its sanitised Tabulator field."""
    if isinstance(value, list):
        return [title_to_field.get(v, v) for v in value]
    return title_to_field.get(value, value)
