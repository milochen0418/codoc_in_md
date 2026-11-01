"""AI in the editor, through the AI Hub of re_ddns (``reflex_ddns_auth.ai``): the selected text
rewritten, translated or summed up, and new text at the caret, on the person's word. Which model
answers is chosen on the AI Hub's page (the role ``fast``); the app holds no model, key or address
of its own.

The AI Hub's assistant works on documents through the tools in ``ai_tools``.

Without the platform library, or with no hub to ask (neither ``RE_DDNS_API_URL``, which re_ddns
sets in its apps, nor ``DDNS_AI_HUB_URL``), these features stay hidden.

This module only words the requests and reads the answers; ``ai_state.py`` runs them.
"""

from __future__ import annotations

import difflib
import os
import re
from typing import Any, Dict, List

try:
    from reflex_ddns_auth import ai as hub
except ImportError:  # runs without the platform library: no AI
    hub = None

ENABLED = hub is not None and bool(os.environ.get("RE_DDNS_API_URL") or os.environ.get("DDNS_AI_HUB_URL"))
# This app on the platform, as the AI Hub knows it (its tools' prefix is "md").
APP = (os.environ.get("SERVICE_SUBDOMAIN") or os.environ.get("DDNS_APP_ID") or "md").strip().lower()

ROLE = "fast"
USES = "Rewriting, translating and summing up the text you select in the editor, and writing at the caret"

# What can go wrong while asking.
FAILED = (hub.HubUnavailable,) if hub is not None else ()

# The buttons of the writer: label, and what the AI is asked. With a selection, then at the caret.
ON_SELECTION = {
    "improve": ("Improve", "Rewrite this so that it reads better: clearer and smoother, with the same meaning and about the same length."),
    "fix": ("Fix mistakes", "Correct the spelling, grammar and punctuation. Change nothing else."),
    "shorter": ("Shorter", "Make this shorter. Keep every important point."),
    "longer": ("Longer", "Make this longer, with more explanation. Invent no facts, names or numbers."),
    "english": ("To English", "Translate this into English."),
    "chinese": ("To 繁體中文", "Translate this into Traditional Chinese as used in Taiwan (繁體中文)."),
    "summary": ("Sum up", "Sum this up in two or three sentences, in the language it is written in."),
    "table": ("To a table", "Turn this into a Markdown table."),
}
AT_CARET = {
    "continue": ("Continue writing", "Go on writing from where the text stops, in the same language, style and subject: one paragraph."),
    "outline": ("Outline", "Write an outline for this document as Markdown headings and short bullet points, in the language of the document."),
}

SYSTEM = """\
You are a writing assistant inside a Markdown editor. You change or add one part of a document, as the instruction says.

Your whole answer goes straight into the document, so answer with the new text and nothing else:
- no introduction, no comment, no explanation, no quotation marks around it;
- no code fence around it, unless the text itself is a code block.

Rules:
- Stay in the language of the text. Traditional Chinese stays Traditional Chinese, never Simplified. Translate only when the instruction says so.
- Keep what the text means. Invent no facts, names or numbers.
- Keep its Markdown as it is: headings, lists, links, pictures, code, math, and lines like {%grid ... %}.
- The text around the part is only there so that you understand it: never repeat it."""

CARET = "[[HERE]]"
# Around the text to work on. Words would end up in the answers: a table got the column "PART".
PART_START = "<<<"
PART_END = ">>>"


def prompt(title: str, before: str, selected: str, after: str, request: str) -> str:
    """The request for the selected text (or for the caret, when nothing is selected) with the
    text around it."""
    lines = [f"The document is titled: {title}", ""] if title else []
    if selected:
        lines += ["The document around the text:", "", f"{before}{CARET}{after}".strip(), "", f"The text that goes at {CARET}:", "", PART_START, selected, PART_END, ""]
        lines += [f"Instruction: {request}", "", "Answer with the new text, and nothing else."]
    else:
        lines += ["The document, with the place to write marked " + CARET + ":", "", f"{before}{CARET}{after}".strip() or CARET, ""]
        lines += [f"Instruction: {request}", "", f"Answer with the text that goes in at {CARET}, and nothing else. Don't repeat the text that is already there."]
    return "\n".join(lines)


FENCED = re.compile(r"^```(?:markdown|md|text)?[ \t]*\n(.*)\n```$", re.S)


def cleaned(answer: str, selected: str, before: str = "") -> str:
    """The answer as it goes in the document: without a fence put around all of it, without the
    marks of the request, and with the whitespace the selection had at its ends. At the caret, a
    repeat of the line it goes on (``before`` is the text in front of it) is left out."""
    text = answer.strip()
    if text.startswith(PART_START):
        text = text[len(PART_START) :].lstrip()
    if text.endswith(PART_END):
        text = text[: -len(PART_END)].rstrip()
    fenced = FENCED.match(text)
    if fenced and not selected.lstrip().startswith("```"):
        text = fenced.group(1).strip("\n")
    if not selected.strip():
        line = before.rsplit("\n", 1)[-1].strip()
        return text[len(line) :].lstrip(" ") if line and text.startswith(line) else text
    lead = selected[: len(selected) - len(selected.lstrip())]
    trail = selected[len(selected.rstrip()) :]
    return lead + text + trail


WORDS = re.compile(r"[A-Za-z0-9_]+|\s+|.", re.S)
# Beyond this many words on both sides the difference isn't worked out (it takes too long).
DIFF_MAX = 6000
# When less than this much of the old text stays, the answer is shown as it is, not as a change.
DIFF_MIN_SAME = 0.3
# Below this, what went isn't shown: struck-out words between the new ones make a rewrite unreadable.
DIFF_SHOW_GONE = 0.8


def marks(old: str, new: str) -> List[Dict[str, Any]]:
    """What changed, as runs of text: ``{"op": "same" | "gone" | "new", "text": ...}``. A small
    change shows both sides, a rewrite the new text with what is new in it, and a text that is all
    new (a translation), or that replaces nothing, stands alone."""
    alone = [{"op": "same", "text": new}]
    a, b = WORDS.findall(old), WORDS.findall(new)
    if not a or len(a) + len(b) > DIFF_MAX:
        return alone
    match = difflib.SequenceMatcher(None, a, b, autojunk=False)
    same = match.ratio()
    if same < DIFF_MIN_SAME:
        return alone
    out: List[Dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in match.get_opcodes():
        if tag == "equal":
            out.append({"op": "same", "text": "".join(a[i1:i2])})
            continue
        if tag in ("delete", "replace") and same >= DIFF_SHOW_GONE:
            out.append({"op": "gone", "text": "".join(a[i1:i2])})
        if tag in ("insert", "replace"):
            out.append({"op": "new", "text": "".join(b[j1:j2])})
    return out


def declare(app: Any) -> None:
    """Tells the AI Hub what the editor asks its models for (shown on the hub's page)."""
    if ENABLED:
        hub.uses(app, fast=USES)
