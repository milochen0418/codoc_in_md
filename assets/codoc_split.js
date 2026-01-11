(function () {
  // CoDoc split resize + scroll sync.
  // Loaded as a static asset so it reliably executes in Reflex/React.

  const INIT_KEY = '__codocSplitInit_v2';
  if (window[INIT_KEY]) return;
  window[INIT_KEY] = true;

  const STORAGE_KEY = 'codoc_split_left_pct_v1';
  const MIN_PCT = 20;
  const MAX_PCT = 80;

  const state = {
    dragging: false,
    pointerId: null,
    container: null,
    divider: null,
    editorScrollEl: null,
    editor: null,
    previewScrollEl: null,
    syncing: false,
    pendingPreviewSync: false,
    lastHeadingText: null,
    editorH2Cache: { versionId: null, lines: [] },
    retryTimer: null,
    retryCount: 0,
  };

  function clamp(n, min, max) {
    return Math.min(max, Math.max(min, n));
  }

  function normalizeText(s) {
    return String(s || '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function getLocked(container) {
    if (!container) return false;
    const viaDataset = container.dataset ? container.dataset.locked : null; // data-locked
    const viaAttr = container.getAttribute('data-locked') || container.getAttribute('data_locked');
    const raw = viaDataset != null ? viaDataset : viaAttr;
    return raw === true || raw === 'true';
  }

  function pickVisibleEditorScrollEl(editorPane) {
    if (!editorPane) return null;
    const candidates = Array.from(
      editorPane.querySelectorAll('.monaco-editor .monaco-scrollable-element')
    );
    const visible = candidates
      .map((el) => {
        const r = el.getBoundingClientRect();
        const area = Math.max(0, r.width) * Math.max(0, r.height);
        return { el, area };
      })
      .filter((x) => x.area > 1000);

    visible.sort((a, b) => b.area - a.area);
    return (visible[0] && visible[0].el) || candidates[0] || null;
  }

  function findElements() {
    const container = document.getElementById('codoc-split');
    if (!container) return false;

    const divider = document.getElementById('split-divider');
    const editorPane = document.getElementById('editor-pane');
    const previewPane = document.getElementById('preview-pane');
    if (!divider || !editorPane || !previewPane) return false;

    const editorScrollEl = pickVisibleEditorScrollEl(editorPane);
    if (!editorScrollEl) return false;

    // Prefer Monaco's editor API for accurate scroll metrics.
    let editorInstance = null;
    try {
      const monaco = window.monaco;
      if (monaco && monaco.editor && typeof monaco.editor.getEditors === 'function') {
        const editors = monaco.editor.getEditors();
        editorInstance =
          editors.find((ed) => {
            const dom = ed && typeof ed.getDomNode === 'function' ? ed.getDomNode() : null;
            return dom && editorPane.contains(dom);
          }) ||
          editors[0] ||
          null;
      }
    } catch (_) {
      editorInstance = null;
    }

    state.container = container;
    state.divider = divider;
    state.editorScrollEl = editorScrollEl;
    state.editor = editorInstance;
    state.previewScrollEl = previewPane;
    return true;
  }

  function applySavedSplit(container) {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (!saved) return;
      const pct = clamp(parseFloat(saved), MIN_PCT, MAX_PCT);
      if (!Number.isFinite(pct)) return;
      container.style.setProperty('--codoc-split-left', pct + '%');
    } catch (_) {
      // ignore
    }
  }

  function setSplitPct(container, pct) {
    const clamped = clamp(pct, MIN_PCT, MAX_PCT);
    container.style.setProperty('--codoc-split-left', clamped + '%');
    try {
      window.localStorage.setItem(STORAGE_KEY, String(clamped));
    } catch (_) {
      // ignore
    }
    // Monaco needs a resize signal to re-layout smoothly.
    window.dispatchEvent(new Event('resize'));
  }

  function bindDividerOnce() {
    if (!state.divider || state.divider.__codocBound) return;
    state.divider.__codocBound = true;

    const startDrag = (e) => {
      // Clicking the lock button should not start dragging.
      if (e.target && e.target.closest && e.target.closest('button')) return;
      if (!state.container) return;
      state.dragging = true;
      state.pointerId = e.pointerId ?? null;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      try {
        if (state.pointerId != null && state.divider.setPointerCapture) {
          state.divider.setPointerCapture(state.pointerId);
        }
      } catch (_) {
        // ignore
      }
      e.preventDefault();
    };

    const moveDrag = (e) => {
      if (!state.dragging || !state.container) return;
      if (state.pointerId != null && e.pointerId != null && e.pointerId !== state.pointerId) return;

      const rect = state.container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(state.container, pct);
    };

    const endDrag = (e) => {
      if (!state.dragging) return;
      if (state.pointerId != null && e.pointerId != null && e.pointerId !== state.pointerId) return;
      state.dragging = false;
      state.pointerId = null;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    // Prefer Pointer Events (covers mouse/touch/pen)
    state.divider.addEventListener('pointerdown', startDrag);
    state.divider.addEventListener('pointermove', moveDrag);
    state.divider.addEventListener('pointerup', endDrag);
    state.divider.addEventListener('pointercancel', endDrag);

    // Fallback for older browsers
    state.divider.addEventListener('mousedown', function (e) {
      // Only run if pointer events are not firing.
      if (state.dragging) return;
      if (e.target && e.target.closest && e.target.closest('button')) return;
      if (!state.container) return;
      state.dragging = true;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      e.preventDefault();
    });

    window.addEventListener('mousemove', function (e) {
      if (!state.dragging || !state.container) return;
      const rect = state.container.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      setSplitPct(state.container, pct);
    });

    window.addEventListener('mouseup', function () {
      if (!state.dragging) return;
      state.dragging = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    });
  }

  function bindEditorScrollOnce() {
    function scrollPreviewToElement(preview, el) {
      try {
        const pr = preview.getBoundingClientRect();
        const er = el.getBoundingClientRect();
        const targetTop = er.top - pr.top + preview.scrollTop - 8;
        preview.scrollTop = targetTop;
      } catch (_) {
        // ignore
      }
    }

    function getOffsetTopInScrollContainer(scrollEl, childEl) {
      const sr = scrollEl.getBoundingClientRect();
      const cr = childEl.getBoundingClientRect();
      return cr.top - sr.top + scrollEl.scrollTop - 8;
    }

    function clamp01(x) {
      return Math.max(0, Math.min(1, x));
    }

    function findPreviewHeading(preview, headingText) {
      const wanted = normalizeText(headingText);
      if (!wanted) return null;
      const headings = Array.from(preview.querySelectorAll('h1,h2,h3,h4,h5,h6'));
      let match = headings.find((h) => normalizeText(h.textContent) === wanted);
      if (match) return match;
      // Be tolerant: some renderers may add extra whitespace/inline nodes.
      match = headings.find((h) => normalizeText(h.textContent).includes(wanted));
      return match || null;
    }

    function buildEditorH2Cache(editor) {
      try {
        const model = editor && typeof editor.getModel === 'function' ? editor.getModel() : null;
        if (!model) return { versionId: null, lines: [] };
        const versionId = typeof model.getVersionId === 'function' ? model.getVersionId() : null;

        if (state.editorH2Cache && state.editorH2Cache.versionId === versionId) {
          return state.editorH2Cache;
        }

        const lineCount = typeof model.getLineCount === 'function' ? model.getLineCount() : 0;
        const lines = [];

        // Avoid false positives: headings inside fenced code blocks shouldn't count.
        let inCode = false;
        let fenceChar = '';
        let fenceLen = 0;

        function maybeOpenFence(rawLine) {
          const m = /^\s{0,3}([`~]{3,})(.*)$/.exec(rawLine);
          if (!m) return null;
          const fence = m[1];
          return { ch: fence[0], len: fence.length };
        }

        function isFenceClose(rawLine, ch, len) {
          if (!ch || !len) return false;
          const re = new RegExp('^\\s{0,3}' + (ch === '`' ? '`' : '~') + '{' + len + ',}\\s*$');
          return re.test(rawLine);
        }

        for (let ln = 1; ln <= lineCount; ln += 1) {
          const line = (model.getLineContent(ln) || '').replace(/\r$/, '');

          if (!inCode) {
            const opened = maybeOpenFence(line);
            if (opened) {
              inCode = true;
              fenceChar = opened.ch;
              fenceLen = opened.len;
              continue;
            }
          } else {
            if (isFenceClose(line, fenceChar, fenceLen)) {
              inCode = false;
              fenceChar = '';
              fenceLen = 0;
            }
            continue;
          }

          const m = /^(##)\s+(.+?)\s*$/.exec(line);
          if (m) {
            lines.push({ lineNumber: ln, text: normalizeText(m[2]) });
          }
        }

        state.editorH2Cache = { versionId, lines };
        return state.editorH2Cache;
      } catch (_) {
        return { versionId: null, lines: [] };
      }
    }

    function getEditorTopLine(editor) {
      try {
        if (editor && typeof editor.getVisibleRanges === 'function') {
          const ranges = editor.getVisibleRanges() || [];
          if (ranges.length && ranges[0] && ranges[0].startLineNumber) {
            return ranges[0].startLineNumber;
          }
        }
      } catch (_) {
        // ignore
      }
      return 1;
    }

    function findSectionIndexForTopLine(h2Lines, topLine) {
      // Returns the last index where lineNumber <= topLine, or -1 if before first H2.
      let lo = 0;
      let hi = h2Lines.length - 1;
      let ans = -1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const ln = h2Lines[mid].lineNumber;
        if (ln <= topLine) {
          ans = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      return ans;
    }

    function computeSectionProgress(editor, startLine, nextLine) {
      // Map editor.scrollTop from startLine -> nextLine (or EOF) into [0..1].
      // Add a small deadzone near section start to create a subtle “stuck” feel.
      const DEADZONE_PX = 14;
      try {
        if (!editor || typeof editor.getScrollTop !== 'function') return { ok: false, progress: 0 };
        const scrollTop = editor.getScrollTop();

        let startTop = 0;
        if (typeof editor.getTopForLineNumber === 'function') {
          startTop = editor.getTopForLineNumber(Math.max(1, startLine));
        }

        let endTop = null;
        if (nextLine && typeof editor.getTopForLineNumber === 'function') {
          endTop = editor.getTopForLineNumber(Math.max(1, nextLine));
        } else {
          const eHeight = typeof editor.getScrollHeight === 'function' ? editor.getScrollHeight() : 0;
          const eViewport =
            typeof editor.getLayoutInfo === 'function' && editor.getLayoutInfo() ? editor.getLayoutInfo().height : 0;
          endTop = Math.max(0, eHeight - eViewport);
        }

        const rawLen = Math.max(1, endTop - startTop);
        const delta = scrollTop - startTop;
        const deadz = Math.min(DEADZONE_PX, Math.max(0, rawLen - 1));
        const effectiveDelta = Math.max(0, delta - deadz);
        const effectiveLen = Math.max(1, rawLen - deadz);
        return { ok: true, progress: clamp01(effectiveDelta / effectiveLen) };
      } catch (_) {
        return { ok: false, progress: 0 };
      }
    }

    function previewH2ByTextOccurrence(preview, text, occurrenceIdx) {
      const wanted = normalizeText(text);
      if (!wanted) return null;
      const h2s = Array.from(preview.querySelectorAll('h2'));

      // 1) Exact matches by normalized text.
      let hits = 0;
      for (const el of h2s) {
        if (normalizeText(el.textContent) === wanted) {
          if (hits === occurrenceIdx) return el;
          hits += 1;
        }
      }

      // 2) Tolerant matches (includes), e.g. emoji/inline nodes/extra whitespace.
      hits = 0;
      for (const el of h2s) {
        const t = normalizeText(el.textContent);
        if (t.includes(wanted) || wanted.includes(t)) {
          if (hits === occurrenceIdx) return el;
          hits += 1;
        }
      }

      return null;
    }

    function occurrenceIndexInEditorH2s(h2Lines, idx) {
      if (idx == null || idx < 0 || idx >= h2Lines.length) return 0;
      const wanted = h2Lines[idx].text;
      let occ = 0;
      for (let i = 0; i <= idx; i += 1) {
        if (h2Lines[i].text === wanted) occ += 1;
      }
      return Math.max(0, occ - 1);
    }

    function scrollPreviewToSectionProgress(preview, startIdx, nextIdx, progress, editorHeadingText, editorNextHeadingText, h2Lines) {
      try {
        const h2s = Array.from(preview.querySelectorAll('h2'));

        let startTop = 0;
        if (startIdx >= 0) {
          const startOcc = occurrenceIndexInEditorH2s(h2Lines || [], startIdx);
          const startEl =
            (editorHeadingText ? previewH2ByTextOccurrence(preview, editorHeadingText, startOcc) : null) ||
            h2s[startIdx] ||
            (editorHeadingText ? findPreviewHeading(preview, editorHeadingText) : null);
          if (startEl) {
            startTop = getOffsetTopInScrollContainer(preview, startEl);
          }
        }

        let endTop = null;
        if (nextIdx != null && nextIdx >= 0) {
          const nextOcc = occurrenceIndexInEditorH2s(h2Lines || [], nextIdx);
          const endEl =
            (editorNextHeadingText ? previewH2ByTextOccurrence(preview, editorNextHeadingText, nextOcc) : null) ||
            h2s[nextIdx] ||
            (editorNextHeadingText ? findPreviewHeading(preview, editorNextHeadingText) : null);
          if (endEl) {
            endTop = getOffsetTopInScrollContainer(preview, endEl);
          }
        }
        if (endTop == null) {
          endTop = Math.max(0, preview.scrollHeight - preview.clientHeight);
        }

        preview.scrollTop = startTop + (endTop - startTop) * clamp01(progress);
        return true;
      } catch (_) {
        return false;
      }
    }

    function getEditorTopHeading(editor) {
      try {
        const model = editor && typeof editor.getModel === 'function' ? editor.getModel() : null;
        if (!model || typeof model.getLineCount !== 'function') return null;

        let topLine = 1;
        if (typeof editor.getVisibleRanges === 'function') {
          const ranges = editor.getVisibleRanges() || [];
          if (ranges.length && ranges[0] && ranges[0].startLineNumber) {
            topLine = ranges[0].startLineNumber;
          }
        }

        const maxLookback = 400;
        const minLine = Math.max(1, topLine - maxLookback);

        for (let ln = topLine; ln >= minLine; ln -= 1) {
          const line = model.getLineContent(ln) || '';
          const m = /^(#{1,6})\s+(.+?)\s*$/.exec(line);
          if (m) {
            return { lineNumber: ln, text: normalizeText(m[2]) };
          }
        }

        return null;
      } catch (_) {
        return null;
      }
    }

    function syncPreviewFromEditor() {
      if (!state.container || !state.previewScrollEl) return;
      if (!getLocked(state.container)) return;
      if (state.syncing) return;

      const ed = state.editor;
      const p = state.previewScrollEl;

      state.syncing = true;

      // Section-aware sync (H2/##): within each section, map editor scroll progress
      // to preview scroll progress proportionally.
      try {
        if (ed && typeof ed.getModel === 'function') {
          const cache = buildEditorH2Cache(ed);
          const h2Lines = cache.lines || [];
          const topLine = getEditorTopLine(ed);
          const startIdx = findSectionIndexForTopLine(h2Lines, topLine);

          const startLine = startIdx >= 0 ? h2Lines[startIdx].lineNumber : 1;
          const nextIdx = startIdx + 1 < h2Lines.length ? startIdx + 1 : null;
          const nextLine = nextIdx != null ? h2Lines[nextIdx].lineNumber : null;
          const headingText = startIdx >= 0 ? h2Lines[startIdx].text : null;
          const nextHeadingText = nextIdx != null ? h2Lines[nextIdx].text : null;

          const prog = computeSectionProgress(ed, startLine, nextLine);
          if (prog.ok) {
            const ok = scrollPreviewToSectionProgress(
              p,
              startIdx,
              nextIdx,
              prog.progress,
              headingText,
              nextHeadingText,
              h2Lines
            );
            if (ok) {
              state.lastHeadingText = headingText;
              requestAnimationFrame(function () {
                state.syncing = false;
              });
              return;
            }
          }
        }
      } catch (_) {
        // ignore
      }

      // Prefer content-aware sync: align preview to the nearest visible heading.
      const heading = ed ? getEditorTopHeading(ed) : null;
      if (heading && heading.text) {
        const hEl = findPreviewHeading(p, heading.text);
        if (hEl) {
          state.lastHeadingText = heading.text;
          scrollPreviewToElement(p, hEl);
          requestAnimationFrame(function () {
            state.syncing = false;
          });
          return;
        }
      }

      // Fallback: proportional scroll.
      try {
        if (ed && typeof ed.getScrollTop === 'function' && typeof ed.getScrollHeight === 'function') {
          const eTop = ed.getScrollTop();
          const eHeight = ed.getScrollHeight();
          const eViewport =
            typeof ed.getLayoutInfo === 'function' && ed.getLayoutInfo() ? ed.getLayoutInfo().height : 0;
          const eMax = Math.max(1, eHeight - eViewport);
          const pMax = Math.max(1, p.scrollHeight - p.clientHeight);
          const ratio = eTop / eMax;
          p.scrollTop = ratio * pMax;
        }
      } catch (_) {
        // ignore
      }

      requestAnimationFrame(function () {
        state.syncing = false;
      });
    }

    function scheduleSyncFromEditor() {
      if (state.pendingPreviewSync) return;
      state.pendingPreviewSync = true;
      requestAnimationFrame(function () {
        state.pendingPreviewSync = false;
        syncPreviewFromEditor();
      });
    }

    // Monaco API path (preferred)
    if (
      state.editor &&
      !state.editor.__codocScrollBound &&
      typeof state.editor.onDidScrollChange === 'function'
    ) {
      state.editor.__codocScrollBound = true;
      state.editor.onDidScrollChange(function () {
        scheduleSyncFromEditor();
      });
      return;
    }

    // DOM fallback
    if (!state.editorScrollEl || state.editorScrollEl.__codocBound) return;
    state.editorScrollEl.__codocBound = true;

    state.editorScrollEl.addEventListener('scroll', function () {
      if (!state.container || !state.previewScrollEl) return;
      if (!getLocked(state.container)) return;
      if (state.syncing) return;

      const e = state.editorScrollEl;
      const p = state.previewScrollEl;

      const eMax = Math.max(1, e.scrollHeight - e.clientHeight);
      const pMax = Math.max(1, p.scrollHeight - p.clientHeight);
      const ratio = e.scrollTop / eMax;

      state.syncing = true;
      p.scrollTop = ratio * pMax;
      requestAnimationFrame(function () {
        state.syncing = false;
      });
    });
  }

  function refresh() {
    if (!findElements()) return;
    applySavedSplit(state.container);
    bindDividerOnce();
    bindEditorScrollOnce();

    // Monaco often loads after initial DOM; retry a few times to upgrade from DOM fallback
    // to Monaco API-based scroll syncing.
    const monacoReady =
      !!window.monaco &&
      !!window.monaco.editor &&
      typeof window.monaco.editor.getEditors === 'function' &&
      (window.monaco.editor.getEditors() || []).length > 0;

    if (!state.editor && monacoReady) {
      scheduleRetryRefresh();
    } else if (state.editor) {
      clearRetryRefresh();
    }
  }

  function scheduleRetryRefresh() {
    if (state.retryTimer) return;
    state.retryCount = 0;
    state.retryTimer = window.setInterval(function () {
      state.retryCount += 1;
      try {
        refresh();
      } catch (_) {
        // ignore
      }
      // Stop after ~10s.
      if (state.retryCount >= 20) {
        clearRetryRefresh();
      }
    }, 500);
  }

  function clearRetryRefresh() {
    if (!state.retryTimer) return;
    window.clearInterval(state.retryTimer);
    state.retryTimer = null;
    state.retryCount = 0;
  }

  function init() {
    refresh();

    // Reflex is a SPA; re-run when DOM changes (view mode switch, monaco mount, etc.).
    const mo = new MutationObserver(function () {
      refresh();
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });

    // Safety net: ensure we eventually bind Monaco scroll handlers even if mutations
    // don't fire in the right moment.
    scheduleRetryRefresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
