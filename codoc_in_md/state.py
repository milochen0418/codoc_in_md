import re as _re
import reflex as rx
import sqlmodel
import asyncio
import atexit
import os
import sys
import threading
import time
import random
import uuid
import zlib
import logging
from datetime import datetime
from typing import TypedDict, Optional
from pathlib import Path

from .call import CallState

try:  # on re_ddns: the documents as items of a shared collection (_ItemDocumentStore)
    from reflex_ddns_auth.collections import Collection, ItemNotFound
    from reflex_ddns_auth.collections.refs import valid_item_id
except ImportError:
    Collection = ItemNotFound = valid_item_id = None

from .embeds import (
    apply_hackmd_mathjax_delimiters,
    apply_hackmd_code_blocks_with_lines,
    apply_hackmd_code_fence_options,
    apply_hackmd_blockquote_labels,
    apply_hackmd_admonitions,
    apply_hackmd_embeds,
    apply_hackmd_emojis,
    apply_hackmd_image_sizes,
    apply_hackmd_fontawesome_icons,
    apply_hackmd_typography,
    apply_hackmd_inline_extensions,
    apply_hackmd_abbreviations,
    apply_hackmd_toc_placeholder,
)


def _inject_scroll_markers(source: str, *, every: int = 3) -> str:
    """Inject hidden line markers for more accurate scroll syncing.

    We insert raw HTML spans that carry the original editor line number:
      <span class="codoc-mdline" data-codoc-mdline="123" ...></span>

    The preview scroll-sync JS can then map Monaco's visible top line to a
    specific DOM anchor, preventing large drift when heading sections are long.

    Markers are skipped inside fenced code blocks.
    """

    text = source or ""
    if not text:
        return text

    every = max(2, int(every))
    lines = text.splitlines(keepends=True)
    out: list[str] = []

    in_code = False
    fence_ch = ""
    fence_len = 0

    def _maybe_open_fence(line: str) -> tuple[str, int] | None:
        import re

        m = re.match(r"^\s*(?P<fence>`{3,}|~{3,})(?P<info>.*)$", line.rstrip("\n"))
        if not m:
            return None
        fence = m.group("fence")
        return fence[0], len(fence)

    def _is_fence_close(line: str, ch: str, ln: int) -> bool:
        import re

        if not ch or not ln:
            return False
        raw = line.rstrip("\n").rstrip("\r")
        return re.match(rf"^\s*{re.escape(ch)}{{{ln},}}\s*$", raw) is not None

    def _marker(line_no: int) -> str:
        # display:block + height:0 means it takes no visible space but has a stable offsetTop.
        return (
            f'<span class="codoc-mdline" data-codoc-mdline="{line_no}" '
            'style="display:block;height:0;overflow:hidden;pointer-events:none"></span>\n'
        )

    import re

    heading_re = re.compile(r"^\s{0,3}#{1,6}\s+.+")

    # Admonition-aware: do not inject markers inside HackMD-style admonitions.
    # Those blocks are later transformed into raw HTML by `apply_hackmd_admonitions`,
    # and any injected marker lines would become literal text inside the admonition.
    admonition_start_re = re.compile(r"^\s*:::[a-zA-Z0-9_-]+.*$")
    admonition_end_re = re.compile(r"^\s*:::\s*$")

    # Table-aware: do not inject raw HTML markers inside GFM tables.
    # Inserting a marker line between the header/delimiter/rows breaks table parsing.
    table_delim_re = re.compile(
        r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)+\|?\s*$"
    )

    def _is_table_header_line(line: str) -> bool:
        s = line.strip()
        if "|" not in s:
            return False
        # Require some non-syntax content.
        return any(ch not in "|:- " for ch in s)

    def _is_table_delim_line(line: str) -> bool:
        return table_delim_re.match(line.rstrip("\r\n")) is not None

    last_marker_line: int | None = None

    in_table = False
    in_admonition = False
    in_math_block = False

    # Math-aware: do not inject raw HTML markers inside display-math fences.
    # Reflex's markdown uses remark-math + rehype-katex. Injecting HTML marker
    # lines between `$$` fences breaks math parsing and renders as plain text.
    math_fence_re = re.compile(r"^\s*\$\$\s*$")

    for idx, line in enumerate(lines):
        line_no = idx + 1

        if not in_code:
            opened = _maybe_open_fence(line)
            if opened is not None:
                in_code = True
                fence_ch, fence_len = opened
            else:
                # Track HackMD admonition fences.
                if not in_admonition and admonition_start_re.match(line.rstrip("\r\n")):
                    in_admonition = True
                elif in_admonition and admonition_end_re.match(line.rstrip("\r\n")):
                    # Keep the closing fence in the output, but stop skipping markers
                    # after this line.
                    pass

                # Detect start/end of a table block.
                if not in_table:
                    if idx + 1 < len(lines) and _is_table_header_line(lines[idx]) and _is_table_delim_line(lines[idx + 1]):
                        in_table = True
                else:
                    # End table when we hit a blank line or a non-pipe line.
                    if (not line.strip()) or ("|" not in line):
                        in_table = False

                if (
                    (not in_table)
                    and (not in_admonition)
                    and (not in_math_block)
                    and (line_no == 1 or (line_no % every == 0) or heading_re.match(line))
                ):
                    out.append(_marker(line_no))
                    last_marker_line = line_no
        else:
            if _is_fence_close(line, fence_ch, fence_len):
                in_code = False
                fence_ch = ""
                fence_len = 0

        out.append(line)

        if in_admonition and admonition_end_re.match(line.rstrip("\r\n")):
            in_admonition = False

        # Toggle math-block state only when not inside fenced code.
        if (not in_code) and math_fence_re.match(line.rstrip("\r\n")):
            in_math_block = not in_math_block

    # Always add a final marker near EOF so the last segment doesn't rely solely on scrollHeight.
    last_line = len(lines)
    if last_line > 0 and last_marker_line != last_line:
        # If the file doesn't end with a newline, avoid concatenating the marker
        # onto the last line (which can break Markdown constructs like `$$`).
        if out and not out[-1].endswith("\n"):
            out.append("\n")
        out.append(_marker(last_line))

    # Add an invisible tail anchor to stabilize "last section" syncing.
    # IMPORTANT: don't use h1/h2/... here because the preview uses a component_map
    # that rebuilds heading elements and can drop raw attributes/styles.
    # A plain div rendered via rehypeRaw preserves data attrs reliably.
    # Give it some height to mimic the "extra slack" effect of a real trailing heading.
    if out and not out[-1].endswith("\n"):
        out.append("\n")
    out.append(
        '<div data-codoc-tail="1" aria-hidden="true" '
        'style="height:40vh;opacity:0;overflow:hidden;pointer-events:none"></div>\n'
    )

    return "".join(out)


