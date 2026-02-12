import reflex as rx
import asyncio
import time
import random
import uuid
import logging
from typing import TypedDict, Optional
from pathlib import Path

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


class Document(TypedDict):
    doc_id: str
    content: str
    updated_at: float
    version: int


class User(TypedDict):
    id: str
    name: str
    color: str
    last_seen: float


class DisplayUser(TypedDict):
    id: str
    name: str
    color: str


DOCUMENTS_STORE: dict[str, Document] = {}


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


class SharedState:
    """In-memory state for active users (ephemeral session tracking)."""

    users: dict[str, dict[str, User]] = {}

    @classmethod
    def update_user(cls, doc_id: str, user: User):
        if doc_id not in cls.users:
            cls.users[doc_id] = {}
        cls.users[doc_id][user["id"]] = user

    @classmethod
    def get_active_users(cls, doc_id: str) -> list[User]:
        if doc_id not in cls.users:
            return []
        now = time.time()
        cls.users[doc_id] = {
            uid: u for uid, u in cls.users[doc_id].items() if now - u["last_seen"] < 10
        }
        return list(cls.users[doc_id].values())


class EditorState(rx.State):
    """Manages the collaborative document editor state."""

    doc_id: str = ""
    doc_content: str = ""
    doc_content_rendered: str = ""
    users: list[DisplayUser] = []
    my_user_id: str = ""
    my_user_name: str = ""
    my_user_color: str = ""
    is_connected: bool = False
    is_syncing: bool = False
    is_loading: bool = True
    last_version: int = 0
    view_mode: str = "split"

    # Split-view behavior.
    # When locked, the preview scroll follows the editor scroll (HackMD-like).
    is_scroll_locked: bool = True

    # Monaco editor should be treated as uncontrolled for a stable cursor.
    # We keep an initial seed value that only changes when the document is (re)loaded
    # or when we intentionally refresh the editor (e.g., remote overwrite).
    editor_seed_content: str = ""
    editor_seed_version: int = 0

    @rx.var
    def editor_component_key(self) -> str:
        return f"{self.doc_id}:{self.editor_seed_version}"

    def _generate_user_info(self):
        """Generates a random identity for the session."""
        adjectives = [
            "Cosmic",
            "Digital",
            "Neon",
            "Pixel",
            "Quantum",
            "Retro",
            "Sonic",
            "Techno",
        ]
        nouns = [
            "Coder",
            "Designer",
            "Hacker",
            "Maker",
            "Ninja",
            "Pilot",
            "Wizard",
            "Writer",
        ]
        colors = [
            "#FF5733",
            "#33FF57",
            "#3357FF",
            "#F033FF",
            "#FF33A8",
            "#33FFF5",
            "#F5FF33",
            "#FF8C33",
        ]
        self.my_user_id = str(random.randint(10000, 99999))
        self.my_user_name = f"{random.choice(adjectives)} {random.choice(nouns)}"
        self.my_user_color = random.choice(colors)

    @rx.event
    def create_new_document(self):
        """Creates a new document and redirects to it."""
        new_id = str(uuid.uuid4())[:8]
        return rx.redirect(f"/doc/{new_id}")

    def _get_doc_from_db(self, doc_id: str) -> Optional[Document]:
        """Helper to fetch document from in-memory store."""
        return DOCUMENTS_STORE.get(doc_id)

    def _save_doc_to_db(self, doc_id: str, content: str):
        """Helper to save document to in-memory store."""
        now = time.time()
        if doc_id not in DOCUMENTS_STORE:
            doc: Document = {
                "doc_id": doc_id,
                "content": content,
                "updated_at": now,
                "version": 1,
            }
            DOCUMENTS_STORE[doc_id] = doc
            self.last_version = 1
        else:
            doc = DOCUMENTS_STORE[doc_id]
            doc["content"] = content
            doc["updated_at"] = now
            doc["version"] += 1
            self.last_version = doc["version"]

    @rx.event(background=True)
    async def on_load(self):
        """Initializes the session for the specific document ID."""
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
                return rx.redirect(f"/doc/{new_id}")
            self.doc_id = doc_id
            if not self.my_user_id:
                self._generate_user_info()
            self.is_loading = True

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
        while True:
            async with self:
                if not self.is_syncing:
                    break
                current_doc_id = self.doc_id
                me: User = {
                    "id": self.my_user_id,
                    "name": self.my_user_name,
                    "color": self.my_user_color,
                    "last_seen": time.time(),
                }

            # Keep ephemeral presence tracking server-side.
            SharedState.update_user(current_doc_id, me)
            current_users = SharedState.get_active_users(current_doc_id)
            current_users.sort(key=lambda u: u["name"])

            display_users: list[DisplayUser] = [
                {"id": u["id"], "name": u["name"], "color": u["color"]}
                for u in current_users
            ]

            # Only write to state if something visible changed.
            async with self:
                if not self.is_syncing:
                    break
                if display_users != self.users:
                    self.users = display_users

            # Document sync is now handled by Yjs (CRDT) via
            # assets/yjs_collab.js + the /yjs/{doc_id} WebSocket relay.
            # Only presence tracking remains in this loop.

            await asyncio.sleep(0.5)

    @rx.event
    def update_content(self, new_content: str):
        """Updates the document content locally and persists to in-memory store."""

        self.doc_content = new_content
        self.doc_content_rendered = _render_markdown_source(new_content)
        self._save_doc_to_db(self.doc_id, new_content)

    @rx.event
    def set_view_mode(self, mode: str):
        """Sets the current view mode (editor, split, or preview)."""
        self.view_mode = mode
        # When returning to a view that shows the editor, ensure the Monaco
        # seed matches the latest document content so it doesn't reset.
        if mode in {"editor", "split"}:
            self.editor_seed_content = self.doc_content
            self.editor_seed_version += 1

    @rx.event
    def toggle_scroll_lock(self):
        """Toggles whether preview scroll follows editor scroll in split view."""
        self.is_scroll_locked = not self.is_scroll_locked

    @rx.var
    def user_count(self) -> int:
        """Returns the number of connected users."""
        return len(self.users)