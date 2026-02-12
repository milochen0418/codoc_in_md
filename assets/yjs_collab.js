/**
 * Yjs collaborative editing integration for CoDoc in MD.
 *
 * Strategy (Plan A – pure frontend JS injection):
 *   1. Load yjs + y-websocket from CDN (esm.sh).
 *   2. Vendor MonacoBinding (adapted from y-monaco@0.1.6, MIT © Kevin Jahns)
 *      so we can reference the already-loaded `window.monaco` rather than
 *      pulling a second copy of monaco-editor from the CDN.
 *   3. Detect Monaco editor mount via polling.
 *   4. Create a Y.Doc per document room and connect via WebsocketProvider
 *      to the backend relay at /yjs/{doc_id}.
 *   5. Bind Y.Text ↔ Monaco model via MonacoBinding.
 *   6. Monaco's on_change (handled by reflex-monaco) naturally fires for
 *      both local and remote edits, keeping the Reflex preview in sync.
 *
 * "First client" problem:
 *   The relay server is stateless – it only forwards messages.  When the
 *   very first client connects there is nobody to sync from, so the
 *   Y.Text starts empty.  We detect this (after a short timeout) and
 *   seed Y.Text from the Monaco model's current value (which was loaded
 *   from the Reflex state / DOCUMENTS_STORE).
 */
