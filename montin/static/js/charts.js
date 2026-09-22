/* montin — charts.js
   ----------------------------------------------------------------------------
   Lazy rendering for the three optional renderers — Plotly, Mermaid, Tabulator.
   Each is a no-op if its library isn't bundled. Tables build the first time
   their slide is shown (so they measure while visible) and redraw on every
   (re)activation and on stage re-fit.

   T.state: none.   Calls: T.expandCell (expandPlotly delegates to it).
   Registers: T.initPlotlyCharts, T.resizePlotlyInSlide, T.renderMermaidInSlide,
              T.renderTabulatorsInSlide, T.expandPlotly.
   ------------------------------------------------------------------------- */
(function (T) {
  "use strict";

  // -- Plotly ----------------------------------------------
  // Pull text/grid colours from the active theme's CSS variables so Plotly
  // stays legible on light themes (where the old hardcoded light-grey font was
  // invisible). Axes inherit the font colour and a muted grid colour.
  function _plotlyThemeColors() {
    var cs = getComputedStyle(document.body);
    var text = (cs.getPropertyValue("--color-text") || "").trim() || "#eaeaea";
    var grid = (cs.getPropertyValue("--color-border") || "").trim() || "rgba(128,128,128,.3)";
    return { text: text, grid: grid };
  }

  function initPlotlyCharts() {
    if (typeof Plotly === "undefined") return;
    var c = _plotlyThemeColors();
    var axis = { gridcolor: c.grid, zerolinecolor: c.grid, linecolor: c.grid };
    var containers = document.querySelectorAll(".plotly-container");
    containers.forEach(function(el) {
      try {
        var figEl = el.querySelector('script[type="application/json"]');
        var raw = figEl ? figEl.textContent : el.getAttribute("data-fig");
        if (!raw) return;
        var fig = JSON.parse(raw);
        var base = fig.layout || {};
        var layout = Object.assign({}, base, {
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor:  "rgba(0,0,0,0)",
          font: Object.assign({ color: c.text }, base.font || {}, { color: c.text }),
          xaxis: Object.assign({}, axis, base.xaxis || {}),
          yaxis: Object.assign({}, axis, base.yaxis || {}),
          margin: { t: 30, r: 10, b: 40, l: 50 },
          autosize: true,
        });
        Plotly.newPlot(el, fig.data || [], layout, { responsive: true });
      } catch(e) {
        el.textContent = "Error rendering chart: " + e.message;
      }
    });
  }

  function renderMermaidInSlide(slideEl) {
    if (typeof mermaid === "undefined") return;
    var unprocessed = Array.from(slideEl.querySelectorAll("pre.mermaid")).filter(function(el) {
      return !el.getAttribute("data-processed");
    });
    if (unprocessed.length > 0) {
      mermaid.run({ nodes: unprocessed });
    }
  }

  function resizePlotlyInSlide(slideEl) {
    if (typeof Plotly === "undefined") return;
    var containers = slideEl.querySelectorAll(".plotly-container");
    containers.forEach(function(el) {
      if (el._fullLayout) Plotly.relayout(el, { autosize: true });
    });
  }

  // -- Tabulator -------------------------------------------
  // Build each interactive table the first time its slide is shown (so it is
  // measured while visible, not inside a display:none slide), then redraw on
  // every (re)activation and on resize to track the fixed-size stage scale.

  var _tabulatorFormatsReady = false;
  function ensureTabulatorFormats() {
    if (_tabulatorFormatsReady || typeof Tabulator === "undefined") return;
    _tabulatorFormatsReady = true;
    Tabulator.extendModule("format", "formatters", {
      // Continuous row numbers across paginated pages.
      // getPosition(true) returns the row's 1-based index in the full filtered
      // set (post-filter, post-sort, before pagination slicing), so the counter
      // never resets when the reader flips to a new page.
      rownumGlobal: function(cell) {
        try {
          var pos = cell.getRow().getPosition(true);
          return pos !== false ? pos : "";
        } catch(e) { return ""; }
      }
    });
  }

  function buildTabulator(el) {
    if (el._tbBuilt || typeof Tabulator === "undefined") return;
    ensureTabulatorFormats();
    var cfgEl = document.getElementById(el.id + "-cfg");
    if (!cfgEl) return;
    el._tbBuilt = true;
    try {
      var table = new Tabulator(el, JSON.parse(cfgEl.textContent));
      el._tabulator = table;
      var card = el.closest(".cell");
      if (card) {
        card.querySelectorAll("[data-tab-download]").forEach(function(b) {
          b.addEventListener("click", function() {
            var f = b.getAttribute("data-tab-download");
            table.download(f, "data." + f);
          });
        });
      }
    } catch (e) {
      el.textContent = "Error rendering table: " + e.message;
    }
  }

  function renderTabulatorsInSlide(slideEl) {
    if (typeof Tabulator === "undefined") return;
    slideEl.querySelectorAll(".montin-tabulator").forEach(function(el) {
      buildTabulator(el);
      var t = el._tabulator;
      // Defer the redraw so it runs after the stage transform / layout settles.
      if (t) requestAnimationFrame(function() { try { t.redraw(true); } catch (e) {} });
    });
  }

  function expandPlotly(btn) {
    T.expandCell(btn);
  }

  // -- Print support ---------------------------------------
  // The live widgets don't print well: Tabulator is a virtual-DOM table (only
  // visible rows in the DOM, internal scroll) and its native printAsHtml hook
  // conflicts across multiple tables; Plotly is a fixed-size on-screen SVG whose
  // legend gets clipped. So on `beforeprint` we generate a print-only static
  // fallback next to each widget — a plain <table> from the row data, and a
  // scalable SVG snapshot of each chart — and the print CSS hides the live
  // widget and shows the fallback. Everything here is synchronous so it is in
  // place before the browser snapshots the page.

  function _flatColumns(defs) {
    var out = [];
    (defs || []).forEach(function (c) {
      if (c.columns && c.columns.length) out = out.concat(_flatColumns(c.columns));
      else out.push(c);
    });
    return out;
  }

  // Build/refresh a static <table> from a Tabulator's *config* (the inlined
  // {id}-cfg JSON), not the live instance: Tabulator builds asynchronously, so a
  // freshly-built widget's getData() is still empty during the synchronous
  // beforeprint pass — only the already-rendered slide would have data. The
  // config carries every column and every row up front, so this works for all
  // slides (visited or not) and prints the full data set. Hidden on screen.
  function buildPrintTable(el) {
    var cfgEl = document.getElementById(el.id + "-cfg");
    if (!cfgEl) return;
    var cfg;
    try { cfg = JSON.parse(cfgEl.textContent); } catch (e) { return; }
    var data = cfg.data || [];
    var cols = _flatColumns(cfg.columns);
    if (!cols.length) {                 // autoColumns / multi-sheet -> derive
      if (!data.length) return;
      cols = Object.keys(data[0]).map(function (k) { return { title: k, field: k }; });
    }

    var next = el.nextElementSibling;
    if (next && next.classList.contains("hs-print-table")) next.remove();

    var tbl = document.createElement("table");
    tbl.className = "hs-table hs-print-table";
    var thead = document.createElement("thead");
    var htr = document.createElement("tr");
    cols.forEach(function (c) {
      var th = document.createElement("th");
      th.textContent = c.title || c.field || "";
      htr.appendChild(th);
    });
    thead.appendChild(htr);
    tbl.appendChild(thead);

    var tbody = document.createElement("tbody");
    data.forEach(function (row, i) {
      var tr = document.createElement("tr");
      cols.forEach(function (c) {
        var td = document.createElement("td");
        var v = c.field ? row[c.field] : (i + 1);   // fieldless col == row number
        td.textContent = (v === undefined || v === null) ? "" : v;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    el.parentNode.insertBefore(tbl, el.nextSibling);
  }

  // Build/refresh a scalable inline-SVG snapshot of a Plotly chart (includes the
  // legend) next to the live container; hidden on screen, shown in print.
  function buildPrintChart(el) {
    if (!(window.Plotly && Plotly.Snapshot && Plotly.Snapshot.toSVG)) return;
    if (!el._fullLayout) return;        // never rendered (unvisited) -> skip
    var svg;
    try { svg = Plotly.Snapshot.toSVG(el); } catch (e) { return; }
    if (!svg) return;
    // toSVG returns a string in most builds, but coerce a node just in case.
    if (typeof svg !== "string") {
      svg = svg.outerHTML || new XMLSerializer().serializeToString(svg);
    }

    var next = el.nextElementSibling;
    if (next && next.classList.contains("plotly-print")) next.remove();

    var wrap = document.createElement("div");
    wrap.className = "plotly-print";
    wrap.innerHTML = svg;
    // The exported SVG carries fixed width/height; convert to a viewBox so it
    // scales to the print cell instead of overflowing it.
    var s = wrap.querySelector("svg");
    if (s) {
      var w = parseFloat(s.getAttribute("width"));
      var h = parseFloat(s.getAttribute("height"));
      if (w && h && !s.getAttribute("viewBox")) s.setAttribute("viewBox", "0 0 " + w + " " + h);
      s.removeAttribute("width");
      s.removeAttribute("height");
      s.setAttribute("preserveAspectRatio", "xMidYMid meet");
    }
    el.parentNode.insertBefore(wrap, el.nextSibling);
  }

  function prepareForPrint() {
    // Static tables are built from the inlined config, so they work even if the
    // live Tabulator never rendered (unvisited slide / library not yet ready).
    document.querySelectorAll(".montin-tabulator").forEach(buildPrintTable);
    document.querySelectorAll(".plotly-container").forEach(buildPrintChart);
  }

  function initChartPrinting() {
    window.addEventListener("beforeprint", prepareForPrint);
  }

  T.initPlotlyCharts        = initPlotlyCharts;
  T.resizePlotlyInSlide     = resizePlotlyInSlide;
  T.renderMermaidInSlide    = renderMermaidInSlide;
  T.renderTabulatorsInSlide = renderTabulatorsInSlide;
  T.expandPlotly            = expandPlotly;
  T.initChartPrinting       = initChartPrinting;

})(window.Montin = window.Montin || {});
