"""The AI's changes to a document as text: where they go, and how one is taken back.

The AI says what to change by quoting it (``{"find": ..., "replace": ...}``), not by position: the
people on the document go on typing while it works, so only the words themselves still point at
the right place. A change is a list of pieces, ``(start, end, new text)`` in the text as it was.

A change the AI made isn't on anyone's undo: to Monaco it is someone else's edit, so Ctrl+Z
doesn't take it back. So each is remembered here for a while, with what it replaced and the words
around it, for the note on the document with its Undo.

Plain Python without Reflex.
"""

from __future__ import annotations

import dataclasses
import difflib
import re
import threading
import time
import uuid
from typing import Iterable, Optional, Sequence

Piece = tuple[int, int, str]

# Words kept on each side of a change, to find it again.
CONTEXT = 40
# How long a change stays takeable, and how many of a document's.
KEPT_SECONDS = 1800.0
KEPT = 10


def _lines_of(text: str, spots: Iterable[int]) -> str:
    return ", ".join(str(text.count("\n", 0, at) + 1) for at in spots)


def _spot(text: str, find: str, number: int) -> tuple[int, int]:
    """Where the quoted text is. Whitespace may differ (a selection reaches the AI on one line); it
    must be there once; anything else is an error telling the AI what to do about it."""
    if text.count(find) == 1:
        start = text.index(find)
        return start, start + len(find)
    label = f"edit {number}" if number else "the text"
    if text.count(find) > 1:
        lines = _lines_of(text, [m.start() for m in re.finditer(re.escape(find), text)][:8])
        raise ValueError(f"{label}: this text is in the document more than once (lines {lines}): quote more of it, so that it is found once")
    words = find.split()
    if words:
        found = list(re.finditer(r"\s+".join(map(re.escape, words)), text))
        if len(found) == 1:
            return found[0].span()
        if found:
            lines = _lines_of(text, [m.start() for m in found[:8]])
            raise ValueError(f"{label}: this text is in the document more than once (lines {lines}): quote more of it, so that it is found once")
    near = difflib.get_close_matches(find.strip().split("\n")[0], text.split("\n"), n=1, cutoff=0.5)
    hint = f'The closest line in it is: "{near[0][:400]}". Call again with `find` copied exactly from the document.' if near else "Read it, and call again with `find` copied exactly from it."
    raise ValueError(f"{label}: this text isn't in the document, so nothing changed. {hint}")


def _trimmed(text: str, start: int, end: int, new: str) -> Piece:
    """The piece without what stays the same at its ends, so that a change touches only what it
    changes (someone's caret next to it doesn't jump)."""
    while start < end and new and text[start] == new[0]:
        start += 1
        new = new[1:]
    while start < end and new and text[end - 1] == new[-1]:
        end -= 1
        new = new[:-1]
    return start, end, new


def located(text: str, edits: Sequence[dict]) -> list[Piece]:
    """The pieces for a list of ``{"find", "replace"}``, in the order of the text."""
    if not edits:
        raise ValueError('edits is empty: give it at least one {"find": text, "replace": text}')
    pieces: list[Piece] = []
    for number, edit in enumerate(edits, 1):
        find, new = (edit.get("find"), edit.get("replace")) if isinstance(edit, dict) else (None, None)
        if not isinstance(find, str) or not find or not isinstance(new, str):
            raise ValueError(f'edit {number}: each edit is {{"find": text in the document, "replace": what it becomes}}')
        pieces.append(_trimmed(text, *_spot(text, find, number if len(edits) > 1 else 0), new))
    pieces.sort()
    for a, b in zip(pieces, pieces[1:]):
        if a[1] > b[0]:
            raise ValueError("two edits change the same text: make them one edit")
    return [p for p in pieces if p[0] != p[1] or p[2]]


