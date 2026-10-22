"""The document store on re_ddns: each document is an item of the shared collection
`documents`, kept in memory when it is saved and written to the collection a moment later."""

import json
import time

import pytest
from reflex_ddns_auth.collections import Collection

from codoc_in_md import state
from codoc_in_md.state import DOC_FILE, KIND, _DocumentStore, _ItemDocumentStore


@pytest.fixture
def store(tmp_path, monkeypatch):
    for name in ("DDNS_COLLECTIONS_NODE_URL", "RE_DDNS_API_URL", "DDNS_APP_ID"):
        monkeypatch.delenv(name, raising=False)
    return _ItemDocumentStore(Collection("documents", app_id="md", root=tmp_path / "collections"))


def doc(doc_id, content, email="", name="Guest"):
    """A document as EditorState._save_doc_to_db saves it."""
    return {"doc_id": doc_id, "title": state._extract_title(content), "content": content,
            "updated_at": time.time(), "version": 1, "created_by_email": email, "created_by_name": name}


def manifest(store, doc_id):
    return json.loads((store.items.own_dir / doc_id / ".item" / "manifest.json").read_text())


def test_documents_are_items_of_the_collection(store):
    """doc.md in the item's folder, published once, then revised in place as it is saved."""
    store["a1b2c3d4"] = doc("a1b2c3d4", "# Plan\r\n\r\nfirst", email="amy@example.com", name="Amy")
    folder = store.items.own_dir / "a1b2c3d4"
    assert not folder.exists(), "written a moment later, not while people type"
    assert "a1b2c3d4" in store and store["a1b2c3d4"]["content"] == "# Plan\r\n\r\nfirst"
    store.flush()
    assert sorted(p.name for p in folder.iterdir()) == [".item", DOC_FILE]
    assert (folder / DOC_FILE).read_bytes() == b"# Plan\r\n\r\nfirst"
    m = manifest(store, "a1b2c3d4")
    assert m["kind"] == KIND == "document.markdown" and m["title"] == "Plan" and m["primary"] == DOC_FILE
    assert m["meta"] == {"created_by_email": "amy@example.com", "created_by_name": "Amy"}
    store["a1b2c3d4"] = {**store["a1b2c3d4"], "title": "Plan B", "content": "# Plan B\n"}
    store.flush()
    assert manifest(store, "a1b2c3d4")["revision"] == 2 and (folder / DOC_FILE).read_text() == "# Plan B\n"
    # Another process (a restart) reads it from the collection, \r\n and all.
    again = _ItemDocumentStore(Collection("documents", app_id="md", root=store.items.root))
    got = again["a1b2c3d4"]
    assert (got["title"], got["content"], got["created_by_name"]) == ("Plan B", "# Plan B\n", "Amy")
    assert got["updated_at"] > 0
    assert [d["doc_id"] for d in again.values()] == ["a1b2c3d4"]
    del again["a1b2c3d4"]
    assert not folder.exists() and "a1b2c3d4" not in again and again.values() == []


def test_a_save_is_written_a_moment_later(store, monkeypatch):
    monkeypatch.setattr(state, "SAVE_DELAY", 0.05)
    store["t1"] = doc("t1", "# T\n")
    path = store.items.own_dir / "t1" / DOC_FILE
    deadline = time.time() + 5
    while not path.exists() and time.time() < deadline:
        time.sleep(0.02)
    assert path.read_text() == "# T\n"
    deadline = time.time() + 5
    while store._pending and time.time() < deadline:
        time.sleep(0.02)
    assert store._pending == {}


def test_deleting_wins_over_an_unwritten_save(store):
    store["d1"] = doc("d1", "# D\n")
    del store["d1"]
    store.flush()
    assert not (store.items.own_dir / "d1").exists() and "d1" not in store


def test_a_document_deleted_on_the_storage_page(store):
    """re_ddns's storage page deletes the item while someone still types in it: the next save
    creates it again, as saving does in the database."""
    store["g1"] = doc("g1", "# Gone\n")
    store.flush()
    store.items.remove("g1")
    assert "g1" not in store and store.get("g1") is None
    store["g1"] = doc("g1", "# Gone\nstill typing\n")
    store.flush()
    assert store["g1"]["content"] == "# Gone\nstill typing\n" and manifest(store, "g1")["kind"] == KIND


def test_only_our_own_documents_are_listed(store):
    other = Collection("documents", app_id="someone", root=store.items.root)
    with other.publish("x1", kind=KIND, title="Theirs") as item:
        with item.open(DOC_FILE) as fh:
            fh.write(b"# Theirs\n")
    store["m1"] = doc("m1", "# Mine\n")
    store.flush()
    assert [d["doc_id"] for d in store.values()] == ["m1"]


def test_an_id_that_cannot_name_an_item_stays_in_memory(store):
    store["-x"] = doc("-x", "# Odd\n")
    store.flush()
    assert store["-x"]["content"] == "# Odd\n" and not store.items.own_dir.exists()


def test_the_store_follows_the_install(tmp_path, monkeypatch):
    """The database on its own; items of the collection when re_ddns gives it one."""
    for name in ("DDNS_COLLECTIONS_ROOT", "DDNS_COLLECTIONS_NODE_URL", "RE_DDNS_API_URL"):
        monkeypatch.delenv(name, raising=False)
    assert type(state._make_store()) is _DocumentStore
    monkeypatch.setenv("DDNS_COLLECTIONS_ROOT", str(tmp_path))
    monkeypatch.setenv("DDNS_APP_ID", "md")
    store = state._make_store()
    assert isinstance(store, _ItemDocumentStore)
    assert store.items.own_dir == tmp_path / "documents" / "by-app" / "md"
