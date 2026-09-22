"""
montin.cells.misc
==================
Remaining cell types: list, code, metric, mermaid, html, iframe, empty.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from montin.cells.base import Cell, CellParams

if TYPE_CHECKING:
    import jinja2


class ListCell(Cell):
    """Bullet or numbered list, with nested sub-levels."""

    def __init__(self, items: list[Any], ordered: bool, params: CellParams) -> None:
        super().__init__(params)
        self.items   = items
        self.ordered = ordered

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_list.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        from montin.io import json_safe

        return {"items": json_safe(self.items), "ordered": self.ordered}

    @classmethod
    def _from_content(cls, content, params):
        return cls(
            items=content.get("items", []),
            ordered=content.get("ordered", False),
            params=params,
        )

    def __repr__(self) -> str:
        return (
            f"ListCell(ID={self.params.cell_id!r}, items={self.items!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


class CodeCell(Cell):
    """
    Code block with syntax highlighting.
    Requires Plugins.Highlight().
    """

    def __init__(self, code: str, language: str, params: CellParams) -> None:
        super().__init__(params)
        self.code     = code
        self.language = language

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_code.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        return {"code": self.code, "language": self.language}

    @classmethod
    def _from_content(cls, content, params):
        return cls(code=content["code"], language=content["language"], params=params)

    def __repr__(self) -> str:
        return (
            f"CodeCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


class MetricCell(Cell):
    """
    KPI card: large value + label + optional delta.

    By default a positive delta is coloured green and negative red.
    Set ``lower_is_better=True`` to invert that (e.g. defect counts, latency).

    ``symbol_good``, ``symbol_bad``, ``symbol_neutral`` customise the indicator
    character — pass any string, including emoji (e.g. ``"✅"``, ``"🔴"``).
    """

    def __init__(
        self,
        value: int | float | str,
        label: str,
        delta: int | float | str | None,
        delta_label: str,
        lower_is_better: bool,
        symbol_good: str,
        symbol_bad: str,
        symbol_neutral: str,
        color_good: str,
        color_bad: str,
        color_neutral: str,
        params: CellParams,
    ) -> None:
        super().__init__(params)
        self.value       = value
        self.label       = label
        self.delta       = delta
        self.delta_label = delta_label
        self.delta_class, self.delta_symbol, self.delta_color = self._classify(
            delta, lower_is_better,
            symbol_good, symbol_bad, symbol_neutral,
            color_good, color_bad, color_neutral,
        )

    @staticmethod
    def _classify(
        delta: "int | float | str | None",
        lower_is_better: bool,
        symbol_good: str,
        symbol_bad: str,
        symbol_neutral: str,
        color_good: str,
        color_bad: str,
        color_neutral: str,
    ) -> "tuple[str | None, str | None, str | None]":
        if delta is None:
            return None, None, None
        try:
            d = float(delta)
        except (TypeError, ValueError):
            return "delta-neutral", symbol_neutral, color_neutral
        if d == 0:
            return "delta-neutral", symbol_neutral, color_neutral
        good = (d > 0) != lower_is_better
        symbol = symbol_good if d > 0 else symbol_bad
        color  = color_good  if good  else color_bad
        return ("delta-positive" if good else "delta-negative", symbol, color)

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_metric.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        # The raw symbol_*/color_*/lower_is_better inputs are consumed by
        # _classify and not retained, so we serialise the *derived* fields the
        # template actually reads and restore them directly on reload.
        from montin.io import json_safe

        return {
            "value": json_safe(self.value),
            "label": self.label,
            "delta": json_safe(self.delta),
            "delta_label": self.delta_label,
            "delta_class": self.delta_class,
            "delta_symbol": self.delta_symbol,
            "delta_color": self.delta_color,
        }

    @classmethod
    def _from_content(cls, content, params):
        obj = cls._raw_new(params)
        obj.value = content.get("value")
        obj.label = content.get("label", "")
        obj.delta = content.get("delta")
        obj.delta_label = content.get("delta_label", "")
        obj.delta_class = content.get("delta_class")
        obj.delta_symbol = content.get("delta_symbol")
        obj.delta_color = content.get("delta_color")
        return obj

    def __repr__(self) -> str:
        return (
            f"MetricCell(ID={self.params.cell_id!r}, value={self.value!r}, label={self.label!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )

class MermaidCell(Cell):
    """
    Mermaid diagram (flowchart, sequenceDiagram, architecture, etc.).
    Requires Plugins.Mermaid().
    """

    def __init__(self, diagram: str, params: CellParams) -> None:
        super().__init__(params)
        self.diagram = diagram

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_mermaid.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        return {"diagram": self.diagram}

    @classmethod
    def _from_content(cls, content, params):
        return cls(diagram=content["diagram"], params=params)

    def __repr__(self) -> str:
        return (
            f"MermaidCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )
    
class HtmlCell(Cell):
    """Raw HTML injected without escaping."""

    def __init__(self, content: str, params: CellParams) -> None:
        super().__init__(params)
        self.content = content

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_html.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        return {"content": self.content}

    @classmethod
    def _from_content(cls, content, params):
        return cls(content=content["content"], params=params)

    def __repr__(self) -> str:
        return (
            f"HtmlCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )


class IframeCell(Cell):
    """
    Embed external content via <iframe>.
    Requires an internet connection.
    The cell always clips; the embedded page scrolls itself.
    """

    def __init__(self, url: str, params: CellParams) -> None:
        super().__init__(params)
        self.url = url

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_iframe.html").render(cell=self)

    def _to_content(self, *, embed: bool = True) -> dict:
        return {"url": self.url}

    @classmethod
    def _from_content(cls, content, params):
        return cls(url=content["url"], params=params)

    def __repr__(self) -> str:
        return (
            f"IframeCell(ID={self.params.cell_id!r}"
            f" at row={self.params.row}, col={self.params.col}"
        )


class EmptyCell(Cell):
    """Empty cell — reserves grid space without rendering any content."""

    def render(self, env: "jinja2.Environment") -> str:
        return env.get_template("cell_empty.html").render(cell=self)
    
    def __repr__(self) -> str:
        return (
            f"EmptyCell(ID={self.params.cell_id!r})"
            f" at row={self.params.row}, col={self.params.col}"
        )
