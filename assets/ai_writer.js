(function () {
  // The AI in the editor (codoc_in_md/ai_state.py, components/ai_views.py), and what the page tells
  // the AI Hub's assistant.
  //
  // The writer works on the selection, or at the caret. A decoration keeps that place while the
  // others type, and what the person accepts goes in through Monaco as their own edit: everyone
  // gets it through Yjs, and Ctrl+Z takes it back.
  //
  // Cmd/Ctrl+I opens the writer and Alt+A the assistant; the keys are taken before Monaco sees them.

  const INIT_KEY = '__codocAiInit';
  if (window[INIT_KEY]) return;
  window[INIT_KEY] = true;

  const BEFORE = 3000; // characters around the selection that go with a request
  const AFTER = 1000;
  const PREVIEW = 600; // characters of the selection in what the assistant is told
  const WIDTH = 640;
  const GAP = 8;
  const CHIP_DELAY_MS = 250;

  const CSS = `
.codoc-ai-target { background: rgba(124, 58, 237, 0.14); }
.codoc-ai-chip {
  display: inline-flex; align-items: center; gap: 3px; padding: 1px 7px; border-radius: 6px; cursor: pointer; white-space: nowrap;
  font: 600 11px/18px system-ui, -apple-system, "Segoe UI", sans-serif; color: #fff; background: #7C3AED; border: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
.codoc-ai-chip:hover { background: #6D28D9; }
`;

  let target = null; // what the writer works on: {editor, model, ids, text}
  let watched = null; // the editor instance listened to (a view-mode switch makes a new one)
  let chip = null;
  let chipTimer = 0;
  let sized = null;

  function editor() {
    try {
      const eds = window.monaco && window.monaco.editor && window.monaco.editor.getEditors();
      return eds && eds.length > 0 ? eds[0] : null;
    } catch {
      return null;
    }
  }

  /** The editor, when the person can see it (Preview Only keeps one hidden). */
  function visibleEditor() {
    const ed = editor();
    return ed && ed.getModel() && ed.getDomNode() && ed.getDomNode().offsetParent ? ed : null;
  }

  function docId() {
    const parts = window.location.pathname.split('/').filter(Boolean);
    return parts.length >= 2 && parts[0] === 'doc' ? parts[1] : '';
  }

  function titleOf(model) {
    const m = model.getValue().match(/^\s{0,3}#{1,6}\s+(.+)$/m);
    return m ? m[1].trim() : '';
  }

  function panel() {
    return document.getElementById('ai-writer');
  }

  function clearTarget() {
    if (target) {
      try { target.model.deltaDecorations(target.ids, []); } catch { /* the model is gone */ }
    }
    target = null;
    if (sized) sized.disconnect();
    sized = null;
  }

  /** The writer goes under the selection, or over it, else wherever it fits. */
  function place() {
    const box = panel();
    if (!box || !target) return;
    const range = target.model.getDecorationRange(target.ids[0]);
    if (!range) return;
    const ed = target.editor;
    const host = ed.getDomNode().getBoundingClientRect();
    const line = ed.getOption(window.monaco.editor.EditorOption.lineHeight);
    const width = Math.min(WIDTH, host.width - 2 * GAP);
    const height = box.offsetHeight;
    const first = ed.getScrolledVisiblePosition(range.getStartPosition());
    const last = ed.getScrolledVisiblePosition(range.getEndPosition());
    const lowest = window.innerHeight - height - GAP;
    let top = host.top + (last ? last.top : 0) + line + GAP;
    if (top > lowest) {
      const above = host.top + (first ? first.top : 0) - height - GAP;
      top = above >= host.top ? above : lowest;
    }
    box.style.top = `${Math.max(GAP, Math.min(top, lowest))}px`;
    box.style.left = `${host.left + Math.max(GAP, Math.min((first ? first.left : 0), host.width - width - GAP))}px`;
    box.style.width = `${width}px`;
  }

  /** The writer just opened: it goes to its place, and the person's words go in its box. */
  function settle(tries) {
    const box = panel();
    if (!box) {
      if (tries > 0) requestAnimationFrame(() => settle(tries - 1));
      return;
    }
    place();
    if (window.ResizeObserver) {
      if (sized) sized.disconnect();
      sized = new ResizeObserver(place);
      sized.observe(box);
    }
    const input = document.getElementById('ai-request');
    if (input) input.focus();
  }

  /** Marks the selection for the writer: what it sends back to the Reflex state. */
  function take() {
    const ed = visibleEditor();
    if (!ed) return null;
    const model = ed.getModel();
    const selection = ed.getSelection();
    clearTarget();
    const text = model.getValue();
    const start = model.getOffsetAt(selection.getStartPosition());
    const end = model.getOffsetAt(selection.getEndPosition());
    const selected = text.slice(start, end);
    const ids = model.deltaDecorations([], [{
      range: selection,
      options: { className: 'codoc-ai-target', stickiness: window.monaco.editor.TrackedRangeStickiness.NeverGrowsWhenTypingAtEdges },
    }]);
    target = { editor: ed, model, ids, text: selected };
    const lines = selection.endLineNumber - selection.startLineNumber + 1;
    settle(120);
    return {
      selected,
      before: text.slice(Math.max(0, start - BEFORE), start),
      after: text.slice(end, end + AFTER),
      title: titleOf(model),
      where: selected
        ? (lines > 1 ? `${lines} lines selected` : `${selected.length} characters selected`)
        : `At the caret, line ${selection.positionLineNumber}`,
    };
  }

  function open() {
    if (panel()) {
      const input = document.getElementById('ai-request');
      if (input) input.focus();
      return;
    }
    const button = document.getElementById('ai-writer-open');
    if (button && visibleEditor()) button.click();
  }

  /** Puts what the person accepted in the document, as their own edit: false when it can't be,
   * because the text it replaces is no longer what the AI saw. */
  function apply(text, below) {
    if (!target || target.editor !== editor() || target.editor.getModel() !== target.model) return false;
    const { editor: ed, model, ids } = target;
    const range = model.getDecorationRange(ids[0]);
    if (!range || model.getValueInRange(range) !== target.text) return false;
    const at = below ? window.monaco.Range.fromPositions(range.getEndPosition()) : range;
    ed.pushUndoStop();
    ed.executeEdits('ai', [{ range: at, text: below ? `\n\n${text}` : text, forceMoveMarkers: true }]);
    ed.pushUndoStop();
    clearTarget();
    ed.focus();
    return true;
  }

  function drop() {
    const ed = target && target.editor;
    clearTarget();
    if (!ed) return;
    ed.focus();
    chipTimer = setTimeout(() => showChip(ed), CHIP_DELAY_MS); // the selection is still there
  }

  /* ---- the small button on a selection ---- */

  class Chip {
    constructor(ed) {
      this.position = null;
      this.node = document.createElement('button');
      this.node.type = 'button';
      this.node.id = 'ai-chip';
      this.node.className = 'codoc-ai-chip';
      this.node.title = 'Ask the AI about this text (Cmd/Ctrl+I)';
      this.node.textContent = '✦ AI';
      this.node.addEventListener('mousedown', (e) => e.preventDefault());
      this.node.addEventListener('click', () => { hideChip(); open(); });
      this.suppressMouseDown = true;
      this.editor = ed;
    }

    getId() { return 'codoc.aiChip'; }

    getDomNode() { return this.node; }

    getPosition() {
      if (!this.position) return null;
      const P = window.monaco.editor.ContentWidgetPositionPreference;
      return { position: this.position, preference: [P.BELOW, P.ABOVE] };
    }
  }

  function hideChip() {
    clearTimeout(chipTimer);
    if (!chip) return;
    try { chip.editor.removeContentWidget(chip); } catch { /* editor disposed */ }
    chip = null;
  }

  function showChip(ed) {
    const selection = ed.getSelection();
    hideChip();
    if (!selection || selection.isEmpty() || !ed.hasTextFocus() || panel() || !document.getElementById('ai-writer-open')) return;
    chip = new Chip(ed);
    chip.position = selection.getPosition(); // where the selecting ended: the mouse is there
    ed.addContentWidget(chip);
  }

  function watch(ed) {
    watched = ed;
    ed.onDidChangeCursorSelection(() => {
      hideChip();
      chipTimer = setTimeout(() => showChip(ed), CHIP_DELAY_MS);
    });
    ed.onDidBlurEditorText(hideChip);
    ed.onDidScrollChange(place);
  }

  /* ---- what the assistant is told ---- */

  // The AI Hub's dialogs ask the page what it shows (reflex_ddns_auth.intent): "this" and "the
  // selection" in what the person writes there mean this.
  window.__ddnsContext = () => {
    const id = docId();
    const ed = editor();
    const model = ed && ed.getModel();
    if (!id || !model) return null;
    const words = [`The document "${titleOf(model)}" (room ${id}) has ${model.getLineCount()} lines.`];
    const selection = ed.getSelection();
    if (selection && !selection.isEmpty()) {
      const text = model.getValueInRange(selection);
      const shown = text.length > PREVIEW ? `${text.slice(0, PREVIEW)}…` : text;
      words.push(`The selection is lines ${selection.startLineNumber} to ${selection.endLineNumber}: ${shown}`);
    } else if (selection) {
      words.push(`The caret is on line ${selection.positionLineNumber}: ${model.getLineContent(selection.positionLineNumber).slice(0, PREVIEW)}`);
    }
    return { text: words.join(' ') };
  };

  /* ---- keys ---- */

  document.addEventListener('keydown', (e) => {
    const typing = e.isComposing || e.keyCode === 229;
    const button = (id) => document.getElementById(id);
    if (panel()) {
      if (e.key === 'Escape' && !typing) {
        const out = button('ai-stop') || button('ai-discard') || button('ai-close');
        if (out) { e.preventDefault(); e.stopPropagation(); out.click(); }
        return;
      }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey) && button('ai-accept')) {
        e.preventDefault();
        e.stopPropagation();
        button('ai-accept').click();
        return;
      }
      // Enter ending a composition is not a request yet (Safari sends it on to the form).
      if (e.key === 'Enter' && typing && e.target === button('ai-request')) e.preventDefault();
    }
    if (!docId()) return;
    if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.code === 'KeyI' && (panel() || visibleEditor())) {
      e.preventDefault();
      e.stopPropagation();
      open();
    } else if (e.altKey && !e.metaKey && !e.ctrlKey && e.code === 'KeyA' && button('ai-assist')) {
      e.preventDefault();
      e.stopPropagation();
      button('ai-assist').click();
    }
  }, true);

  /* ---- start ---- */

  window.codocAi = { open, take, apply, drop };

  const style = document.createElement('style');
  style.id = 'codoc-ai-style';
  style.textContent = CSS;
  document.head.appendChild(style);

  window.addEventListener('resize', place);
  setInterval(() => {
    const ed = editor();
    if (ed && ed !== watched) watch(ed);
    // The editor it worked on went (a view-mode switch): so did the place the answer was for.
    if (target && ed !== target.editor && document.getElementById('ai-close')) document.getElementById('ai-close').click();
  }, 600);
})();