def placed(text: str, new: str, at: str) -> list[Piece]:
    """The piece that puts ``new`` at the end or the start of the text, on lines of its own, or
    makes it the whole text (``at``: "end", "start" or "whole")."""
    if at == "whole":
        piece = _trimmed(text, 0, len(text), new)
        return [piece] if piece[0] != piece[1] or piece[2] else []
    if at == "start":
        return [(0, 0, new.rstrip("\n") + "\n\n")] if text.strip() else [(0, len(text), new)]
    if not text.strip():
        return [(0, len(text), new)]
    gap = "" if text.endswith("\n\n") else "\n" if text.endswith("\n") else "\n\n"
    return [(len(text), len(text), gap + new.lstrip("\n"))]


def spliced(text: str, pieces: Iterable[Piece]) -> str:
    """The text with the pieces in it."""
    for start, end, new in sorted(pieces, reverse=True):
        text = text[:start] + new + text[end:]
    return text


# ------------------------------------------------------------ taking one back


@dataclasses.dataclass
class Spot:
    """A changed place: what was there, what is there now, and the words around it."""

    was: str
    now: str
    left: str
    right: str


@dataclasses.dataclass
class Change:
    """A change the AI made to a document."""

    id: str
    summary: str
    who: str
    spots: list[Spot]
    at: float = dataclasses.field(default_factory=time.time)


def _once(text: str, wanted: str) -> Optional[int]:
    """Where ``wanted`` is in the text, when it is there exactly once."""
    return text.index(wanted) if wanted and text.count(wanted) == 1 else None


def undoing(text: str, spots: Sequence[Spot]) -> Optional[list[Piece]]:
    """The pieces that put back what a change replaced, or None when the text was changed there
    since, so that it can't be told where it goes any more."""
    pieces: list[Piece] = []
    for spot in spots:
        at = _once(text, spot.left + spot.now + spot.right)
        if at is not None:
            at += len(spot.left)
        else:
            at = _once(text, spot.now)
        if at is None:
            return None
        pieces.append((at, at + len(spot.now), spot.was))
    pieces.sort()
    if any(a[1] > b[0] for a, b in zip(pieces, pieces[1:])):
        return None
    return pieces


def spots_of(text: str, pieces: Sequence[Piece]) -> list[Spot]:
    """What :func:`undoing` needs of the pieces just made in ``text``."""
    after = spliced(text, pieces)
    spots = []
    shift = 0
    for start, end, new in sorted(pieces):
        at = start + shift
        stop = at + len(new)
        spots.append(Spot(text[start:end], new, after[max(0, at - CONTEXT) : at], after[stop : stop + CONTEXT]))
        shift += len(new) - (end - start)
    return spots


_lock = threading.Lock()
_changes: dict[str, list[Change]] = {}  # document id -> its latest changes, oldest first


def _prune(now: float) -> None:
    for doc_id in list(_changes):
        kept = [c for c in _changes[doc_id] if now - c.at < KEPT_SECONDS][-KEPT:]
        if kept:
            _changes[doc_id] = kept
        else:
            del _changes[doc_id]


def remember(doc_id: str, summary: str, who: str, text: str, pieces: Sequence[Piece]) -> Change:
    """Keeps a change just made in ``text``, for its note on the document."""
    change = Change(uuid.uuid4().hex[:10], summary, who, spots_of(text, pieces))
    with _lock:
        _changes.setdefault(doc_id, []).append(change)
        _prune(change.at)
    return change


def recent(doc_id: str) -> list[Change]:
    """The document's changes that can still be taken back, the latest first."""
    with _lock:
        _prune(time.time())
        return list(reversed(_changes.get(doc_id, ())))


def find(doc_id: str, change_id: str) -> Optional[Change]:
    return next((c for c in recent(doc_id) if c.id == change_id), None)


def forget(doc_id: str, change_id: str) -> None:
    """The change was taken back."""
    with _lock:
        kept = [c for c in _changes.get(doc_id, ()) if c.id != change_id]
        if kept:
            _changes[doc_id] = kept
        else:
            _changes.pop(doc_id, None)
