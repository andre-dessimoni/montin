/* montin — sidebar.js
   ----------------------------------------------------------------------------
   The slide-list sidebar: width persistence + collapse toggle, drag-to-resize,
   collapsible sections (level-based nesting), and the search filter.

   Search state is shared with navigation (it skips hidden items while a filter
   is active), so the "is a filter active?" flag lives on T.state.searchActive;
   everything else here is module-local.

   T.state: reads/writes searchActive; reads current.
   Calls: none.
   Registers: T.initSidebar, T.initSidebarSections, T.toggleSidebar,
              T.revealActiveSidebarItem, T.filterSidebar, T.toggleSection,
              T.toggleRegexMode, T.collapseAllSections, T.expandAllSections,
              T.collapseLevel, T.expandLevel.
   ------------------------------------------------------------------------- */
(function (T) {
  "use strict";

  // -- Sidebar toggle & resize ----------------------------
  var _savedSidebarWidth = "220px";
  var _sbMinWidth = 120;
  var _sbMaxWidth = 480;

  function initSidebar() {
    var saved = localStorage.getItem("montin-sb-width");
    if (saved) {
      var w = parseInt(saved, 10);
      if (w >= _sbMinWidth && w <= _sbMaxWidth) {
        _savedSidebarWidth = w + "px";
        document.documentElement.style.setProperty("--sidebar-width", _savedSidebarWidth);
      }
    }
    // Reconcile collapse state. A remembered toggle (localStorage) wins over
    // the server-rendered default; otherwise the .sb-collapsed body class
    // (set when Sidebar(collapsed=True)) governs.
    var storedCollapsed = localStorage.getItem("montin-sb-collapsed");
    if (storedCollapsed === "1") {
      document.documentElement.style.setProperty("--sidebar-width", "0px");
      document.body.classList.add("sb-collapsed");
    } else if (storedCollapsed === "0") {
      document.body.classList.remove("sb-collapsed");
      document.documentElement.style.setProperty("--sidebar-width", _savedSidebarWidth);
    }

    var handle = document.getElementById("sidebar-resize-handle");
    if (!handle) return;

    handle.addEventListener("mousedown", function (e) {
      if (e.button !== 0) return;
      e.preventDefault();
      handle.classList.add("dragging");
      document.body.classList.add("sb-no-transition");

      function onMove(e) {
        var w = Math.max(_sbMinWidth, Math.min(_sbMaxWidth, e.clientX));
        document.documentElement.style.setProperty("--sidebar-width", w + "px");
      }

      function onUp() {
        handle.classList.remove("dragging");
        document.body.classList.remove("sb-no-transition");
        var w = getComputedStyle(document.documentElement)
          .getPropertyValue("--sidebar-width").trim();
        _savedSidebarWidth = w;
        localStorage.setItem("montin-sb-width", parseInt(w, 10));
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      }

      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  // Flags the deck area to hide its scrollbars (see layout.css) for the duration
  // of the sidebar width transition, so they don't flicker mid-animation.
  var _sbAnimTimer = null;
  function markSidebarAnimating() {
    document.body.classList.add("sb-animating");
    if (_sbAnimTimer) clearTimeout(_sbAnimTimer);
    _sbAnimTimer = setTimeout(function () {
      document.body.classList.remove("sb-animating");
      _sbAnimTimer = null;
    }, 240);   // slightly longer than the 0.2s width/left transition
  }

  function toggleSidebar() {
    var collapsed = document.body.classList.toggle("sb-collapsed");
    if (collapsed) {
      var current = getComputedStyle(document.documentElement)
        .getPropertyValue("--sidebar-width").trim();
      if (parseInt(current, 10) > 0) _savedSidebarWidth = current;
      document.documentElement.style.setProperty("--sidebar-width", "0px");
    } else {
      document.documentElement.style.setProperty("--sidebar-width", _savedSidebarWidth);
    }
    markSidebarAnimating();
    localStorage.setItem("montin-sb-collapsed", collapsed ? "1" : "0");
  }

  // -- Sidebar search & collapsible sections --------------
  var _collapsedSections = new Set();
  var _searchRe = null;
  var _regexMode = false;          // literal by default; remembered across reloads
  var _ancestors = new Map();      // item el -> [ancestor section id, ...] (outermost first)
  var _sectionGroups = new Map();  // section id -> [descendant item els]
  var _searchTimer = null;
  var SB_COLLAPSED_KEY = "montin-sb-collapsed-sections";
  var SB_REGEX_KEY = "montin-sb-regex";

  function initSidebarSections() {
    if (!document.getElementById("slide-list")) return;   // chromeless / no sidebar
    buildSectionTree();
    hideEmptyCarets();
    restoreCollapsed();
    restoreRegexMode();
    applySidebarVisibility();
    // Hide the fold toolbar when the deck has no foldable sections.
    var foldBar = document.getElementById("sidebar-fold-bar");
    if (foldBar && _sectionEls().length === 0) foldBar.style.display = "none";
  }

  // Foldable sections (those with a non-empty descendant group), with level.
  function _sectionEls() {
    var out = [];
    document.querySelectorAll('.sidebar-item[data-type="section"]').forEach(function (el) {
      var group = _sectionGroups.get(el.dataset.target);
      if (group && group.length) {
        out.push({ el: el, id: el.dataset.target, level: parseInt(el.dataset.level, 10) || 0 });
      }
    });
    return out;
  }

  function _applyFold(touched) {
    touched.forEach(syncCaret);
    persistCollapsed();
    applySidebarVisibility();
  }

  function collapseAllSections() {
    var touched = [];
    _sectionEls().forEach(function (s) {
      if (!_collapsedSections.has(s.id)) { _collapsedSections.add(s.id); touched.push(s.id); }
    });
    _applyFold(touched);
  }

  function expandAllSections() {
    var touched = Array.from(_collapsedSections);
    _collapsedSections.clear();
    _applyFold(touched);
  }

  // Progressive: fold the deepest currently-open layer of sections.
  function collapseLevel() {
    var open = _sectionEls().filter(function (s) {
      return !_collapsedSections.has(s.id) && !hasCollapsedAncestor(s.el);
    });
    if (!open.length) return;
    var maxLevel = open.reduce(function (m, s) { return Math.max(m, s.level); }, 0);
    var touched = [];
    open.forEach(function (s) {
      if (s.level === maxLevel) { _collapsedSections.add(s.id); touched.push(s.id); }
    });
    _applyFold(touched);
  }

  // Progressive: reveal the outermost currently-folded layer of sections.
  function expandLevel() {
    var folded = _sectionEls().filter(function (s) {
      return _collapsedSections.has(s.id) && !hasCollapsedAncestor(s.el);
    });
    if (!folded.length) return;
    var minLevel = folded.reduce(function (m, s) { return Math.min(m, s.level); }, Infinity);
    var touched = [];
    folded.forEach(function (s) {
      if (s.level === minLevel) { _collapsedSections.delete(s.id); touched.push(s.id); }
    });
    _applyFold(touched);
  }

  // Walk the flat item list with a level stack to derive each item's ancestor
  // sections. A section records its ancestors before pushing itself, so it is
  // never its own ancestor; popping while top.level >= level means a level-1
  // section's group spans nested level-2 subsections (level-based nesting).
  function buildSectionTree() {
    var items = Array.from(document.querySelectorAll(".sidebar-item"));
    var stack = [];  // [{id, level}]
    items.forEach(function (el) {
      var type = el.dataset.type;
      var level = parseInt(el.dataset.level, 10) || 0;
      if (type === "section") {
        while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
      }
      var anc = stack.map(function (s) { return s.id; });
      _ancestors.set(el, anc);
      anc.forEach(function (id) {
        if (!_sectionGroups.has(id)) _sectionGroups.set(id, []);
        _sectionGroups.get(id).push(el);
      });
      if (type === "section") stack.push({ id: el.dataset.target, level: level });
    });
  }

  function hideEmptyCarets() {
    document.querySelectorAll('.sidebar-item[data-type="section"]').forEach(function (el) {
      var group = _sectionGroups.get(el.dataset.target);
      var caret = el.querySelector(".sidebar-caret");
      if (caret && (!group || group.length === 0)) caret.classList.add("sidebar-caret-empty");
    });
  }

  // -- Search --------------------------------------------
  function filterSidebar(value) {
    // Debounce so content-scope search stays responsive on large decks.
    if (_searchTimer) clearTimeout(_searchTimer);
    _searchTimer = setTimeout(function () { _applyFilter(value); }, 120);
  }

  function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function _applyFilter(value) {
    var input = document.getElementById("sidebar-search");
    value = (value || "").trim();
    if (value === "") {
      T.state.searchActive = false; _searchRe = null;
      if (input) input.classList.remove("sidebar-search-error");
    } else if (_regexMode) {
      try {
        _searchRe = new RegExp(value, "i");
        T.state.searchActive = true;
        if (input) input.classList.remove("sidebar-search-error");
      } catch (e) {
        _searchRe = null; T.state.searchActive = false;   // invalid regex -> no filter
        if (input) input.classList.add("sidebar-search-error");
      }
    } else {
      // Literal mode: escape the query so specials match verbatim (always valid).
      _searchRe = new RegExp(escapeRegex(value), "i");
      T.state.searchActive = true;
      if (input) input.classList.remove("sidebar-search-error");
    }
    applySidebarVisibility();
  }

  function _syncRegexUI() {
    var btn = document.getElementById("sidebar-regex-toggle");
    var wrap = document.getElementById("sidebar-search-wrap");
    var input = document.getElementById("sidebar-search");
    if (btn) btn.classList.toggle("active", _regexMode);
    if (wrap) wrap.classList.toggle("regex-on", _regexMode);
    if (input) input.placeholder = _regexMode ? "Filter slides… (regex)" : "Filter slides…";
  }

  function toggleRegexMode() {
    _regexMode = !_regexMode;
    try { localStorage.setItem(SB_REGEX_KEY, _regexMode ? "1" : "0"); } catch (e) {}
    _syncRegexUI();
    var input = document.getElementById("sidebar-search");
    if (input) _applyFilter(input.value);   // re-run with the new interpretation
  }

  function restoreRegexMode() {
    _regexMode = localStorage.getItem(SB_REGEX_KEY) === "1";
    _syncRegexUI();
    var input = document.getElementById("sidebar-search");
    if (input && input.value) _applyFilter(input.value);   // honor a restored value
  }

  function getSearchHaystack(el) {
    var scope = document.body.dataset.sbSearchScope || "title";
    var t = el.querySelector(".sidebar-title");
    var title = t ? t.textContent : "";
    if (scope === "title_subtitle") return title + " " + (el.dataset.subtitle || "");
    if (scope === "content") {
      var slide = document.getElementById(el.dataset.target);
      return title + " " + (slide ? slide.textContent : "");
    }
    return title;
  }

  function matchesSearch(el) {
    if (!T.state.searchActive || !_searchRe) return true;
    return _searchRe.test(getSearchHaystack(el));
  }

  // -- Collapse ------------------------------------------
  function toggleSection(event, sectionId) {
    if (event) event.stopPropagation();
    if (_collapsedSections.has(sectionId)) _collapsedSections.delete(sectionId);
    else _collapsedSections.add(sectionId);
    persistCollapsed();
    syncCaret(sectionId);
    applySidebarVisibility();
  }

  function syncCaret(sectionId) {
    var sec = document.querySelector('.sidebar-item[data-target="' + cssEscape(sectionId) + '"]');
    var caret = sec && sec.querySelector(".sidebar-caret");
    if (caret) caret.classList.toggle("collapsed", _collapsedSections.has(sectionId));
  }

  function cssEscape(s) {
    return (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");
  }

  function persistCollapsed() {
    try {
      localStorage.setItem(SB_COLLAPSED_KEY, JSON.stringify(Array.from(_collapsedSections)));
    } catch (e) {}
  }

  function restoreCollapsed() {
    try {
      var raw = localStorage.getItem(SB_COLLAPSED_KEY);
      if (raw) {
        var arr = JSON.parse(raw);
        if (Array.isArray(arr)) arr.forEach(function (id) { _collapsedSections.add(id); });
      }
    } catch (e) {}
    _collapsedSections.forEach(function (id) { syncCaret(id); });
  }

  function hasCollapsedAncestor(el) {
    var anc = _ancestors.get(el) || [];
    for (var i = 0; i < anc.length; i++) if (_collapsedSections.has(anc[i])) return true;
    return false;
  }

  // Single source of truth: search overrides collapse while a query is active.
  function applySidebarVisibility() {
    var items = document.querySelectorAll(".sidebar-item");
    if (!items.length) return;
    items.forEach(function (el) {
      var visible = T.state.searchActive ? matchesSearch(el) : !hasCollapsedAncestor(el);
      el.classList.toggle("sidebar-hidden", !visible);
    });
  }

  // Auto-expand collapsed ancestors of the active item so keyboard/arrow nav
  // into a folded section reveals it. Called at the end of goTo().
  function revealActiveSidebarItem() {
    if (T.state.searchActive) return;   // search shows matches regardless of collapse
    var items = document.querySelectorAll(".sidebar-item");
    var el = items[T.state.current];
    if (!el) return;
    var anc = _ancestors.get(el) || [];
    var changed = false;
    anc.forEach(function (id) {
      if (_collapsedSections.has(id)) { _collapsedSections.delete(id); syncCaret(id); changed = true; }
    });
    if (changed) {
      persistCollapsed();
      if (!T.state.searchActive) applySidebarVisibility();
      el.scrollIntoView({ block: "nearest" });   // re-scroll now that it is shown
    }
  }

  T.initSidebar            = initSidebar;
  T.initSidebarSections    = initSidebarSections;
  T.toggleSidebar          = toggleSidebar;
  T.revealActiveSidebarItem = revealActiveSidebarItem;
  T.filterSidebar          = filterSidebar;
  T.toggleSection          = toggleSection;
  T.toggleRegexMode        = toggleRegexMode;
  T.collapseAllSections    = collapseAllSections;
  T.expandAllSections      = expandAllSections;
  T.collapseLevel          = collapseLevel;
  T.expandLevel            = expandLevel;

})(window.Montin = window.Montin || {});
