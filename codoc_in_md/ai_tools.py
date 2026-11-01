"""What the AI Hub's assistant may do with documents: tools (``reflex_ddns_auth.tools``) that read
them, and tools that change them.

``room`` is the document's id (``/doc/<room>``); the assistant passes the one it was opened from.

The AI works like one more person on a document: it shows among the people there while it works,
and its change reaches everyone's editor the way typing does (``yjs_ws.visit``), merged with what
they type at that moment, or goes straight into the saved document when nobody has it open. What
it wrote stays marked in its color for a moment. A tool that changes a document is a ``danger``
tool: the AI Hub runs it only after the person's Accept; and because Ctrl+Z doesn't reach another
person's edit, a note on the document can take the change back (``ai_edits``).
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import uuid
from typing import Literal, Optional

import reflex as rx
from reflex_ddns_auth.intent.protocol import app_url
from reflex_ddns_auth.tools import ToolContext, tool

from . import ai, ai_edits, yjs_ws
from .state import DOCUMENTS_STORE, PRESENCE_TTL, Document, SharedState, _extract_title

ROOM = "The document's id, as in /doc/<id>: the one the assistant was opened from (md.list_documents lists them)."
SUMMARY = "One sentence, in the person's language, saying what this does: they read it before they accept."

# What one read may return: a long document, not a book.
READ_MAX_CHARS = 60_000
LIST_MAX = 50
# The AI's color and picture, and how long what it wrote stays marked for the people on the document.
AI_COLOR = "#7C3AED"
AI_PICTURE = "https://api.dicebear.com/9.x/initials/svg?seed=AI&backgroundColor=7c3aed"
MARK_SECONDS = 6.0
# How long a tab that is reconnecting gets to come back before a change is refused.
RECONNECT_WAIT = 3.0

GUIDE = """\
This is a shared Markdown editor in the style of HackMD; each document is a room (/doc/<room>). People may be writing in it right now, and they see what you do at once.
Reading:
- md_read: the document's text, or some of its lines. Never guess what a document says: read it before you answer from it, summarise it or change it.
- md_list_documents: the documents; `search` finds words in them.
Changing: do the change yourself with these tools rather than telling the person what to type. Each call waits for the person's Accept in this chat, and they can take an accepted call back in one click: put all the changes of one request in one call.
- md_append: adds text at the end of the document (or at its start). Anything that goes "at the end" goes through this.
- md_edit: replaces pieces of text where they are. Copy each `find` exactly from md_read, long enough to be found once; to add text next to a line, find that line and repeat it in `replace`. Change only what the request is about: others may be writing elsewhere in the document.
- md_rewrite: replaces the whole document, for a request about all of it, such as a translation.
- md_create: makes a new document; don't use it for a change to this one.
- Every change has a summary: one sentence, in the person's language, saying what it does.
- When the person rejects a change, nothing changed: ask what they want instead, don't try the same again.
- A message may begin with what the person's page shows (the document, the caret's line, the selection): "this", "here" and "the selection" mean those. Read those lines before you change them.
Keep the language the document is written in, unless asked otherwise. Write Markdown; besides GitHub's (tables, task lists, code), this editor shows:
- [TOC] on a line of its own: a table of contents.
- :::info, :::success, :::warning, :::danger, each ending with a line :::, are coloured boxes; :::spoiler Title is a section that folds.
- Math: $a^2$ in a line, $$ on lines of their own around a block.
- Diagrams, as fenced code blocks of the language mermaid, sequence, flow, graphviz, plantuml, vega (a JSON spec), abc (music) or csvpreview (a table from CSV).
- A code fence's language with = shows line numbers (```python=); with ! it wraps long lines.
- ==highlight==, ++underline++, ~sub~, ^sup^, and emoji such as :smile:.
- Pictures with a size: ![](url =200x). Embeds on a line of their own: {%youtube id %}, {%vimeo id %}, {%pdf url %}, {%gist user/id %}.
- {%grid <book> ... %} lines show a ReflexGrid workbook: keep them as they are."""


def _who(ctx: ToolContext) -> str:
    """How the AI shows on a document: the AI Hub's own assistant and talking AI are just "AI",
    an agent connected with a token of its own goes by that token's name."""
    return f"AI · {ctx.user}" if ctx.user and ctx.user not in ("assistant", "companion") else "AI"


def _show_ai(ctx: ToolContext, room: str) -> None:
    """The AI is on the document: among its people, until it has stopped for a moment."""
    key = "ai-" + hashlib.sha1(ctx.user.encode("utf-8")).hexdigest()[:8]
    now = time.time()
    SharedState.update_user(
        room,
        key,
        {"id": key, "name": _who(ctx), "color": AI_COLOR, "last_seen": now, "avatar_url": AI_PICTURE, "joined_at": now, "doc_color": ""},
    )