def _render_markdown_source(source: str) -> str:
    normalized = apply_hackmd_mathjax_delimiters(source)
    normalized = _inject_scroll_markers(normalized, every=5)
    normalized = apply_hackmd_code_fence_options(normalized)
    normalized = apply_hackmd_toc_placeholder(normalized)
    normalized = apply_hackmd_typography(normalized)
    normalized = apply_hackmd_inline_extensions(normalized)
    normalized = apply_hackmd_abbreviations(normalized)
    normalized = apply_hackmd_fontawesome_icons(normalized)
    normalized = apply_hackmd_emojis(normalized)
    normalized = apply_hackmd_image_sizes(normalized)
    normalized = apply_hackmd_embeds(normalized)
    normalized = apply_hackmd_admonitions(normalized)
    normalized = apply_hackmd_blockquote_labels(normalized)
    return apply_hackmd_code_blocks_with_lines(normalized)


def render_markdown_for_export(source: str) -> str:
    """Render markdown for export (PDF/HTML) without scroll markers."""

    normalized = apply_hackmd_mathjax_delimiters(source)
    normalized = apply_hackmd_code_fence_options(normalized)
    normalized = apply_hackmd_toc_placeholder(normalized)
    normalized = apply_hackmd_typography(normalized)
    normalized = apply_hackmd_inline_extensions(normalized)
    normalized = apply_hackmd_abbreviations(normalized)
    normalized = apply_hackmd_fontawesome_icons(normalized)
    normalized = apply_hackmd_emojis(normalized)
    normalized = apply_hackmd_image_sizes(normalized)
    normalized = apply_hackmd_embeds(normalized)
    normalized = apply_hackmd_admonitions(normalized)
    normalized = apply_hackmd_blockquote_labels(normalized)
    return apply_hackmd_code_blocks_with_lines(normalized)


def _extract_title(content: str) -> str:
    """Extract the first markdown heading as document title."""
    for line in (content or "").splitlines():
        m = _re.match(r"^\s{0,3}(#{1,6})\s+(.+)", line)
        if m:
            return m.group(2).strip()[:100]
    return "Untitled"


class DocumentModel(rx.Model, table=True):
    """Persistent document storage."""
    doc_id: str = sqlmodel.Field(index=True, unique=True)
    title: str = ""
    content: str = ""
    updated_at: float = 0.0
    version: int = 1
    created_by_email: str = ""
    created_by_name: str = ""


class Document(TypedDict):
    doc_id: str
    title: str
    content: str
    updated_at: float
    version: int
    created_by_email: str
    created_by_name: str


class _DocumentStore:
    """Dict-like facade backed by the database.

    Keeps the same interface as the original ``dict[str, Document]``
    so callers don't need to know about the persistence layer.
    Swap out the implementation here to switch databases.
    """

    @staticmethod
    def _to_document(row: DocumentModel) -> Document:
        return Document(
            doc_id=row.doc_id,
            title=row.title or _extract_title(row.content),
            content=row.content,
            updated_at=row.updated_at,
            version=row.version,
            created_by_email=row.created_by_email,
            created_by_name=row.created_by_name,
        )

    def get(self, doc_id: str) -> Optional[Document]:
        with rx.session() as session:
            row = session.exec(
                DocumentModel.select().where(DocumentModel.doc_id == doc_id)
            ).first()
            return self._to_document(row) if row else None

    def __contains__(self, doc_id: str) -> bool:
        return self.get(doc_id) is not None

    def __getitem__(self, doc_id: str) -> Document:
        doc = self.get(doc_id)
        if doc is None:
            raise KeyError(doc_id)
        return doc

    def __setitem__(self, doc_id: str, doc: Document):
        title = doc.get("title") or _extract_title(doc.get("content", ""))
        with rx.session() as session:
            row = session.exec(
                DocumentModel.select().where(DocumentModel.doc_id == doc_id)
            ).first()
            if row is None:
                row = DocumentModel(
                    doc_id=doc_id,
                    title=title,
                    content=doc.get("content", ""),
                    updated_at=doc.get("updated_at", 0.0),
                    version=doc.get("version", 1),
                    created_by_email=doc.get("created_by_email", ""),
                    created_by_name=doc.get("created_by_name", ""),
                )
                session.add(row)
            else:
                row.content = doc.get("content", "")
                row.title = title
                row.updated_at = doc.get("updated_at", 0.0)
                row.version = doc.get("version", 1)
                if doc.get("created_by_email") and not row.created_by_email:
                    row.created_by_email = doc["created_by_email"]
                    row.created_by_name = doc.get("created_by_name", "")
                session.add(row)
            session.commit()

    def __delitem__(self, doc_id: str):
        with rx.session() as session:
            row = session.exec(
                DocumentModel.select().where(DocumentModel.doc_id == doc_id)
            ).first()
            if row:
                session.delete(row)
                session.commit()

    def values(self) -> list[Document]:
        """Return all documents, most-recently-updated first."""
        with rx.session() as session:
            rows = session.exec(
                DocumentModel.select().order_by(DocumentModel.updated_at.desc())
            ).all()
            return [self._to_document(r) for r in rows]

    def clear(self):
        """Delete every document (useful for testing)."""
        with rx.session() as session:
            rows = session.exec(DocumentModel.select()).all()
            for row in rows:
                session.delete(row)
            session.commit()