(() => {
  /* ================================================================== */
  /*  Vendored helpers (lib0 mutex)                                      */
  /* ================================================================== */
  const createMutex = () => {
    let token = true;
    return (f, g) => {
      if (token) {
        token = false;
        try { f(); } finally { token = true; }
      } else if (g !== undefined) {
        g();
      }
    };
  };

  /* ================================================================== */
  /*  Vendored MonacoBinding (y-monaco@0.1.6, MIT)                       */
  /*  Adapted: uses `window.monaco` & passed-in `Y` instead of imports. */
  /* ================================================================== */

  class RelativeSelection {
    constructor(start, end, direction) {
      this.start = start;
      this.end = end;
      this.direction = direction;
    }
  }

  const _createRelSel = (Y, editor, monacoModel, type) => {
    const sel = editor.getSelection();
    if (sel !== null) {
      const startPos = sel.getStartPosition();
      const endPos = sel.getEndPosition();
      const start = Y.createRelativePositionFromTypeIndex(type, monacoModel.getOffsetAt(startPos));
      const end = Y.createRelativePositionFromTypeIndex(type, monacoModel.getOffsetAt(endPos));
      return new RelativeSelection(start, end, sel.getDirection());
    }
    return null;
  };

  const _relSelToMonaco = (Y, m, editor, type, relSel, doc) => {
    const start = Y.createAbsolutePositionFromRelativePosition(relSel.start, doc);
    const end = Y.createAbsolutePositionFromRelativePosition(relSel.end, doc);
    if (start !== null && end !== null && start.type === type && end.type === type) {
      const model = editor.getModel();
      const sp = model.getPositionAt(start.index);
      const ep = model.getPositionAt(end.index);
      return m.Selection.createWithDirection(sp.lineNumber, sp.column, ep.lineNumber, ep.column, relSel.direction);
    }
    return null;
  };

  /**
   * Bi-directional binding between a Y.Text and a Monaco ITextModel.
   *
   * @param {object}  Y          – the Yjs module namespace
   * @param {object}  m          – `window.monaco` namespace
   * @param {Y.Text}  ytext      – shared text type
   * @param {object}  monacoModel
   * @param {Set}     editors    – editor instances (for cursor sync)
   * @param {object?} awareness  – y-protocols Awareness instance
   */
  class MonacoBinding {
    constructor(Y, m, ytext, monacoModel, editors, awareness) {
      if (!editors) editors = new Set();
      this.doc = ytext.doc;
      this.ytext = ytext;
      this.monacoModel = monacoModel;
      this.editors = editors;
      this.mux = createMutex();
      this._savedSelections = new Map();
      this._Y = Y;
      this._m = m;

      /* --- save cursor positions before transactions --- */
      this._beforeTransaction = () => {
        this.mux(() => {
          this._savedSelections = new Map();
          editors.forEach((ed) => {
            if (ed.getModel() === monacoModel) {
              const r = _createRelSel(Y, ed, monacoModel, ytext);
              if (r) this._savedSelections.set(ed, r);
            }
          });
        });
      };
      this.doc.on("beforeAllTransactions", this._beforeTransaction);

      /* --- remote cursor decorations --- */
      this._decorations = new Map();
      this._rerenderDecorations = () => {
        editors.forEach((editor) => {
          if (awareness && editor.getModel() === monacoModel) {
            const cur = this._decorations.get(editor) || [];
            const next = [];
            awareness.getStates().forEach((state, clientID) => {
              if (
                clientID !== this.doc.clientID &&
                state.selection != null &&
                state.selection.anchor != null &&
                state.selection.head != null
              ) {
                const aAbs = Y.createAbsolutePositionFromRelativePosition(state.selection.anchor, this.doc);
                const hAbs = Y.createAbsolutePositionFromRelativePosition(state.selection.head, this.doc);
                if (aAbs && hAbs && aAbs.type === ytext && hAbs.type === ytext) {
                  let start, end, after, before;
                  if (aAbs.index < hAbs.index) {
                    start = monacoModel.getPositionAt(aAbs.index);
                    end = monacoModel.getPositionAt(hAbs.index);
                    after = "yRemoteSelectionHead yRemoteSelectionHead-" + clientID;
                    before = null;
                  } else {
                    start = monacoModel.getPositionAt(hAbs.index);
                    end = monacoModel.getPositionAt(aAbs.index);
                    after = null;
                    before = "yRemoteSelectionHead yRemoteSelectionHead-" + clientID;
                  }
                  next.push({
                    range: new m.Range(start.lineNumber, start.column, end.lineNumber, end.column),
                    options: {
                      className: "yRemoteSelection yRemoteSelection-" + clientID,
                      afterContentClassName: after,
                      beforeContentClassName: before,
                    },
                  });
                }
              }
            });
            this._decorations.set(editor, editor.deltaDecorations(cur, next));
          } else {
            this._decorations.delete(editor);
          }
        });
      };

      /* --- Y.Text → Monaco --- */
      this._ytextObserver = (event) => {
        this.mux(() => {
          let index = 0;
          event.delta.forEach((op) => {
            if (op.retain !== undefined) {
              index += op.retain;
            } else if (op.insert !== undefined) {
              const pos = monacoModel.getPositionAt(index);
              const range = new m.Selection(pos.lineNumber, pos.column, pos.lineNumber, pos.column);
              monacoModel.applyEdits([{ range, text: /** @type {string} */ (op.insert) }]);
              index += op.insert.length;
            } else if (op.delete !== undefined) {
              const pos = monacoModel.getPositionAt(index);
              const endPos = monacoModel.getPositionAt(index + op.delete);
              const range = new m.Selection(pos.lineNumber, pos.column, endPos.lineNumber, endPos.column);
              monacoModel.applyEdits([{ range, text: "" }]);
            }
          });
          this._savedSelections.forEach((rsel, ed) => {
            const sel = _relSelToMonaco(Y, m, ed, ytext, rsel, this.doc);
            if (sel) ed.setSelection(sel);
          });
        });
        this._rerenderDecorations();
      };
      ytext.observe(this._ytextObserver);

      /* --- initial value reconciliation --- */
      {
        const ytv = ytext.toString();
        if (monacoModel.getValue() !== ytv) {
          monacoModel.setValue(ytv);
        }
      }

      /* --- Monaco → Y.Text --- */
      this._monacoChangeHandler = monacoModel.onDidChangeContent((event) => {
        this.mux(() => {
          this.doc.transact(() => {
            event.changes
              .sort((a, b) => b.rangeOffset - a.rangeOffset)
              .forEach((change) => {
                ytext.delete(change.rangeOffset, change.rangeLength);
                ytext.insert(change.rangeOffset, change.text);
              });
          }, this);
        });
      });

      this._monacoDisposeHandler = monacoModel.onWillDispose(() => {
        this.destroy();
      });

      /* --- awareness (cursor broadcast) --- */
      if (awareness) {
        editors.forEach((editor) => {
          editor.onDidChangeCursorSelection(() => {
            if (editor.getModel() === monacoModel) {
              const sel = editor.getSelection();
              if (!sel) return;
              let anchor = monacoModel.getOffsetAt(sel.getStartPosition());
              let head = monacoModel.getOffsetAt(sel.getEndPosition());
              if (sel.getDirection() === m.SelectionDirection.RTL) {
                const tmp = anchor; anchor = head; head = tmp;
              }
              awareness.setLocalStateField("selection", {
                anchor: Y.createRelativePositionFromTypeIndex(ytext, anchor),
                head: Y.createRelativePositionFromTypeIndex(ytext, head),
              });
            }
          });
          awareness.on("change", this._rerenderDecorations);
        });
        this.awareness = awareness;
      }
    }

    destroy() {
      this._monacoChangeHandler.dispose();
      this._monacoDisposeHandler.dispose();
      this.ytext.unobserve(this._ytextObserver);
      this.doc.off("beforeAllTransactions", this._beforeTransaction);
      if (this.awareness) {
        this.awareness.off("change", this._rerenderDecorations);
      }
    }
  }

  /* ================================================================== */
  /*  Module-level state                                                 */
  /* ================================================================== */
  let ydoc = null;
  let provider = null;
  let binding = null;
  let currentDocId = null;
  let setupBusy = false;
  let setupErrors = 0;
  const MAX_SETUP_ERRORS = 5;

  // Cached CDN module references (loaded once).
  let Y = null;
  let WsProvider = null;

  /* ================================================================== */
  /*  Helpers                                                            */
  /* ================================================================== */

  const getDocId = () => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    if (parts.length >= 2 && parts[0] === "doc") return parts[1];
    return "";
  };

  /** Derive the WebSocket URL for the Yjs relay on the backend. */
  const getWsBase = () => {
    const { protocol, hostname } = window.location;
    const port = window.location.port;
    const wsProt = protocol === "https:" ? "wss:" : "ws:";
    // Dev: frontend on 3000 → backend on 8000.
    const backendPort = port === "3000" ? "8000" : port;
    return `${wsProt}//${hostname}${backendPort ? ":" + backendPort : ""}/yjs`;
  };

  /** Return the first Monaco ICodeEditor instance, or null. */
  const getEditor = () => {
    try {
      const eds = window.monaco && window.monaco.editor && window.monaco.editor.getEditors();
      return eds && eds.length > 0 ? eds[0] : null;
    } catch {
      return null;
    }
  };

  /* ================================================================== */
  /*  Lifecycle                                                          */
  /* ================================================================== */

  const destroyBinding = () => {
    if (binding) {
      try { binding.destroy(); } catch { /* ignore */ }
      binding = null;
    }
  };

  const destroyAll = () => {
    destroyBinding();
    if (provider) {
      try { provider.destroy(); } catch { /* ignore */ }
      provider = null;
    }
    if (ydoc) {
      try { ydoc.destroy(); } catch { /* ignore */ }
      ydoc = null;
    }
    currentDocId = null;
  };

  /** Load yjs + y-websocket from esm.sh (cached after first call). */
  const ensureModules = async () => {
    if (Y) return;
    const CDN = "https://esm.sh";
    const YJS_VER = "yjs@13.6.18";
    const [yMod, wsMod] = await Promise.all([
      import(`${CDN}/${YJS_VER}`),
      import(`${CDN}/y-websocket@2.0.4?deps=${YJS_VER}`),
    ]);
    Y = yMod;
    WsProvider = wsMod.WebsocketProvider;
  };

  /**
   * Main setup: create Y.Doc, connect WebSocket, bind to Monaco.
   *
   * Designed to be re-entrant – if called while another setup is running it
   * short-circuits.  If called with a different doc_id it cleans up first.
   */
  const setup = async (docId) => {
    if (setupBusy) return;
    if (currentDocId === docId && ydoc) return; // already active
    if (setupErrors >= MAX_SETUP_ERRORS) return; // stop retrying
    setupBusy = true;

    try {
      destroyAll();
      await ensureModules();

      currentDocId = docId;
      ydoc = new Y.Doc();
      const ytext = ydoc.getText("monaco");

      // Connect to the backend Yjs relay.
      const wsBase = getWsBase();
      provider = new WsProvider(wsBase, docId, ydoc);

      // Wait for sync (another client responds) or timeout (we're first).
      await new Promise((resolve) => {
        if (provider.synced) { resolve(); return; }
        const onSync = (ev) => {
          if (ev && ev.synced !== undefined ? ev.synced : true) {
            provider.off("synced", onSync);
            resolve();
          }
        };
        provider.on("synced", onSync);
        setTimeout(() => { provider.off("synced", onSync); resolve(); }, 2000);
      });

      // First-client seed: if Y.Text is still empty, populate from Monaco.
      const editor = getEditor();
      if (editor && ytext.length === 0) {
        const model = editor.getModel();
        if (model) {
          const content = model.getValue();
          if (content) {
            ydoc.transact(() => { ytext.insert(0, content); });
          }
        }
      }

      // Bind Y.Text ↔ Monaco (using vendored MonacoBinding).
      if (editor) {
        const model = editor.getModel();
        if (model) {
          binding = new MonacoBinding(
            Y,
            window.monaco,
            ytext,
            model,
            new Set([editor]),
            provider.awareness,
          );
        }
      }

      // Store for rebinding after Monaco remounts.
      window._codocYjs = { ytext, provider };
      setupErrors = 0; // success resets error counter
    } catch (err) {
      setupErrors++;
      console.error("[codoc-yjs] setup error (" + setupErrors + "/" + MAX_SETUP_ERRORS + "):", err);
    } finally {
      setupBusy = false;
    }
  };

  /** Re-create the MonacoBinding after Monaco remounts (e.g. view-mode switch). */
  const tryRebind = () => {
    if (!window._codocYjs || !currentDocId || !Y) return;
    const editor = getEditor();
    if (!editor) return;

    destroyBinding();

    const { ytext, provider: prov } = window._codocYjs;
    const model = editor.getModel();
    if (model && ytext) {
      binding = new MonacoBinding(
        Y,
        window.monaco,
        ytext,
        model,
        new Set([editor]),
        prov ? prov.awareness : null,
      );
    }
  };

  /* ================================================================== */
  /*  Polling loop – detect Monaco mount / doc changes                   */
  /* ================================================================== */

  const poll = () => {
    const docId = getDocId();
    if (!docId) return;

    // Document changed → full re-setup.
    if (docId !== currentDocId) {
      setup(docId);
      return;
    }

    const editor = getEditor();
    if (editor && !binding) {
      tryRebind();
    } else if (!editor && binding) {
      destroyBinding();
    }
  };

  const start = () => {
    setInterval(poll, 600);
    // Immediate first check.
    poll();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  window.addEventListener("beforeunload", destroyAll);
})();