async def _document(room: str) -> Document:
    """The saved document (else ValueError, for the AI to read)."""
    room = (room or "").strip()
    doc = await asyncio.to_thread(DOCUMENTS_STORE.get, room) if room else None
    if doc is None:
        raise ValueError(f"there is no document {room!r}: md.list_documents lists them, md.create makes one")
    return doc


def _people_on(room: str) -> bool:
    """Whether a tab reports being on the document (presence, which outlasts a dropped socket)."""
    now = time.time()
    return any(not token.startswith("ai-") and now - u["last_seen"] < PRESENCE_TTL for token, u in SharedState.users.get(room, {}).items())


async def _visit(room: str, doc: Document) -> Optional[yjs_ws.Visitor]:
    """Joins the document's room. Nobody's tab being there means the saved document is all there
    is, unless someone is on the document and their socket is coming back (the server restarted):
    a change saved now would be overwritten from that tab, so it waits, and then refuses."""
    deadline = time.monotonic() + RECONNECT_WAIT
    while not yjs_ws.has_tabs(room) and _people_on(room) and time.monotonic() < deadline:
        await asyncio.sleep(0.2)
    if not yjs_ws.has_tabs(room) and _people_on(room):
        raise ValueError("the people on this document are reconnecting: try again in a moment")
    try:
        return await yjs_ws.visit(room, wanted=bool(doc["content"]))
    except TimeoutError as e:
        raise ValueError("the tabs on this document didn't answer: try again in a moment") from e


def _save(room: str, text: str) -> None:
    doc = DOCUMENTS_STORE.get(room)
    if doc is None:
        return
    doc.update(content=text, title=_extract_title(text), updated_at=time.time(), version=doc["version"] + 1)
    DOCUMENTS_STORE[room] = doc


async def _apply(room: str, doc: Document, who: str, pieces_of) -> tuple[str, list[ai_edits.Piece]]:
    """Makes a change: ``pieces_of(text)`` says what it is, for the text as it is right now in
    everyone's editors, or saved. Answers that text and the pieces (none: nothing to change)."""
    visitor = await _visit(room, doc)
    marked = False
    try:
        text = visitor.value if visitor else doc["content"].replace("\r\n", "\n")
        pieces = pieces_of(text)
        if not pieces:
            return text, []
        # Saved first: the tabs save what they get, so whatever a tab saves after this is newer.
        await asyncio.to_thread(_save, room, ai_edits.spliced(text, pieces))
        if visitor:
            await visitor.show_as(who, AI_COLOR)
            await visitor.replace(pieces)
            marked = True
        return text, pieces
    finally:
        if visitor:
            visitor.leave(MARK_SECONDS if marked else 0.0)


async def _change(ctx: ToolContext, room: str, summary: str, pieces_of) -> dict:
    """A change of the AI's, remembered for the note that takes it back."""
    doc = await _document(room)
    _show_ai(ctx, room)
    text, pieces = await _apply(room, doc, _who(ctx), pieces_of)
    if not pieces:
        return {"room": room, "changed": 0, "message": "The document already says this: nothing changed."}
    after = ai_edits.spliced(text, pieces)
    ai_edits.remember(room, summary.strip() or "Changed the document", _who(ctx), text, pieces)
    return {"room": room, "changed": len(pieces), "lines": after.count("\n") + 1, "first_changed_line": text.count("\n", 0, pieces[0][0]) + 1}


async def take_back(room: str, change_id: str) -> str:
    """Takes a change of the AI's back: "" when it is done, else why it can't be (the text was
    changed there since). The ``Undo`` on the note."""
    change = ai_edits.find(room, change_id)
    if change is None:
        return "This change can't be taken back any more."
    doc = await _document(room)
    undone = False

    def pieces_of(text: str) -> list[ai_edits.Piece]:
        nonlocal undone
        pieces = ai_edits.undoing(text, change.spots)
        undone = pieces is not None
        return pieces or []

    await _apply(room, doc, change.who, pieces_of)
    if not undone:
        return "The text there was changed after the AI's change, so it can't be taken back: change it by hand."
    ai_edits.forget(room, change_id)
    return ""


async def guide(ctx: ToolContext) -> str:
    """How to work with documents here, and what Markdown this editor shows: read this first."""
    return GUIDE