logger = logging.getLogger(__name__)

# The App Store gives the app this collection (its catalog entry declares it, and the install
# sets DDNS_COLLECTIONS_ROOT); every document is then an item of it, of this kind.
COLLECTION = "documents"
KIND = "document.markdown"
DOC_FILE = "doc.md"
# A saved change reaches the collection this many seconds later, so typing writes a document
# at most once per SAVE_DELAY.
SAVE_DELAY = 1.5


class _ItemDocumentStore:
    """The documents as items of a shared collection (re_ddns's Owned Collections).

    Document ``<doc_id>`` is the item ``documents:<app>/<doc_id>``, a folder holding
    ``doc.md``, with the title and the creator in its manifest. Every app given the
    collection can read the documents, and the App Store's storage page lists them.

    Same interface as :class:`_DocumentStore`, and as fast while people type: a save
    keeps the document in memory, and a background thread writes it SAVE_DELAY seconds
    later (published the first time, revised in place after that). Whatever is still
    unwritten at exit is written then.
    """

    def __init__(self, items):
        self.items = items
        self._lock = threading.Lock()  # guards _pending and _timer
        self._write_lock = threading.Lock()  # one write or delete at a time
        # Saved, not written yet: readers get these until they are on disk.
        self._pending: dict[str, Document] = {}
        self._timer: Optional[threading.Timer] = None
        atexit.register(self.flush)

    def _item(self, doc_id: str):
        """The document's item in our own folder (not a copy from another host), or None."""
        if not valid_item_id(doc_id):
            return None
        item = self.items.get(self.items.ref(doc_id), remote=False)
        return item if item is not None and item.kind == KIND and not item.replica else None

    @staticmethod
    def _to_document(item) -> Optional[Document]:
        try:
            # Decoded from bytes: reading it as text would turn \r\n into \n.
            content = item.primary.read_bytes().decode("utf-8") if item.primary else ""
        except (OSError, UnicodeDecodeError):
            return None
        meta = item.meta
        return Document(
            doc_id=item.id,
            title=item.title or _extract_title(content),
            content=content,
            updated_at=_timestamp(item.updated_at),
            version=item.revision,
            created_by_email=str(meta.get("created_by_email") or ""),
            created_by_name=str(meta.get("created_by_name") or ""),
        )

    def get(self, doc_id: str) -> Optional[Document]:
        with self._lock:
            doc = self._pending.get(doc_id)
        if doc is not None:
            return Document(**doc)
        item = self._item(doc_id)
        return self._to_document(item) if item is not None else None

    def __contains__(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id in self._pending:
                return True
        return self._item(doc_id) is not None

    def __getitem__(self, doc_id: str) -> Document:
        doc = self.get(doc_id)
        if doc is None:
            raise KeyError(doc_id)
        return doc

    def __setitem__(self, doc_id: str, doc: Document):
        doc = Document(**doc)
        doc["title"] = doc.get("title") or _extract_title(doc.get("content", ""))
        with self._lock:
            if doc_id not in self._pending and not valid_item_id(doc_id):
                logger.warning("Document id %r can't name an item; it is kept in memory only", doc_id)
            self._pending[doc_id] = doc
            if self._timer is None:
                self._timer = threading.Timer(SAVE_DELAY, self.flush)
                self._timer.daemon = True
                self._timer.start()

    def __delitem__(self, doc_id: str):
        with self._write_lock:
            with self._lock:
                self._pending.pop(doc_id, None)
            if valid_item_id(doc_id):
                self.items.remove(doc_id)

    def values(self) -> list[Document]:
        """Return all documents, most-recently-updated first."""
        with self._lock:
            docs = {doc_id: Document(**doc) for doc_id, doc in self._pending.items()}
        # Copies fetched from another host are that host's documents, not ours.
        for item in self.items.items(kind=KIND, remote=False):
            if item.owner == self.items.app_id and not item.replica and item.id not in docs:
                doc = self._to_document(item)
                if doc is not None:
                    docs[item.id] = doc
        return sorted(docs.values(), key=lambda d: d["updated_at"], reverse=True)

    def clear(self):
        """Delete every document (useful for testing)."""
        for doc in self.values():
            del self[doc["doc_id"]]

    def flush(self) -> None:
        """Writes the documents saved since they were last written (on the timer, and at exit)."""
        with self._lock:
            self._timer = None
            doc_ids = list(self._pending)
        for doc_id in doc_ids:
            if not valid_item_id(doc_id):
                continue
            with self._write_lock:
                with self._lock:
                    doc = self._pending.get(doc_id)
                if doc is None:
                    continue  # deleted meanwhile
                try:
                    self._write(doc_id, doc)
                except Exception as exc:  # kept in memory; the next save tries again
                    logger.warning("Could not write document %s to the collection: %s", doc_id, exc)
                    continue
                with self._lock:
                    # Saved again meanwhile: that one is written next time.
                    if self._pending.get(doc_id) is doc:
                        del self._pending[doc_id]

    def _write(self, doc_id: str, doc: Document) -> None:
        """Revises the document's item, or publishes one when there is none: a new document,
        or one deleted on the storage page while people were still writing in it (saving
        creates it again, as the database does)."""
        data = (doc.get("content") or "").encode("utf-8")
        fields = dict(
            title=doc["title"],
            meta={
                "created_by_email": doc.get("created_by_email", ""),
                "created_by_name": doc.get("created_by_name", ""),
            },
        )
        try:
            with self.items.revise(doc_id, **fields) as rev:
                with rev.open(DOC_FILE) as fh:
                    fh.write(data)
            return
        except ItemNotFound:
            pass
        with self.items.publish(doc_id, kind=KIND, primary=DOC_FILE, **fields) as item:
            with item.open(DOC_FILE) as fh:
                fh.write(data)


def _timestamp(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _make_store():
    """The documents as items of the shared collection when re_ddns gave the app one, else in
    the database (``db_url`` in rxconfig.py)."""
    if os.environ.get("DDNS_COLLECTIONS_ROOT") and Collection is not None:
        if hasattr(Collection, "revise"):
            return _ItemDocumentStore(Collection(COLLECTION))
        print("CoDoc: this reflex_ddns_auth can't revise items; documents stay in the database", file=sys.stderr)
    return _DocumentStore()


DOCUMENTS_STORE = _make_store()


# Presence and cursor colors: distinct, visible as a caret on the white editor,
# and readable behind a name tag.
USER_COLORS = [
    "#E53935",  # red
    "#1E88E5",  # blue
    "#43A047",  # green
    "#8E24AA",  # purple
    "#F4511E",  # orange
    "#00897B",  # teal
    "#D81B60",  # pink
    "#3949AB",  # indigo
    "#6D4C41",  # brown
    "#0097A7",  # cyan
    "#7CB342",  # light green
    "#5E35B1",  # deep purple
]


class User(TypedDict):
    id: str
    name: str
    color: str  # the color the user prefers
    last_seen: float
    avatar_url: str
    joined_at: float  # when they arrived on the document
    doc_color: str  # the color they show on the document (cursor, avatar ring)


class DisplayUser(TypedDict):
    id: str
    name: str
    color: str
    avatar_url: str


class DocListItem(TypedDict):
    doc_id: str
    title: str
    updated_at: float
    formatted_time: str
    created_by_email: str
    created_by_name: str
    words: int
    is_empty: bool
    snippet: str


class CreatorOption(TypedDict):
    key: str
    label: str
    sublabel: str
    count: int


FIXTURE_DOCS: dict[str, str] = {
    # Special fixture docs to validate renderer behavior.
    "emojify": "hackmd_emojify_smoke.md",
    "emojify_all": "hackmd_emojify_all_shortcodes.md",
    "embeds": "hackmd_embeds.md",
    "fontawesome": "hackmd_fontawesome.md",
    "images": "hackmd_images.md",
    "mathjax": "hackmd_mathjax.md",
    "hackmd_toc": "hackmd_toc.md",
    "plantuml": "ext_plantuml.md",
}


# Seconds without a heartbeat before a tab counts as gone from a document.
PRESENCE_TTL = 10
# How long a tab's Reflex socket may be down before its presence loop gives up:
# long enough for a reload or a brief network blip to reconnect, short enough
# that a closed tab leaves the header within a moment.
PRESENCE_DISCONNECT_GRACE = 3
# Someone who comes straight back (reload, reconnect) gets their color again.
PRESENCE_COLOR_MEMORY = 60
# A page unmount followed by a mount within this long is a dev-build (React
# StrictMode) remount, not a departure.
PRESENCE_LEAVE_SETTLE = 0.5


def _client_connected(token: str) -> bool:
    """Whether the tab with this Reflex client token still has its socket open.

    Reflex keeps a state's background tasks running after the tab's socket is
    gone (the token is merely unlinked), so the presence loop has to check for
    itself; otherwise it would keep a closed tab "present" until the backend
    restarts.
    """
    try:
        from codoc_in_md.codoc_in_md import app  # lazy: that module imports this one

        namespace = app.event_namespace
    except Exception:
        return True
    if namespace is None:
        return True
    return token in namespace.token_to_sid


class SharedState:
    """In-memory presence (ephemeral, per backend process).

    Entries are per tab (Reflex client token), so one tab closing never drops a
    person who still has the document open in another tab; the header shows
    one avatar per person.
    """

    users: dict[str, dict[str, User]] = {}
    # (doc_id, user id) -> (their color on it, when they left): given back on return.
    _recent_colors: dict[tuple[str, str], tuple[str, float]] = {}
    # token -> (doc_id, when): tabs whose document page unmounted (see
    # EditorState.leave_document). Applied by whichever presence loop runs next,
    # so the departure shows for the others even while the leaving tab's own
    # state lock is busy with its next page.
    pending_leaves: dict[str, tuple[str, float]] = {}

    @classmethod
    def apply_pending_leaves(cls, now: float):
        for token, (doc_id, left_at) in list(cls.pending_leaves.items()):
            if now - left_at >= PRESENCE_LEAVE_SETTLE:
                cls.pending_leaves.pop(token, None)
                cls.remove_user(doc_id, token)

    @classmethod
    def update_user(cls, doc_id: str, token: str, user: User):
        room = cls.users.setdefault(doc_id, {})
        prev = room.get(token)
        if prev:
            # Keep when they arrived and their color here for as long as they stay.
            user["joined_at"] = prev.get("joined_at", user["joined_at"])
            user["doc_color"] = prev.get("doc_color", "")
        else:
            # Their other tab, or a quick return: the same color as before.
            same = next((u for u in room.values() if u["id"] == user["id"]), None)
            if same:
                user["joined_at"] = same.get("joined_at", user["joined_at"])
                user["doc_color"] = same.get("doc_color", "")
            else:
                color, left_at = cls._recent_colors.get((doc_id, user["id"]), ("", 0.0))
                if color and time.time() - left_at < PRESENCE_COLOR_MEMORY:
                    user["doc_color"] = color
        room[token] = user

    @classmethod
    def remove_user(cls, doc_id: str, token: str):
        """A tab left ``doc_id`` (closed, reloaded, or went to another page)."""
        room = cls.users.get(doc_id)
        if room is None:
            return
        gone = room.pop(token, None)
        now = time.time()
        if gone and gone.get("doc_color"):
            cls._recent_colors[(doc_id, gone["id"])] = (gone["doc_color"], now)
        cls._recent_colors = {
            k: v for k, v in cls._recent_colors.items() if now - v[1] < PRESENCE_COLOR_MEMORY
        }
        if not room:
            cls.users.pop(doc_id, None)

    @classmethod
    def get_active_users(cls, doc_id: str) -> list[User]:
        """Who is on ``doc_id``: one entry per person, each with a distinct color."""
        now = time.time()
        cls.apply_pending_leaves(now)
        if doc_id not in cls.users:
            return []
        room = {t: u for t, u in cls.users[doc_id].items() if now - u["last_seen"] < PRESENCE_TTL}
        cls.users[doc_id] = room
        # One entry per person (their earliest tab).
        people: dict[str, User] = {}
        for u in sorted(room.values(), key=lambda u: (u.get("joined_at", 0.0), u["id"])):
            people.setdefault(u["id"], u)
        # Everyone on a document gets a different color, so their cursors can be told
        # apart: earlier arrivals keep theirs, a later one whose color is taken gets
        # the first free one.
        taken: set[str] = set()
        for u in people.values():
            color = u.get("doc_color") or u["color"]
            if color in taken:
                color = next((c for c in USER_COLORS if c not in taken), color)
            u["doc_color"] = color
            taken.add(color)
        for u in room.values():
            u["doc_color"] = people[u["id"]]["doc_color"]
        return list(people.values())


class EditorState(rx.State):
    """Manages the collaborative document editor state."""

    doc_id: str = ""
    doc_content: str = ""
    doc_content_rendered: str = ""
    users: list[DisplayUser] = []
    my_user_id: str = ""
    my_user_name: str = ""
    my_user_color: str = ""
    # This user's color on the current document (see SharedState.get_active_users).
    my_doc_color: str = ""
    my_user_email: str = ""
    my_user_avatar: str = ""
    is_authenticated: bool = False
    is_connected: bool = False
    is_syncing: bool = False
    # Bumped by each run of on_load: the presence loop of an earlier run stops.
    _presence_gen: int = 0
    # When the document page was left for another page (see leave_document).
    _left_at: float = 0.0
    is_loading: bool = True
    last_version: int = 0
    view_mode: str = "split"

    # Sidebar visibility — defaults to True (open on wide screens).
    sidebar_open: bool = True

    # Mobile header menu
    mobile_menu_open: bool = False

    # Split-view behavior.
    # When locked, the preview scroll follows the editor scroll (HackMD-like).
    is_scroll_locked: bool = True

    def handle_viewport_width(self, width: list):
        """Auto-close sidebar and switch view mode on narrow viewports."""
        try:
            w = int(width[0]) if isinstance(width, list) else int(width)
        except (TypeError, ValueError, IndexError):
            return
        if w < 768:
            self.sidebar_open = False
            if self.view_mode == "split":
                self.view_mode = "editor"
        elif w < 1024:
            self.sidebar_open = False

    # Monaco editor should be treated as uncontrolled for a stable cursor.
    # We keep an initial seed value that only changes when the document is (re)loaded
    # or when we intentionally refresh the editor (e.g., remote overwrite).
    editor_seed_content: str = ""
    editor_seed_version: int = 0

    @rx.var
    def editor_component_key(self) -> str:
        return f"{self.doc_id}:{self.editor_seed_version}"

    async def _generate_user_info(self):
        """Use SSO auth info if available, otherwise generate random identity."""
        try:
            from reflex_ddns_auth import AuthState
            auth = await self.get_state(AuthState)
            if not auth._auth_loaded:
                await auth.load_auth()
            if auth.is_logged_in:
                self.my_user_id = auth.user_email or str(random.randint(10000, 99999))
                self.my_user_name = auth.user_name or auth.user_email
                self.my_user_email = auth.user_email
                self.my_user_avatar = auth.user_avatar
                # Stable across restarts (unlike hash()), so a person keeps their color.
                self.my_user_color = USER_COLORS[zlib.crc32(auth.user_email.encode()) % len(USER_COLORS)]
                self.is_authenticated = True
                return
        except ImportError:
            pass

        # Keep a stable guest id/color across page loads; only rotate when
        # coming from a logged-in identity (or on first visit).
        if self.is_authenticated or not self.my_user_id:
            self.my_user_id = str(random.randint(10000, 99999))
            self.my_user_color = random.choice(USER_COLORS)
        elif self.my_user_color not in USER_COLORS:
            # A session from before the current palette.
            self.my_user_color = random.choice(USER_COLORS)
        self.is_authenticated = False
        self.my_user_name = "Guest"
        self.my_user_email = ""
        self.my_user_avatar = ""

    @rx.event
    async def create_new_document(self):
        """Creates a new empty document and redirects to it."""
        await self._generate_user_info()
        new_id = str(uuid.uuid4())[:8]
        default_content = "# Start typing your masterpiece..."
        self.is_syncing = False
        self.doc_id = new_id
        self.doc_content = default_content
        self.doc_content_rendered = _render_markdown_source(default_content)
        self._save_doc_to_db(new_id, default_content)
        self.last_version = 1
        self.editor_seed_content = default_content
        self.editor_seed_version += 1
        return rx.redirect(f"/doc/{new_id}")

    @rx.event
    async def duplicate_document(self):
        """Duplicates the current document into a new one and redirects to it."""
        await self._generate_user_info()
        new_id = str(uuid.uuid4())[:8]
        self.is_syncing = False
        self._save_doc_to_db(new_id, self.doc_content)
        self.doc_id = new_id
        self.editor_seed_content = self.doc_content
        self.editor_seed_version += 1
        return rx.redirect(f"/doc/{new_id}")

    def _get_doc_from_db(self, doc_id: str) -> Optional[Document]:
        """Helper to fetch document from the store."""
        return DOCUMENTS_STORE.get(doc_id)

    def _save_doc_to_db(self, doc_id: str, content: str):
        """Helper to save document to the store."""
        now = time.time()
        creator_email = self.my_user_email if self.is_authenticated else ""
        creator_name = self.my_user_name if self.is_authenticated else "Guest"
        if doc_id not in DOCUMENTS_STORE:
            doc: Document = {
                "doc_id": doc_id,
                "title": _extract_title(content),
                "content": content,
                "updated_at": now,
                "version": 1,
                "created_by_email": creator_email,
                "created_by_name": creator_name,
            }
            DOCUMENTS_STORE[doc_id] = doc
            self.last_version = 1
        else:
            doc = DOCUMENTS_STORE[doc_id]
            doc["content"] = content
            doc["title"] = _extract_title(content)
            doc["updated_at"] = now
            doc["version"] += 1
            DOCUMENTS_STORE[doc_id] = doc
            self.last_version = doc["version"]

    @rx.event(background=True)
    async def on_load(self):
        """Initializes the session for the specific document ID."""
        # Auto-close sidebar on narrow viewports.
        yield rx.call_script(
            "window.innerWidth",
            callback=EditorState.handle_viewport_width,
        )

        path = getattr(self.router.url, "path", "")
        doc_id = path.rstrip("/").split("/")[-1] if path else ""

        # Fixture docs are meant to reflect the current contents of files in ./assets.
        # Always reload fixtures on load to avoid stale in-memory documents causing
        # confusing behavior in demos and E2E tests.
        fixture_name = FIXTURE_DOCS.get(doc_id) if doc_id else None
        fixture_content: str | None = None
        if fixture_name:
            try:
                repo_root = Path(__file__).resolve().parents[1]
                fixture_path = repo_root / "assets" / fixture_name
                fixture_content = fixture_path.read_text(encoding="utf-8")
            except Exception:
                fixture_content = None

        async with self:
            if not doc_id:
                new_id = str(uuid.uuid4())[:8]
                yield rx.redirect(f"/doc/{new_id}")
                return
            # Drop the previous document's content before switching doc_id so the
            # editor (keyed by doc_id) never remounts under the new doc with stale
            # content, which Yjs would otherwise seed/sync into the new document.
            self.is_loading = True
            self.doc_id = doc_id
            self.doc_content = ""
            self.doc_content_rendered = ""
            self.editor_seed_content = ""
            self.editor_seed_version += 1
            await self._generate_user_info()
            # This run reports the tab's presence from now on (a reload or another
            # document runs on_load again; the earlier loop then stops).
            self._presence_gen += 1
            presence_gen = self._presence_gen
            self._left_at = 0.0
            token = self.router.session.client_token
            SharedState.pending_leaves.pop(token, None)

        # For fixtures, prefer the asset file even if the doc exists in memory.
        if fixture_content is not None:
            db_doc = None
        else:
            db_doc = self._get_doc_from_db(doc_id)
        async with self:
            if db_doc:
                self.doc_content = db_doc["content"]
                self.doc_content_rendered = _render_markdown_source(self.doc_content)
                self.last_version = db_doc["version"]
                self.editor_seed_content = self.doc_content
                self.editor_seed_version += 1
            else:
                default_content = "# Start typing your masterpiece..."

                if fixture_content is not None:
                    default_content = fixture_content
                else:
                    fixture_name2 = FIXTURE_DOCS.get(doc_id)
                    if fixture_name2:
                        try:
                            repo_root = Path(__file__).resolve().parents[1]
                            fixture_path = repo_root / "assets" / fixture_name2
                            default_content = fixture_path.read_text(encoding="utf-8")
                        except Exception:
                            # Fall back to the normal default if fixture isn't available.
                            pass
                self.doc_content = default_content
                self.doc_content_rendered = _render_markdown_source(default_content)
                self._save_doc_to_db(doc_id, default_content)
                self.last_version = 1
                self.editor_seed_content = default_content
                self.editor_seed_version += 1
            self.is_connected = True
            self.is_syncing = True
            self.is_loading = False
        gone_since: float | None = None
        presence_doc = ""  # the document this loop last reported us on
        while True:
            async with self:
                if not self.is_syncing:
                    SharedState.remove_user(presence_doc, token)
                    break
                if self._presence_gen != presence_gen:
                    break  # a newer run of on_load reports this tab now
                left_at = self._left_at
                current_doc_id = self.doc_id
                page_path = getattr(self.router.url, "path", "") or ""
                now = time.time()
                me: User = {
                    "id": self.my_user_id,
                    "name": self.my_user_name,
                    "color": self.my_user_color,
                    "last_seen": now,
                    "avatar_url": self.my_user_avatar,
                    "joined_at": now,
                    "doc_color": "",
                }

            # The page was left (see leave_document): stop, unless the unmount
            # was a dev-build remount, which enter_document undoes within a moment.
            if left_at:
                if time.time() - left_at >= PRESENCE_LEAVE_SETTLE:
                    SharedState.pending_leaves.pop(token, None)
                    SharedState.remove_user(presence_doc, token)
                    break
                await asyncio.sleep(0.2)
                continue
            # The tab is gone once its socket has been down for a moment (a reload
            # or a brief network blip reconnects sooner), or once it shows another
            # page of the app (e.g. My Documents).
            if _client_connected(token):
                gone_since = None
            else:
                gone_since = gone_since or time.time()
            if (gone_since and time.time() - gone_since > PRESENCE_DISCONNECT_GRACE) or (
                page_path and not page_path.startswith("/doc/")
            ):
                SharedState.remove_user(presence_doc, token)
                break
            if presence_doc and presence_doc != current_doc_id:
                SharedState.remove_user(presence_doc, token)
            presence_doc = current_doc_id

            # Keep ephemeral presence tracking server-side.
            SharedState.update_user(current_doc_id, token, me)
            current_users = SharedState.get_active_users(current_doc_id)
            current_users.sort(key=lambda u: u["name"])

            display_users: list[DisplayUser] = [
                {"id": u["id"], "name": u["name"], "color": u["doc_color"], "avatar_url": u.get("avatar_url", "")}
                for u in current_users
            ]
            my_doc_color = next(
                (u["doc_color"] for u in current_users if u["id"] == me["id"]), me["color"]
            )

            # Only write to state if something visible changed.
            async with self:
                if not self.is_syncing:
                    break
                if display_users != self.users:
                    self.users = display_users
                if my_doc_color != self.my_doc_color:
                    self.my_doc_color = my_doc_color
                # The document's call: how many are in it, whether it rings us.
                calls = await self.get_state(CallState)
                calls._refresh(current_doc_id, self.my_user_id)

            # Document sync is now handled by Yjs (CRDT) via
            # assets/yjs_collab.js + the /yjs/{doc_id} WebSocket relay.
            # Only presence tracking remains in this loop.

            await asyncio.sleep(0.5)

    @rx.event
    def update_content(self, new_content: str):
        """Updates the document content locally and persists to in-memory store."""

        # Ignore editor changes while a document is (re)loading: they belong to
        # the previous document's editor instance, not to self.doc_id.
        if self.is_loading:
            return
        self.doc_content = new_content
        self.doc_content_rendered = _render_markdown_source(new_content)
        self._save_doc_to_db(self.doc_id, new_content)

    @rx.event
    def export_markdown(self):
        """Download the current document as a .md file."""
        filename = f"{self.doc_id}.md"
        return rx.download(data=self.doc_content, filename=filename)

    @rx.event
    def set_view_mode(self, mode: str):
        """Sets the current view mode (editor, split, or preview)."""
        self.view_mode = mode
        # Whichever editor mounts next (Preview keeps one, hidden) starts from the
        # latest document content, so it doesn't reset or hand Yjs an old copy.
        self.editor_seed_content = self.doc_content
        if mode in {"editor", "split"}:
            self.editor_seed_version += 1

    @rx.event
    def set_sidebar_open(self, value: bool):
        self.sidebar_open = value

    @rx.event
    def set_mobile_menu_open(self, value: bool):
        self.mobile_menu_open = value

    @rx.event
    def toggle_scroll_lock(self):
        """Toggles whether preview scroll follows editor scroll in split view."""
        self.is_scroll_locked = not self.is_scroll_locked

    @rx.event
    def enter_document(self):
        """The document page mounted (or, in dev builds, remounted right after unmounting)."""
        self._left_at = 0.0
        SharedState.pending_leaves.pop(self.router.session.client_token, None)

    @rx.event
    def leave_document(self):
        """The document page unmounted (My Documents, another app page).

        Marks this tab as leaving; the presence loops take it off the document
        PRESENCE_LEAVE_SETTLE later unless enter_document cancels it first (React
        StrictMode fires unmount+mount once right after mounting in dev builds).
        Doing it this way, rather than in the loop of this tab alone, shows the
        departure to the others even while this tab's state lock is busy with
        the next page's on_load.
        """
        now = time.time()
        self._left_at = now
        SharedState.pending_leaves[self.router.session.client_token] = (self.doc_id, now)

    @rx.var
    def user_count(self) -> int:
        """Returns the number of connected users."""
        return len(self.users)


SEARCH_INPUT_ID = "doc-list-search"


class DocListState(rx.State):
    """State for the document management page."""

    # Filtered + sorted view shown in the table.
    documents: list[DocListItem] = []
    total_count: int = 0
    creator_options: list[CreatorOption] = []
    empty_count: int = 0
    my_email: str = ""

    # Filters
    search: str = ""
    creator_filter: str = "all"  # all | mine | guest | acct:<email>
    time_filter: str = "any"  # any | today | 7d | 30d | older
    sort_by: str = "updated_desc"  # updated_desc | updated_asc | title_asc | title_desc
    only_empty: bool = False

    _all_docs: list[DocListItem] = []
    _contents: dict[str, str] = {}

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.search.strip()
            or self.creator_filter != "all"
            or self.time_filter != "any"
            or self.only_empty
        )

    @staticmethod
    def _creator_key(doc: DocListItem) -> str:
        email = doc["created_by_email"]
        return f"acct:{email}" if email else "guest"

    @rx.event
    async def load_documents(self):
        """Load all documents from the store, then apply the current filters."""
        import datetime

        self.my_email = ""
        try:
            from reflex_ddns_auth import AuthState
            auth = await self.get_state(AuthState)
            if auth.is_logged_in:
                self.my_email = auth.user_email or ""
        except ImportError:
            pass

        all_docs: list[DocListItem] = []
        contents: dict[str, str] = {}
        for d in DOCUMENTS_STORE.values():
            content = d.get("content", "") or ""
            stripped = content.strip()
            all_docs.append(
                DocListItem(
                    doc_id=d["doc_id"],
                    title=d.get("title") or _extract_title(content),
                    updated_at=d["updated_at"],
                    formatted_time=(
                        datetime.datetime.fromtimestamp(d["updated_at"]).strftime("%Y-%m-%d %H:%M")
                        if d["updated_at"] > 0 else ""
                    ),
                    created_by_email=d.get("created_by_email", ""),
                    created_by_name=d.get("created_by_name", ""),
                    words=len(stripped.split()),
                    is_empty=stripped in ("", "# Start typing your masterpiece..."),
                    snippet="",
                )
            )
            contents[d["doc_id"]] = content
        self._all_docs = all_docs
        self._contents = contents
        self.total_count = len(all_docs)
        self.empty_count = sum(1 for d in all_docs if d["is_empty"])

        # Creator facets: accounts by email, everyone without an email is a guest.
        counts: dict[str, int] = {}
        names: dict[str, str] = {}
        for d in all_docs:
            key = self._creator_key(d)
            counts[key] = counts.get(key, 0) + 1
            if key != "guest" and d["created_by_name"]:
                names.setdefault(key, d["created_by_name"])
        options = [CreatorOption(key="all", label="All", sublabel="", count=len(all_docs))]
        if self.my_email:
            options.append(CreatorOption(
                key="mine", label="Mine", sublabel=self.my_email,
                count=counts.get(f"acct:{self.my_email}", 0),
            ))
        if "guest" in counts:
            options.append(CreatorOption(key="guest", label="Guest", sublabel="Not signed in", count=counts["guest"]))
        accounts = sorted(
            (k for k in counts if k != "guest"),
            key=lambda k: (-counts[k], names.get(k, k).lower()),
        )
        for key in accounts:
            email = key.removeprefix("acct:")
            options.append(CreatorOption(key=key, label=names.get(key) or email, sublabel=email, count=counts[key]))
        self.creator_options = options

        valid_keys = {o["key"] for o in options}
        if self.creator_filter not in valid_keys:
            self.creator_filter = "all"
        self._apply_filters()

    def _apply_filters(self):
        now = time.time()
        day = 86400
        start_of_today = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
        query = self.search.strip().lower()

        result: list[DocListItem] = []
        for d in self._all_docs:
            key = self._creator_key(d)
            if self.creator_filter == "mine":
                if key != f"acct:{self.my_email}":
                    continue
            elif self.creator_filter != "all" and key != self.creator_filter:
                continue

            ts = d["updated_at"]
            if self.time_filter == "today" and ts < start_of_today:
                continue
            if self.time_filter == "7d" and ts < now - 7 * day:
                continue
            if self.time_filter == "30d" and ts < now - 30 * day:
                continue
            if self.time_filter == "older" and ts >= now - 30 * day:
                continue

            if self.only_empty and not d["is_empty"]:
                continue

            snippet = ""
            if query:
                meta = " ".join(
                    (d["title"], d["doc_id"], d["created_by_name"], d["created_by_email"])
                ).lower()
                if query not in meta:
                    content = self._contents.get(d["doc_id"], "")
                    pos = content.lower().find(query)
                    if pos < 0:
                        continue
                    start = max(0, pos - 40)
                    end = min(len(content), pos + len(query) + 60)
                    snippet = (
                        ("…" if start > 0 else "")
                        + " ".join(content[start:end].split())
                        + ("…" if end < len(content) else "")
                    )
            result.append({**d, "snippet": snippet})

        if self.sort_by == "updated_asc":
            result.sort(key=lambda d: d["updated_at"])
        elif self.sort_by == "title_asc":
            result.sort(key=lambda d: d["title"].lower())
        elif self.sort_by == "title_desc":
            result.sort(key=lambda d: d["title"].lower(), reverse=True)
        else:
            result.sort(key=lambda d: d["updated_at"], reverse=True)
        self.documents = result

    @rx.event
    def set_search(self, value: str):
        self.search = value
        self._apply_filters()

    @rx.event
    def set_creator_filter(self, value: str):
        self.creator_filter = value
        self._apply_filters()

    @rx.event
    def set_time_filter(self, value: str):
        self.time_filter = value
        self._apply_filters()

    @rx.event
    def set_sort_by(self, value: str):
        self.sort_by = value
        self._apply_filters()

    @rx.event
    def toggle_only_empty(self):
        self.only_empty = not self.only_empty
        self._apply_filters()

    @rx.event
    def filter_by_creator_of(self, email: str):
        """Row shortcut: show every document from the same creator."""
        self.creator_filter = f"acct:{email}" if email else "guest"
        self._apply_filters()

    @rx.event
    def clear_search(self):
        self.search = ""
        self._apply_filters()
        # The search box is uncontrolled, so clear its DOM value explicitly.
        return rx.set_value(SEARCH_INPUT_ID, "")

    @rx.event
    def reset_filters(self):
        self.search = ""
        self.creator_filter = "all"
        self.time_filter = "any"
        self.only_empty = False
        self._apply_filters()
        return rx.set_value(SEARCH_INPUT_ID, "")

    @rx.event
    async def delete_document(self, doc_id: str):
        """Delete a single document and refresh the list."""
        del DOCUMENTS_STORE[doc_id]
        await self.load_documents()

    @rx.event
    async def delete_filtered_documents(self):
        """Delete every document in the current filtered view."""
        for d in self.documents:
            if d["doc_id"] in DOCUMENTS_STORE:
                del DOCUMENTS_STORE[d["doc_id"]]
        await self.load_documents()

    @rx.event
    async def clear_all_documents(self):
        """Delete ALL documents."""
        DOCUMENTS_STORE.clear()
        await self.load_documents()