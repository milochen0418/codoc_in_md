import reflex as rx
import asyncio
import time
import random
import uuid
import logging
from typing import TypedDict, Optional

from .embeds import apply_hackmd_embeds


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
        async with self:
            if not doc_id:
                new_id = str(uuid.uuid4())[:8]
                return rx.redirect(f"/doc/{new_id}")
            self.doc_id = doc_id
            if not self.my_user_id:
                self._generate_user_info()
            self.is_loading = True
        db_doc = self._get_doc_from_db(doc_id)
        async with self:
            if db_doc:
                self.doc_content = db_doc["content"]
                self.doc_content_rendered = apply_hackmd_embeds(self.doc_content)
                self.last_version = db_doc["version"]
            else:
                default_content = "# Start typing your masterpiece..."
                self.doc_content = default_content
                self.doc_content_rendered = apply_hackmd_embeds(default_content)
                self._save_doc_to_db(doc_id, default_content)
                self.last_version = 1
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

            remote_doc = self._get_doc_from_db(current_doc_id)
            async with self:
                if remote_doc and remote_doc["version"] > self.last_version:
                    if remote_doc["content"] != self.doc_content:
                        self.doc_content = remote_doc["content"]
                        self.doc_content_rendered = apply_hackmd_embeds(self.doc_content)
                        self.last_version = remote_doc["version"]

            await asyncio.sleep(0.5)

    @rx.event
    def update_content(self, new_content: str):
        """
        Updates the document content locally and persists to in-memory store.
        """
        self.doc_content = new_content
        self.doc_content_rendered = apply_hackmd_embeds(new_content)
        self._save_doc_to_db(self.doc_id, new_content)

    @rx.event
    def set_view_mode(self, mode: str):
        """Sets the current view mode (editor, split, or preview)."""
        self.view_mode = mode

    @rx.var
    def user_count(self) -> int:
        """Returns the number of connected users."""
        return len(self.users)