async def list_documents(ctx: ToolContext, search: str = "") -> dict:
    """The documents, the most recently changed first: their ids ("room"), titles and creators."""
    docs = await asyncio.to_thread(DOCUMENTS_STORE.values)
    words = search.strip().lower()
    found = [d for d in docs if not words or words in d["title"].lower() or words in d["content"].lower()]
    return {
        "total": len(found),
        "documents": [
            {
                "room": d["doc_id"],
                "title": d["title"],
                "created_by": d["created_by_name"],
                "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime(d["updated_at"])),
                "words": len(d["content"].split()),
            }
            for d in found[:LIST_MAX]
        ],
    }


async def read(ctx: ToolContext, room: str, from_line: int = 1, to_line: int = 0) -> dict:
    """The document's text as it is now, or its lines ``from_line`` to ``to_line``."""
    doc = await _document(room)
    lines = doc["content"].replace("\r\n", "\n").split("\n")
    first = max(1, from_line)
    last = min(len(lines), to_line) if to_line > 0 else len(lines)
    if first > len(lines) or first > last:
        raise ValueError(f"the document has {len(lines)} lines: lines {from_line} to {to_line} aren't in it")
    out = {"room": doc["doc_id"], "title": doc["title"], "lines": len(lines), "from_line": first, "to_line": last}
    text = "\n".join(lines[first - 1 : last])
    if len(text) > READ_MAX_CHARS:
        text = text[:READ_MAX_CHARS]
        end = first + text.count("\n")
        out.update(to_line=end, more=f"This is as much as one read gives: read on with from_line={end}.")
    return {**out, "text": text}


async def append(ctx: ToolContext, room: str, summary: str, text: str, at: Literal["end", "start"] = "end") -> dict:
    """Adds text at the end of the document (or at its start), on lines of its own."""
    if not text.strip():
        raise ValueError("text is empty: there is nothing to add")
    return await _change(ctx, room, summary, lambda now: ai_edits.placed(now, text, at))


async def edit(ctx: ToolContext, room: str, summary: str, edits: list[dict]) -> dict:
    """Replaces pieces of the document's text where they are, all of them or none. Each is {"find":
    text copied exactly from the document, long enough to be found once, "replace": what it
    becomes}. To add something at the end, use md.append."""
    return await _change(ctx, room, summary, lambda text: ai_edits.located(text, edits))


async def rewrite(ctx: ToolContext, room: str, summary: str, text: str) -> dict:
    """Replaces the whole document, for a request about all of it (a translation, say)."""
    if not text.strip():
        raise ValueError("text is empty: a document isn't emptied this way")
    return await _change(ctx, room, summary, lambda now: ai_edits.placed(now, text, "whole"))


async def create(ctx: ToolContext, title: str, text: str = "") -> dict:
    """Makes a new document and returns its id ("room") and address."""
    title = " ".join(title.split()) or "Untitled"
    content = text if text.lstrip().startswith("#") else f"# {title}\n\n{text}".rstrip() + "\n"
    doc_id = uuid.uuid4().hex[:8]
    doc = Document(
        doc_id=doc_id,
        title=_extract_title(content),
        content=content,
        updated_at=time.time(),
        version=1,
        created_by_email="",
        created_by_name=_who(ctx),
    )
    await asyncio.to_thread(DOCUMENTS_STORE.__setitem__, doc_id, doc)
    return {"room": doc_id, "title": doc["title"], "address": f"{app_url(ai.APP)}/doc/{doc_id}"}


def register(app: rx.App) -> None:
    """Offers the document tools on ``app``'s backend."""
    tool(app, "md.guide", title="How to work with documents here")(guide)
    tool(
        app,
        "md.list_documents",
        title="List the documents",
        params={"search": "Words to look for in their titles and text."},
    )(list_documents)
    tool(
        app,
        "md.read",
        title="Read a document",
        params={"room": ROOM, "from_line": "The first line to read, from 1.", "to_line": "The last line to read; 0: to the end."},
    )(read)
    tool(
        app,
        "md.append",
        title="Add text to a document",
        kind="danger",
        params={"room": ROOM, "summary": SUMMARY, "text": "The Markdown to add.", "at": "Where it goes: at the end, or at the start."},
    )(append)
    tool(
        app,
        "md.edit",
        title="Change text in a document",
        kind="danger",
        params={"room": ROOM, "summary": SUMMARY, "edits": 'What to replace: [{"find": "...", "replace": "..."}].'},
    )(edit)
    tool(
        app,
        "md.rewrite",
        title="Rewrite a whole document",
        kind="danger",
        params={"room": ROOM, "summary": SUMMARY, "text": "The whole new document, in Markdown."},
    )(rewrite)
    tool(
        app,
        "md.create",
        title="Make a new document",
        kind="write",
        params={"title": "The document's title.", "text": "Its Markdown; only the title when left out."},
    )(create)
