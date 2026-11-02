(function () {
  // Frames embedded in the preview: ReflexGrid's forms and tables (embeds.GridEmbed) and Codoc in
  // VecDraw's drawings (embeds.VecdrawEmbed).
  //
  // The document only holds an empty box for each one. The frames live in a layer of their own in
  // the preview's scroll area, placed over their boxes: the preview is drawn anew on every edit, and
  // when a block is added above a box React moves the box, and an iframe that moves reloads. A form
  // someone is filling in has to survive the others typing in the document.

  const INIT_KEY = '__codocEmbedFramesInit';
  if (window[INIT_KEY]) return;
  window[INIT_KEY] = true;

  const MESSAGES = ['reflex-grid-embed', 'vecdraw-embed'];
  // A box stays this long before its frame loads: someone may still be typing the line.
  const SETTLE_MS = 500;
  // A frame stays this long (hidden) after its box went: it may be back on the next render.
  const GONE_MS = 2000;
  // A table taller than this share of the window scrolls inside its frame; a drawing gets smaller.
  const TABLE_MAX = 0.7;

  const frames = new Map(); // "<src> <nth of that src>" -> {src, kind, box, el, origin, height, ratio, since, gone}
  let pane = null;
  let layer = null;
  let sizes = null;
  let edits = null;
  let scheduled = false;

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(sync);
  }

  function makeFrame(f) {
    const el = document.createElement('iframe');
    el.src = f.src;
    el.title = f.kind === 'drawing' ? 'Codoc in VecDraw' : 'ReflexGrid';
    el.setAttribute('frameborder', '0');
    el.setAttribute('allow', 'clipboard-write');
    el.style.cssText = 'position:absolute;border:0;background:#fff;display:block;';
    layer.appendChild(el);
    return el;
  }

  function fit(f, base) {
    const wanted = f.ratio ? f.box.getBoundingClientRect().width * f.ratio : f.height;
    if (wanted) {
      const room = f.kind === 'form' ? Infinity : Math.max(200, window.innerHeight * TABLE_MAX);
      const height = Math.min(wanted, room) + 'px';
      if (f.box.style.height !== height) {
        f.box.style.minHeight = '0';
        f.box.style.height = height;
      }
    }
    const r = f.box.getBoundingClientRect();
    const s = f.el.style;
    s.top = r.top - base.top + pane.scrollTop + 'px';
    s.left = r.left - base.left + pane.scrollLeft + 'px';
    s.width = r.width + 'px';
    s.height = r.height + 'px';
    s.visibility = '';
  }

  function sync() {
    scheduled = false;
    if (!pane || !layer) return;
    const now = Date.now();
    const base = pane.getBoundingClientRect();
    const counts = new Map();
    const seen = new Set();
    pane.querySelectorAll('[data-embed-src]').forEach((box) => {
      const src = box.dataset.embedSrc;
      const n = (counts.get(src) || 0) + 1;
      counts.set(src, n);
      const key = src + ' ' + n;
      seen.add(key);
      let f = frames.get(key);
      if (!f) {
        f = { src, kind: box.dataset.embedKind, el: null, height: 0, ratio: 0, since: now, gone: 0 };
        f.origin = new URL(src, location.href).origin;
        frames.set(key, f);
        setTimeout(schedule, SETTLE_MS);
      }
      f.box = box;
      f.gone = 0;
      if (!f.el && now - f.since >= SETTLE_MS) f.el = makeFrame(f);
      if (f.el) fit(f, base);
    });
    frames.forEach((f, key) => {
      if (seen.has(key)) return;
      if (!f.gone) {
        f.gone = now;
        if (f.el) f.el.style.visibility = 'hidden';
        setTimeout(schedule, GONE_MS);
      } else if (now - f.gone >= GONE_MS) {
        if (f.el) f.el.remove();
        frames.delete(key);
      }
    });
  }

  // The preview pane is replaced when the view mode changes: its frames go with it.
  function attach() {
    const el = document.getElementById('preview-pane');
    if (el === pane) return;
    if (sizes) sizes.disconnect();
    if (edits) edits.disconnect();
    frames.clear();
    pane = el;
    layer = null;
    if (!pane) return;
    if (getComputedStyle(pane).position === 'static') pane.style.position = 'relative';
    layer = document.createElement('div');
    layer.id = 'embed-layer';
    layer.style.cssText = 'position:absolute;left:0;top:0;width:0;height:0;';
    pane.appendChild(layer);
    sizes = new ResizeObserver(schedule);
    sizes.observe(pane);
    if (pane.firstElementChild) sizes.observe(pane.firstElementChild);
    edits = new MutationObserver(schedule);
    edits.observe(pane, { childList: true, subtree: true, characterData: true });
    schedule();
  }

  setInterval(attach, 400);
  attach();
  window.addEventListener('resize', schedule);

  // A frame says how tall it wants to be, in pixels or as a share of its width; only the frame
  // itself can say that.
  window.addEventListener('message', (ev) => {
    const m = ev.data;
    if (!m || !MESSAGES.includes(m.type)) return;
    frames.forEach((f) => {
      if (f.el && f.el.contentWindow === ev.source && f.origin === ev.origin) {
        f.height = Math.max(0, Number(m.height) || 0);
        f.ratio = Math.max(0, Number(m.ratio) || 0);
        schedule();
      }
    });
  });

  // Puts a block on lines of its own: at the caret, or at the end of the document when there is no
  // caret to speak of (the editor is hidden, or was never clicked). Through the editor, so everyone
  // on the document gets it.
  window.codocInsertBlock = (text) => {
    const eds = window.monaco && window.monaco.editor && window.monaco.editor.getEditors();
    const ed = eds && eds.length > 0 ? eds[0] : null;
    const model = ed && ed.getModel();
    if (!model) return;
    const hidden = !!document.querySelector('#editor-pane.hidden');
    let at = ed.getPosition();
    if (hidden || (at.lineNumber === 1 && at.column === 1)) at = model.getFullModelRange().getEndPosition();
    const line = model.getLineContent(at.lineNumber);
    const before = at.column > 1 ? '\n\n' : '';
    const after = at.column <= line.length ? '\n\n' : '\n';
    const range = new window.monaco.Range(at.lineNumber, at.column, at.lineNumber, at.column);
    ed.executeEdits('embed', [{ range, text: before + text + after, forceMoveMarkers: true }]);
    if (!hidden) ed.focus();
  };
})();
