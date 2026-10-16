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
 *   7. Remote cursors (HackMD-style): everyone's caret and selection in their
 *      own color, with a name tag that shows while they move or type and on
 *      hover. Name and color come from data-codoc-user-* on the editor panel
 *      and travel in the Yjs awareness state. A caret is shown only while its
 *      owner is in the editor (focus), so readers don't park one somewhere.
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

  /* ================================================================== */
  /*  Remote cursors (HackMD-style)                                      */
  /* ================================================================== */

  const TAG_SHOW_MS = 2000; // a name tag stays up this long after its owner moves
  const HEX_COLOR = /^#[0-9a-fA-F]{6}$/;
  const FALLBACK_COLOR = "#1E88E5";

  const safeColor = (c) => (typeof c === "string" && HEX_COLOR.test(c) ? c : FALLBACK_COLOR);

  const rgba = (hex, alpha) => {
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  };

  /** Dark text on light colors, white text on the others. */
  const tagTextColor = (hex) => {
    const n = parseInt(hex.slice(1), 16);
    const lin = (v) => {
      const c = v / 255;
      return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    };
    const lum = 0.2126 * lin(n >> 16) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255);
    return lum > 0.3 ? "#111827" : "#ffffff";
  };

  const CURSOR_CSS = `
.yRemoteSelection { background-color: ${rgba(FALLBACK_COLOR, 0.25)}; }
.yRemoteSelectionHead {
  position: absolute; height: 100%; box-sizing: border-box; margin-left: -1px;
  border-left: 3px solid ${FALLBACK_COLOR}; color: ${FALLBACK_COLOR}; pointer-events: none;
}
/* A small flag on top of the caret: whose it is stays visible after the name tag fades. */
.yRemoteSelectionHead::before {
  content: ""; position: absolute; top: -3px; left: -5px; width: 7px; height: 7px;
  border-radius: 2px; background: currentColor;
}
.codoc-cursor-tag {
  padding: 0 6px; border-radius: 4px 4px 4px 0; white-space: nowrap; pointer-events: none;
  font: 600 11px/16px system-ui, -apple-system, "Segoe UI", sans-serif;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25); opacity: 0; transition: opacity 0.15s;
}
.codoc-cursor-tag.is-visible { opacity: 1; }
`;

  let cursorStyleEl = null;

  /** One stylesheet with every remote person's color, keyed by Yjs clientID. */
  const updateCursorStyles = (states, selfID) => {
    let css = CURSOR_CSS;
    states.forEach((state, id) => {
      if (id === selfID || !Number.isInteger(id)) return;
      const color = safeColor(state.user && state.user.color);
      css += `.yRemoteSelection-${id} { background-color: ${rgba(color, 0.25)}; }\n`;
      css += `.yRemoteSelectionHead-${id} { border-left-color: ${color}; color: ${color}; }\n`;
    });
    if (!cursorStyleEl || !cursorStyleEl.isConnected) {
      cursorStyleEl = document.createElement("style");
      cursorStyleEl.id = "codoc-remote-cursors";
      document.head.appendChild(cursorStyleEl);
    }
    if (cursorStyleEl.textContent !== css) cursorStyleEl.textContent = css;
  };

  /** A remote person's name tag: a Monaco content widget just above their caret. */
  class CursorTag {
    constructor(m, clientID) {
      this._m = m;
      this._id = "codoc.cursorTag." + clientID;
      this.node = document.createElement("div");
      this.node.className = "codoc-cursor-tag";
      this.position = null;
      this.active = false; // moved or typed in the last TAG_SHOW_MS
      this.hovered = false;
      this.timer = 0;
    }

    getId() { return this._id; }

    getDomNode() { return this.node; }

    getPosition() {
      if (!this.position) return null;
      const P = this._m.editor.ContentWidgetPositionPreference;
      return { position: this.position, preference: [P.ABOVE, P.BELOW] };
    }

    refresh() { this.node.classList.toggle("is-visible", this.active || this.hovered); }
  }

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

      /* --- remote cursors: caret/selection decorations + name tags --- */
      this._decorations = new Map();
      this._tags = new Map(); // editor -> Map(clientID -> CursorTag)
      this._spots = new Map(); // editor -> Map(clientID -> { head, start, end, user })
      this._rerenderDecorations = () => {
        if (awareness) updateCursorStyles(awareness.getStates(), this.doc.clientID);
        editors.forEach((editor) => {
          if (awareness && editor.getModel() === monacoModel) {
            const cur = this._decorations.get(editor) || [];
            const next = [];
            const spots = new Map();
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
                  spots.set(clientID, {
                    head: monacoModel.getPositionAt(hAbs.index),
                    start,
                    end,
                    user: state.user,
                  });
                }
              }
            });
            this._decorations.set(editor, editor.deltaDecorations(cur, next));
            this._spots.set(editor, spots);
            try {
              this._renderTags(editor, spots);
            } catch (err) {
              console.warn("[codoc-yjs] cursor tags:", err);
            }
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
      this._listeners = [];
      if (awareness) {
        editors.forEach((editor) => {
          // Our caret and selection, for the others: only while we are in the
          // editor. Someone who clicked below the text (to focus or to scroll)
          // and went on reading used to leave a caret parked at the end of the
          // document for everyone else.
          const publishSelection = () => {
            if (editor.getModel() !== monacoModel) return;
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
          };
          const hideSelection = () => {
            try { awareness.setLocalStateField("selection", null); } catch { /* ignore */ }
          };
          this._listeners.push(editor.onDidChangeCursorSelection(() => {
            if (editor.hasTextFocus()) publishSelection();
          }));
          this._listeners.push(editor.onDidFocusEditorText(publishSelection));
          this._listeners.push(editor.onDidBlurEditorText(hideSelection));
          // Hovering someone's caret or selection shows their name tag.
          this._listeners.push(editor.onMouseMove((e) => this._hover(editor, e.target && e.target.position)));
          this._listeners.push(editor.onMouseLeave(() => this._hover(editor, null)));
        });
        // Whoever moved or typed shows their name tag for a moment, as on HackMD.
        this._onAwarenessChange = ({ added, updated }) => {
          this._rerenderDecorations();
          added.concat(updated).forEach((id) => {
            if (id !== this.doc.clientID) this._flashTag(id);
          });
        };
        awareness.on("change", this._onAwarenessChange);
        this.awareness = awareness;
        // Show the cursors that are already there (e.g. after a view-mode switch).
        this._rerenderDecorations();
      }
    }

    _renderTags(editor, spots) {
      let tags = this._tags.get(editor);
      if (!tags) {
        tags = new Map();
        this._tags.set(editor, tags);
      }
      Array.from(tags.keys()).forEach((id) => {
        if (!spots.has(id)) this._removeTag(editor, tags, id);
      });
      spots.forEach(({ head, user }, id) => {
        const name = (user && typeof user.name === "string" && user.name.trim()) || "Guest";
        const color = safeColor(user && user.color);
        let tag = tags.get(id);
        const isNew = !tag;
        if (isNew) {
          tag = new CursorTag(this._m, id);
          tags.set(id, tag);
        }
        if (tag.node.textContent !== name) tag.node.textContent = name;
        tag.node.style.backgroundColor = color;
        tag.node.style.color = tagTextColor(color);
        const moved = !tag.position || tag.position.lineNumber !== head.lineNumber || tag.position.column !== head.column;
        tag.position = { lineNumber: head.lineNumber, column: head.column };
        if (isNew) {
          editor.addContentWidget(tag);
          this._flashTag(id); // a cursor that just appeared here shows its name too
        } else if (moved) {
          editor.layoutContentWidget(tag);
        }
      });
    }

    _removeTag(editor, tags, id) {
      const tag = tags.get(id);
      if (!tag) return;
      clearTimeout(tag.timer);
      try { editor.removeContentWidget(tag); } catch { /* editor already disposed */ }
      tags.delete(id);
    }

    _flashTag(clientID) {
      this._tags.forEach((tags) => {
        const tag = tags.get(clientID);
        if (!tag) return;
        tag.active = true;
        tag.refresh();
        clearTimeout(tag.timer);
        tag.timer = setTimeout(() => {
          tag.active = false;
          tag.refresh();
        }, TAG_SHOW_MS);
      });
    }

    _hover(editor, pos) {
      const tags = this._tags.get(editor);
      if (!tags) return;
      const spots = this._spots.get(editor) || new Map();
      let hit = null;
      if (pos) {
        spots.forEach(({ head, start, end }, id) => {
          if (hit !== null) return;
          const nearCaret = pos.lineNumber === head.lineNumber && Math.abs(pos.column - head.column) <= 1;
          const range = new this._m.Range(start.lineNumber, start.column, end.lineNumber, end.column);
          if (nearCaret || (!range.isEmpty() && range.containsPosition(pos))) hit = id;
        });
      }
      tags.forEach((tag, id) => {
        const hovered = id === hit;
        if (tag.hovered !== hovered) {
          tag.hovered = hovered;
          tag.refresh();
        }
      });
    }

    destroy() {
      try { this._monacoChangeHandler.dispose(); } catch {}
      try { this._monacoDisposeHandler.dispose(); } catch {}
      try { this.ytext.unobserve(this._ytextObserver); } catch {}
      try { this.doc.off("beforeAllTransactions", this._beforeTransaction); } catch {}
      this._listeners.forEach((l) => { try { l.dispose(); } catch {} });
      this._listeners = [];
      this._tags.forEach((tags, editor) => {
        Array.from(tags.keys()).forEach((id) => this._removeTag(editor, tags, id));
      });
      this._tags.clear();
      this._decorations.forEach((ids, editor) => { try { editor.deltaDecorations(ids, []); } catch {} });
      this._decorations.clear();
      if (this.awareness) {
        try { this.awareness.off("change", this._onAwarenessChange); } catch {}
        // This editor is gone: stop showing our caret to the others.
        try { this.awareness.setLocalStateField("selection", null); } catch {}
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
    // When behind a reverse proxy, CODOC_BACKEND_BASE_URL is the canonical
    // external URL (e.g. https://md.reflex-ddns.com).  Derive WebSocket URL
    // from it so the browser connects through nginx, not to localhost.
    const backendBase = window.CODOC_BACKEND_BASE_URL;
    if (backendBase) {
      const url = new URL(backendBase);
      const wsProt = url.protocol === "https:" ? "wss:" : "ws:";
      const portPart = url.port ? ":" + url.port : "";
      return `${wsProt}//${url.hostname}${portPart}/yjs`;
    }
    // Fallback: local dev (frontend on 3000 → backend on 8000).
    const { protocol, hostname } = window.location;
    const port = window.location.port;
    const wsProt = protocol === "https:" ? "wss:" : "ws:";
    const backendPort = port === "3000" ? "8000" : port;
    return `${wsProt}//${hostname}${backendPort ? ":" + backendPort : ""}/yjs`;
  };

  /**
   * True when the Monaco editor on the page holds the loaded content of
   * `docId` (see data_codoc_* attrs on editor_panel in codoc_in_md.py).
   * Guards against binding/seeding with the previous document's content
   * while Reflex is still loading the new one.
   */
  const editorReadyFor = (docId) => {
    const el = document.querySelector("[data-codoc-doc-id], [data_codoc_doc_id]");
    if (!el) return false;
    const attr = (name) => el.getAttribute("data-" + name) ?? el.getAttribute("data_" + name.replace(/-/g, "_"));
    return attr("codoc-doc-id") === docId && attr("codoc-loading") === "false";
  };

  /** This person's name and color for their cursor (data-codoc-user-* on the editor panel). */
  const readLocalUser = () => {
    const el = document.querySelector("[data-codoc-user-name], [data_codoc_user_name]");
    if (!el) return null;
    const attr = (name) => el.getAttribute("data-" + name) ?? el.getAttribute("data_" + name.replace(/-/g, "_"));
    const name = (attr("codoc-user-name") || "").trim();
    const color = attr("codoc-user-color") || "";
    return name && HEX_COLOR.test(color) ? { name, color } : null;
  };

  let localCursorStyleEl = null;

  /** Our own caret in our color as well, like the ring around our avatar. */
  const styleLocalCursor = (color) => {
    const css = `.monaco-editor .cursors-layer .cursor { background-color: ${color} !important; border-color: ${color} !important; }\n`;
    if (!localCursorStyleEl || !localCursorStyleEl.isConnected) {
      localCursorStyleEl = document.createElement("style");
      localCursorStyleEl.id = "codoc-local-cursor";
      document.head.appendChild(localCursorStyleEl);
    }
    if (localCursorStyleEl.textContent !== css) localCursorStyleEl.textContent = css;
  };

  /** Publish our name and color (again, when they change) with our cursor. */
  const syncLocalUser = () => {
    const user = readLocalUser();
    if (!user) return;
    styleLocalCursor(user.color);
    const awareness = provider && provider.awareness;
    if (!awareness) return;
    const cur = (awareness.getLocalState() || {}).user;
    if (!cur || cur.name !== user.name || cur.color !== user.color) {
      awareness.setLocalStateField("user", user);
    }
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
      // Tell the others we left, so our cursor disappears now rather than
      // after y-protocols' 30 s awareness timeout.
      try { provider.awareness.setLocalState(null); } catch { /* ignore */ }
      try { provider.destroy(); } catch { /* ignore */ }
      provider = null;
    }
    if (ydoc) {
      try { ydoc.destroy(); } catch { /* ignore */ }
      ydoc = null;
    }
    // Never leave the previous document's Y.Text reachable: tryRebind() would
    // otherwise bind it to the next document's editor while setup() is pending.
    window._codocYjs = null;
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
      // resyncInterval: now and then ask the room for anything we missed (the
      // relay forwards blindly, so a message can be lost while someone joins
      // or leaves), not only when connecting.
      const prov = new WsProvider(wsBase, docId, ydoc, { resyncInterval: 10000 });
      provider = prov;

      // The relay keeps no awareness state, so ask the others for theirs
      // (y-websocket's messageQueryAwareness); otherwise their cursors would
      // only appear when they next move, or after up to 15 s.
      prov.on("status", ({ status }) => {
        if (status !== "connected" || !prov.ws) return;
        try { prov.ws.send(new Uint8Array([3])); } catch { /* ignore */ }
      });
      syncLocalUser();

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

      // First-client seed and Monaco binding are deferred to tryRebind()
      // so that we always read from the freshly (re)mounted Monaco model
      // rather than a stale model that hasn't re-rendered yet.

      // Store for rebinding after Monaco remounts.
      window._codocYjs = { docId, ytext, provider, ydoc };
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
    if (setupBusy || !window._codocYjs || !currentDocId || !Y) return;
    if (window._codocYjs.docId !== currentDocId) return;
    if (!editorReadyFor(currentDocId)) return;
    const editor = getEditor();
    if (!editor) return;

    destroyBinding();

    const { ytext, provider: prov, ydoc: yd } = window._codocYjs;
    const model = editor.getModel();
    if (!model || !ytext) return;

    // Everyone's text has to be the same string for Yjs offsets to agree: Monaco
    // on Windows would otherwise type \r\n into a document the others keep as \n,
    // and every cursor after such a line would be off (or shown at the end).
    try {
      if (model.getEOL() !== "\n") model.setEOL(window.monaco.editor.EndOfLineSequence.LF);
    } catch { /* ignore */ }

    // Deferred first-client seed: if setup() could not seed because Monaco
    // was not mounted yet, do it now before creating the binding.
    if (ytext.length === 0 && yd) {
      const content = model.getValue();
      if (content) {
        yd.transact(() => { ytext.insert(0, content); });
      }
    }

    binding = new MonacoBinding(
      Y,
      window.monaco,
      ytext,
      model,
      new Set([editor]),
      prov ? prov.awareness : null,
    );
  };

  /* ================================================================== */
  /*  Polling loop – detect Monaco mount / doc changes                   */
  /* ================================================================== */

  const poll = () => {
    const docId = getDocId();
    if (!docId) {
      // Left the editor page (e.g. back to My Documents): disconnect.
      if (currentDocId && !setupBusy) destroyAll();
      return;
    }

    // Document changed → full re-setup.
    if (docId !== currentDocId) {
      setup(docId);
      return;
    }

    syncLocalUser();

    // Monaco remounts (view-mode switch, Reflex re-seeding the editor) create a
    // new model while the old binding lingers on the disposed one.
    const editor = getEditor();
    const model = editor ? editor.getModel() : null;
    if (model && (!binding || binding.monacoModel !== model)) {
      if (binding) destroyBinding();
      tryRebind();
    } else if (!model && binding) {
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

  // Say goodbye (cursor and room) when the tab closes or navigates away:
  // mobile browsers often skip beforeunload but do fire pagehide.
  window.addEventListener("beforeunload", destroyAll);
  window.addEventListener("pagehide", destroyAll);
})();
