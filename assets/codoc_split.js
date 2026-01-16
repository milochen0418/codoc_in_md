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
    editorH2Cache: { versionId: null, headings: [] },
    previewLineMarkerCache: { count: 0, lines: [], els: [] },
    retryTimer: null,
    retryCount: 0,
  };

  function slugifyGfm(text) {
    let s = String(text || '').trim();
    if (!s) return '';
    try {
      s = s.normalize('NFKD');
    } catch (_) {
      // ignore
    }
    s = s.toLowerCase();
    // Keep unicode letters/numbers, whitespace, and hyphens.
    // This matches GitHub/CodiMD behavior more closely for CJK headings.
    try {
      s = s.replace(/[^\p{L}\p{N}\s-]/gu, '');
    } catch (_) {
      // Fallback if unicode property escapes are unavailable.
      s = s.replace(/[^\w\s-]/g, '');
    }
    s = s.replace(/\s+/g, '-');
    s = s.replace(/-+/g, '-');
    s = s.replace(/^-+|-+$/g, '');
    return s;
  }

  function ensureHeadingIds(previewRoot) {
    if (!previewRoot) return;
    const headings = Array.from(previewRoot.querySelectorAll('h1,h2,h3,h4,h5,h6'));
    const used = new Map();

    // Seed `used` with existing ids.
    for (const h of headings) {
      const id = (h.getAttribute('id') || '').trim();
      if (!id) continue;
      used.set(id, (used.get(id) || 0) + 1);
    }

    for (const h of headings) {
      const existing = (h.getAttribute('id') || '').trim();
      if (existing) continue;
      const base = slugifyGfm(h.textContent || '');
      if (!base) continue;
      let id = base;
      if (used.has(id)) {
        let n = used.get(id) || 1;
        // CodiMD/GitHub style: append -1, -2, ...
        while (used.has(base + '-' + n)) n += 1;
        id = base + '-' + n;
      }
      h.setAttribute('id', id);
      used.set(id, 1);
    }
  }

  function buildToc(previewRoot, maxLevel) {
    const headings = Array.from(previewRoot.querySelectorAll('h1,h2,h3,h4,h5,h6'))
      .map((h) => {
        const level = parseInt(String(h.tagName || '').slice(1), 10);
        return { h, level };
      })
      .filter((x) => Number.isFinite(x.level) && x.level >= 1 && x.level <= maxLevel)
      .filter((x) => (x.h.getAttribute('id') || '').trim().length > 0);

    if (!headings.length) return null;

    const minLevel = Math.min.apply(
      null,
      headings.map((x) => x.level)
    );

    const tocRoot = document.createElement('div');
    tocRoot.className = 'toc my-4';

    function listStyleTypeForDepth(depthIdx) {
      return depthIdx <= 0 ? 'disc' : depthIdx === 1 ? 'circle' : depthIdx === 2 ? 'square' : 'disc';
    }

    function applyListStyles(ul, depthIdx) {
      ul.style.listStylePosition = 'outside';
      ul.style.listStyleType = listStyleTypeForDepth(depthIdx);
      ul.style.paddingLeft = '1.5rem';
      ul.style.marginLeft = depthIdx <= 0 ? '0.25rem' : '1rem';
      ul.style.marginTop = '0.25rem';
      ul.style.marginBottom = '0';
    }

    const topUl = document.createElement('ul');
    applyListStyles(topUl, 0);
    tocRoot.appendChild(topUl);

    const stack = [{ level: minLevel, ul: topUl, lastLi: null }];

    function ensureDepth(targetLevel) {
      while (stack.length && targetLevel < stack[stack.length - 1].level) {
        stack.pop();
      }
      while (stack.length && targetLevel > stack[stack.length - 1].level) {
        const parent = stack[stack.length - 1];
        const parentLi = parent.lastLi;
        const newUl = document.createElement('ul');
        const depthIdx = stack.length;
        applyListStyles(newUl, depthIdx);
        if (parentLi) {
          parentLi.appendChild(newUl);
        } else {
          parent.ul.appendChild(newUl);
        }
        stack.push({ level: parent.level + 1, ul: newUl, lastLi: null });
      }
    }

    for (const item of headings) {
      const level = item.level;
      ensureDepth(level);

      const li = document.createElement('li');
      const depthIdx = Math.max(0, stack.length - 1);
      li.style.display = 'list-item';
      li.style.listStylePosition = 'outside';
      li.style.listStyleType = listStyleTypeForDepth(depthIdx);
      li.style.marginTop = '0.25rem';
      li.style.marginLeft = depthIdx <= 0 ? '0' : '0.5rem';
      const a = document.createElement('a');
      a.href = '#' + item.h.getAttribute('id');
      a.textContent = normalizeText(item.h.textContent || '');
      a.style.color = '#4f46e5';
      a.style.textDecoration = 'none';
      a.addEventListener('mouseenter', () => {
        a.style.textDecoration = 'underline';
      });
      a.addEventListener('mouseleave', () => {
        a.style.textDecoration = 'none';
      });
      li.appendChild(a);
      const top = stack[stack.length - 1];
      top.ul.appendChild(li);
      top.lastLi = li;
    }

    return tocRoot;
  }

  function renderTocPlaceholders(previewRoot) {
    if (!previewRoot) return;
    const placeholders = Array.from(previewRoot.querySelectorAll('div.codoc-toc[data-codoc-toc="1"]'));
    if (!placeholders.length) return;

    ensureHeadingIds(previewRoot);

    for (const ph of placeholders) {
      const raw = (ph.getAttribute('data-toc-depth') || '').trim();
      const depth = Math.max(1, Math.min(6, parseInt(raw || '3', 10) || 3));
      const toc = buildToc(previewRoot, depth);
      if (!toc) {
        ph.replaceWith(document.createTextNode(''));
        continue;
      }
      ph.replaceWith(toc);
    }
  }

  function scrollPreviewToHash(previewScrollEl, hash) {
    if (!previewScrollEl) return;
    const id = String(hash || '').replace(/^#/, '').trim();
    if (!id) return;
    let target = null;
    try {
      target = previewScrollEl.querySelector('#' + CSS.escape(id));
    } catch (_) {
      target = previewScrollEl.querySelector('[id="' + id.replace(/"/g, '') + '"]');
    }
    if (!target) return;
    try {
      const top = target.getBoundingClientRect().top - previewScrollEl.getBoundingClientRect().top;
      previewScrollEl.scrollTop = previewScrollEl.scrollTop + top - 8;
    } catch (_) {
      // ignore
    }
  }

  function bindPreviewHashScrollOnce() {
    if (!state.previewScrollEl || state.previewScrollEl.__codocHashBound) return;
    state.previewScrollEl.__codocHashBound = true;

    state.previewScrollEl.addEventListener(
      'click',
      function (e) {
        const a = e.target && e.target.closest ? e.target.closest('a') : null;
        if (!a) return;
        const href = a.getAttribute('href') || '';
        if (!href || href[0] !== '#') return;
        e.preventDefault();
        const id = href;
        // Keep URL hash in sync (HackMD-like).
        try {
          window.history.replaceState(null, '', id);
        } catch (_) {
          // ignore
        }
        scrollPreviewToHash(state.previewScrollEl, id);
      },
      true
    );

    // Initial load hash.
    if (window.location && window.location.hash) {
      scrollPreviewToHash(state.previewScrollEl, window.location.hash);
    }
  }

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

    function cleanupHeadingText(raw) {
      // Approximate the rendered heading text from markdown source.
      // Example: "[書籍m模式](/book-example)" -> "書籍m模式"
      let s = String(raw || '');
      // Strip HTML tags.
      s = s.replace(/<[^>]+>/g, ' ');
      // Replace markdown images/links with their labels.
      s = s.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '$1');
      s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1');
      // Strip inline code.
      s = s.replace(/`([^`]+)`/g, '$1');
      // Strip common emphasis markers.
      s = s.replace(/\*\*([^*]+)\*\*/g, '$1');
      s = s.replace(/__([^_]+)__/g, '$1');
      s = s.replace(/\*([^*]+)\*/g, '$1');
      s = s.replace(/_([^_]+)_/g, '$1');
      return normalizeText(s);
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
        if (!model) return { versionId: null, headings: [] };
        const versionId = typeof model.getVersionId === 'function' ? model.getVersionId() : null;

        if (state.editorH2Cache && state.editorH2Cache.versionId === versionId) {
          return state.editorH2Cache;
        }

        const lineCount = typeof model.getLineCount === 'function' ? model.getLineCount() : 0;
        const headings = [];

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

          const m = /^(#{1,4})\s+(.+?)\s*$/.exec(line);
          if (m) {
            const level = m[1].length;
            headings.push({ lineNumber: ln, level, text: cleanupHeadingText(m[2]) });
          }
        }

        state.editorH2Cache = { versionId, headings };
        return state.editorH2Cache;
      } catch (_) {
        return { versionId: null, headings: [] };
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

    function getEditorLastLineTop(editor) {
      try {
        const model = editor && typeof editor.getModel === 'function' ? editor.getModel() : null;
        if (!model || typeof model.getLineCount !== 'function') return null;
        const lastLine = model.getLineCount();
        if (typeof editor.getTopForLineNumber !== 'function') return null;
        return editor.getTopForLineNumber(Math.max(1, lastLine));
      } catch (_) {
        return null;
      }
    }

    function isEditorBeyondLastLine(editor) {
      // When Monaco allows scrolling beyond the last line, scrollTop can exceed
      // the top position of the last line. In that "slack" region, we should
      // freeze preview to avoid it moving while editor is effectively past EOF.
      try {
        if (!editor || typeof editor.getScrollTop !== 'function') return false;
        const lastTop = getEditorLastLineTop(editor);
        if (lastTop == null) return false;
        const EPS = 2;
        return editor.getScrollTop() > lastTop + EPS;
      } catch (_) {
        return false;
      }
    }

    function getEditorScrollMetrics(editor) {
      try {
        if (!editor || typeof editor.getScrollTop !== 'function') return null;
        const scrollTop = editor.getScrollTop();
        const eHeight = typeof editor.getScrollHeight === 'function' ? editor.getScrollHeight() : null;
        const eViewport =
          typeof editor.getLayoutInfo === 'function' && editor.getLayoutInfo() ? editor.getLayoutInfo().height : null;
        if (!Number.isFinite(eHeight) || !Number.isFinite(eViewport)) return null;
        const maxScrollTop = Math.max(0, eHeight - eViewport);
        return { scrollTop, maxScrollTop, viewport: eViewport };
      } catch (_) {
        return null;
      }
    }

    function isEditorNearBottom(editor) {
      // Match the "manual trailing heading" feel:
      // when user is in the bottom slack band, keep preview pinned.
      const m = getEditorScrollMetrics(editor);
      if (!m) return false;
      const band = clamp(Math.floor(m.viewport * 0.6), 80, 420);
      return m.maxScrollTop - m.scrollTop <= band;
    }

    function findSectionIndexForTopLine(headings, topLine) {
      // Returns the last index where lineNumber <= topLine, or -1 if before first H2.
      let lo = 0;
      let hi = headings.length - 1;
      let ans = -1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const ln = headings[mid].lineNumber;
        if (ln <= topLine) {
          ans = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      return ans;
    }

    function computeSectionProgress(editor, startLine, nextLine, deadzonePx) {
      // Map editor.scrollTop from startLine -> nextLine (or EOF) into [0..1].
      // deadzonePx is only for real headings (to create a subtle “stuck” feel).
      // For soft anchors (line markers), pass 0.
      const DEADZONE_PX = Number.isFinite(deadzonePx) ? Math.max(0, deadzonePx) : 14;
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

    function getPreviewLineMarkers(preview) {
      try {
        const nodes = Array.from(preview.querySelectorAll('[data-codoc-mdline]'));
        const count = nodes.length;
        if (state.previewLineMarkerCache && state.previewLineMarkerCache.count === count) {
          const cached = state.previewLineMarkerCache;
          const first = cached.els && cached.els[0];
          if (first && first.isConnected && preview.contains(first)) {
            return cached;
          }
          // DOM likely re-rendered; rebuild even if count is the same.
        }

        const lines = [];
        const els = [];
        for (const el of nodes) {
          const raw = el.getAttribute('data-codoc-mdline');
          const n = raw ? parseInt(raw, 10) : NaN;
          if (!Number.isFinite(n)) continue;
          lines.push(n);
          els.push(el);
        }

        state.previewLineMarkerCache = { count, lines, els };
        return state.previewLineMarkerCache;
      } catch (_) {
        return { count: 0, lines: [], els: [] };
      }
    }

    function getPreviewTailAnchor(preview) {
      try {
        return preview.querySelector('[data-codoc-tail="1"]');
      } catch (_) {
        return null;
      }
    }

    function lastIndexLE(sortedNums, target) {
      let lo = 0;
      let hi = sortedNums.length - 1;
      let ans = -1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const v = sortedNums[mid];
        if (v <= target) {
          ans = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }
      return ans;
    }

    function previewHeadingByTextOccurrence(preview, level, text, occurrenceIdx) {
      const wanted = normalizeText(text);
      if (!wanted) return null;
      const selector = level ? 'h' + String(level) : 'h1,h2,h3,h4,h5,h6';
      const hs = Array.from(preview.querySelectorAll(selector));

      // 1) Exact matches by normalized text.
      let hits = 0;
      for (const el of hs) {
        if (normalizeText(el.textContent) === wanted) {
          if (hits === occurrenceIdx) return el;
          hits += 1;
        }
      }

      // 2) Tolerant matches (includes), e.g. emoji/inline nodes/extra whitespace.
      hits = 0;
      for (const el of hs) {
        const t = normalizeText(el.textContent);
        // Avoid reverse-substring matches that cause jumps, e.g.
        // wanted="[書籍m模式](/...)" contains t="m模式".
        const allowReverse = t.length >= Math.max(4, Math.floor(wanted.length * 0.9));
        if (t.includes(wanted) || (allowReverse && wanted.includes(t))) {
          if (hits === occurrenceIdx) return el;
          hits += 1;
        }
      }

      return null;
    }

    function occurrenceIndexInEditorHeadings(headings, idx) {
      if (idx == null || idx < 0 || idx >= headings.length) return 0;
      const wanted = headings[idx].text;
      const level = headings[idx].level;
      let occ = 0;
      for (let i = 0; i <= idx; i += 1) {
        if (headings[i].level === level && headings[i].text === wanted) occ += 1;
      }
      return Math.max(0, occ - 1);
    }

    function scrollPreviewToSectionProgress(
      preview,
      startIdx,
      nextIdx,
      progress,
      startHeading,
      nextHeading,
      headings
    ) {
      try {
        let startTop = 0;
        if (startIdx >= 0 && startHeading) {
          const startOcc = occurrenceIndexInEditorHeadings(headings || [], startIdx);
          const startEl =
            previewHeadingByTextOccurrence(preview, startHeading.level, startHeading.text, startOcc) ||
            previewHeadingByTextOccurrence(preview, null, startHeading.text, startOcc) ||
            findPreviewHeading(preview, startHeading.text);
          if (startEl) {
            startTop = getOffsetTopInScrollContainer(preview, startEl);
          }
        }

        let endTop = null;
        if (nextIdx != null && nextIdx >= 0 && nextHeading) {
          const nextOcc = occurrenceIndexInEditorHeadings(headings || [], nextIdx);
          const endEl =
            previewHeadingByTextOccurrence(preview, nextHeading.level, nextHeading.text, nextOcc) ||
            previewHeadingByTextOccurrence(preview, null, nextHeading.text, nextOcc) ||
            findPreviewHeading(preview, nextHeading.text);
          if (endEl) {
            endTop = getOffsetTopInScrollContainer(preview, endEl);
          }
        }
        if (endTop == null) {
          const tail = getPreviewTailAnchor(preview);
          endTop = tail
            ? getOffsetTopInScrollContainer(preview, tail)
            : Math.max(0, preview.scrollHeight - preview.clientHeight);
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

      // Tail clamp: if editor is near bottom (including scrollBeyondLastLine slack),
      // keep preview pinned to bottom until editor scrolls back into content.
      try {
        if (ed && isEditorNearBottom(ed)) {
          p.scrollTop = Math.max(0, p.scrollHeight - p.clientHeight);
          requestAnimationFrame(function () {
            state.syncing = false;
          });
          return;
        }
      } catch (_) {
        // ignore
      }

      // Best effort: line-marker sync (reduces drift for very long heading sections).
      // If markers exist in preview, map Monaco visible top line -> nearest marker range.
      try {
        if (ed && typeof ed.getModel === 'function') {
          const markers = getPreviewLineMarkers(p);
          if (markers && markers.lines && markers.lines.length >= 2) {
            const topLine = getEditorTopLine(ed);
            const idx = lastIndexLE(markers.lines, topLine);
            if (idx >= 0) {
              // If we're in the last marker bucket, pin preview to bottom. This matches
              // the "manual trailing heading" behavior (preview doesn't move in tail slack).
              if (idx >= markers.lines.length - 1) {
                const tail = getPreviewTailAnchor(p);
                p.scrollTop = tail
                  ? getOffsetTopInScrollContainer(p, tail)
                  : Math.max(0, p.scrollHeight - p.clientHeight);
                requestAnimationFrame(function () {
                  state.syncing = false;
                });
                return;
              }

              const startLine = markers.lines[idx];
              const nextLine = idx + 1 < markers.lines.length ? markers.lines[idx + 1] : null;
              const startEl = markers.els[idx];
              const nextEl = idx + 1 < markers.els.length ? markers.els[idx + 1] : null;

              const startTop = startEl ? getOffsetTopInScrollContainer(p, startEl) : 0;
              let endTop = null;
              if (nextEl) {
                endTop = getOffsetTopInScrollContainer(p, nextEl);
              } else {
                const tail = getPreviewTailAnchor(p);
                endTop = tail
                  ? getOffsetTopInScrollContainer(p, tail)
                  : Math.max(0, p.scrollHeight - p.clientHeight);
              }

              const prog = computeSectionProgress(ed, startLine, nextLine, 0);
              if (prog.ok) {
                p.scrollTop = startTop + (endTop - startTop) * clamp01(prog.progress);
                requestAnimationFrame(function () {
                  state.syncing = false;
                });
                return;
              }
            }
          }
        }
      } catch (_) {
        // ignore
      }

      // Section-aware sync (#..####): within each heading section, map editor scroll
      // progress to preview scroll progress proportionally.
      try {
        if (ed && typeof ed.getModel === 'function') {
          const cache = buildEditorH2Cache(ed);
          const headings = cache.headings || [];
          const topLine = getEditorTopLine(ed);
          const startIdx = findSectionIndexForTopLine(headings, topLine);

          const startHeading = startIdx >= 0 ? headings[startIdx] : null;
          const nextIdx = startIdx + 1 < headings.length ? startIdx + 1 : null;
          const nextHeading = nextIdx != null ? headings[nextIdx] : null;

          const startLine = startHeading ? startHeading.lineNumber : 1;
          const nextLine = nextHeading ? nextHeading.lineNumber : null;

          const prog = computeSectionProgress(ed, startLine, nextLine, 14);
          if (prog.ok) {
            const ok = scrollPreviewToSectionProgress(
              p,
              startIdx,
              nextIdx,
              prog.progress,
              startHeading,
              nextHeading,
              headings
            );
            if (ok) {
              state.lastHeadingText = startHeading ? startHeading.text : null;
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
    bindPreviewHashScrollOnce();
    // Post-render enhancements (CodiMD-like): heading ids + TOC rendering.
    try {
      if (state.previewScrollEl) {
        ensureHeadingIds(state.previewScrollEl);
        renderTocPlaceholders(state.previewScrollEl);
      }
    } catch (_) {
      // ignore
    }

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
