"""The AI on documents: where its changes go in the text, how one is taken back, and the visitor that
brings a change into a room of tabs. A tab here is a pycrdt copy behind a socket that behaves as
y-websocket does; a real browser's Yjs is covered by the suite `ai_assist`."""

import asyncio
import time

import pytest
from pycrdt import (
    Doc,
    Text,
    YMessageType,
    YSyncMessageType,
    create_sync_message,
    create_update_message,
    handle_sync_message,
)

from codoc_in_md import ai, ai_edits, ai_tools, state, yjs_ws
from codoc_in_md.ai_edits import located, placed, spliced, undoing, spots_of
from reflex_ddns_auth.tools import ToolContext

AI = ToolContext(user="assistant", caller="ai-hub")


class Tab:
    """A browser tab in a room: it answers the sync, and passes its own changes on."""

    def __init__(self, doc_id, text=None, silent=False):
        self.doc_id = doc_id
        self.ydoc = Doc()
        self.text = self.ydoc.get("monaco", type=Text)
        self.silent = silent
        self.seen = []
        if text:
            self.text.insert(0, text)
        yjs_ws._rooms[doc_id].add(self)

    @property
    def value(self):
        return str(self.text)

    async def send_bytes(self, data):
        self.seen.append(data)
        if data[:1] != bytes([YMessageType.SYNC]):
            return
        reply = handle_sync_message(data[1:], self.ydoc)
        if reply is not None and not self.silent:
            await yjs_ws._broadcast(yjs_ws._rooms[self.doc_id], self, reply)

    async def type(self, at, words):
        before = self.ydoc.get_state()
        self.text.insert(len(self.value[:at].encode("utf-8")), words)
        await yjs_ws._broadcast(yjs_ws._rooms[self.doc_id], self, create_update_message(self.ydoc.get_update(before)))


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(yjs_ws, "WebSocket", Tab)  # a Tab counts as a browser
    monkeypatch.setattr(yjs_ws, "_rooms", yjs_ws.defaultdict(set))
    monkeypatch.setattr(ai_tools, "MARK_SECONDS", 0.0)
    monkeypatch.setattr(ai_tools, "RECONNECT_WAIT", 0.3)
    monkeypatch.setattr(ai_edits, "_changes", {})
    monkeypatch.setattr(state.SharedState, "users", {})


class Store(dict):
    def get(self, key, default=None):
        doc = dict.get(self, key, default)
        return dict(doc) if doc else doc

    def values(self):
        return [dict(d) for d in dict.values(self)]


def save(store, doc_id, content):
    store[doc_id] = dict(doc_id=doc_id, title=state._extract_title(content), content=content, updated_at=time.time(),
                         version=1, created_by_email="", created_by_name="Guest")


@pytest.fixture
def store(monkeypatch):
    s = Store()
    monkeypatch.setattr(ai_tools, "DOCUMENTS_STORE", s)
    return s


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------ where a change goes


def test_a_quoted_piece_is_found_and_only_what_differs_changes():
    text = "# Title\n\nThe cat sat.\n"
    pieces = located(text, [{"find": "The cat sat.", "replace": "The dog sat."}])
    assert pieces == [(9 + 4, 9 + 7, "dog")]
    assert spliced(text, pieces) == "# Title\n\nThe dog sat.\n"


def test_several_edits_go_in_together_and_two_on_the_same_text_are_refused():
    text = "one two three"
    pieces = located(text, [{"find": "three", "replace": "3"}, {"find": "one", "replace": "1"}])
    assert spliced(text, pieces) == "1 two 3"
    with pytest.raises(ValueError, match="same text"):
        located(text, [{"find": "one two", "replace": "x"}, {"find": "two three", "replace": "y"}])


def test_text_found_twice_or_not_at_all_is_an_error_the_ai_can_act_on():
    with pytest.raises(ValueError, match=r"more than once \(lines 1, 3\)"):
        located("same\nother\nsame\n", [{"find": "same", "replace": "x"}])
    with pytest.raises(ValueError, match='closest line in it is: "The quick brown fox"'):
        located("The quick brown fox\nend\n", [{"find": "The quick brown cat", "replace": "x"}])
    for bad in ([], [{"find": "", "replace": "x"}], [{"replace": "x"}], ["x"]):
        with pytest.raises(ValueError):
            located("text", bad)


def test_whitespace_may_differ_in_a_quote():
    """A selection reaches the AI on one line, so a quote of it has no line break."""
    text = "first line\nsecond line\n"
    assert spliced(text, located(text, [{"find": "first line second line", "replace": "both"}])) == "both\n"


def test_nothing_to_change_is_no_piece():
    assert located("same", [{"find": "same", "replace": "same"}]) == []
    assert placed("same", "same", "whole") == []


def test_text_is_added_on_lines_of_its_own():
    assert spliced("one", placed("one", "two", "end")) == "one\n\ntwo"
    assert spliced("one\n", placed("one\n", "two", "end")) == "one\n\ntwo"
    assert spliced("one\n\n", placed("one\n\n", "two", "end")) == "one\n\ntwo"
    assert spliced("one\n", placed("one\n", "two", "start")) == "two\n\none\n"
    assert spliced("  \n", placed("  \n", "two", "end")) == "two"
    assert spliced("old text", placed("old text", "new", "whole")) == "new"


# ------------------------------------------------------------ taking one back


def changed(text, edits):
    pieces = located(text, edits)
    return spliced(text, pieces), spots_of(text, pieces)


def test_a_change_is_taken_back_after_others_wrote_elsewhere():
    text = "# Plan\n\nWe ship in May.\n\nThe end.\n"
    after, spots = changed(text, [{"find": "ship in May", "replace": "ship in June"}])
    later = after.replace("# Plan", "# The plan").replace("The end.", "The very end.")
    assert spliced(later, undoing(later, spots)) == "# The plan\n\nWe ship in May.\n\nThe very end.\n"


def test_a_change_people_wrote_over_is_not_taken_back():
    text = "We ship in May.\n"
    after, spots = changed(text, [{"find": "May", "replace": "June"}])
    assert undoing(after.replace("June", "July"), spots) is None


def test_a_deletion_is_taken_back_by_the_words_around_it():
    text = "keep this remove this keep that\n"
    after, spots = changed(text, [{"find": "remove this ", "replace": ""}])
    assert after == "keep this keep that\n"
    assert spliced(after, undoing(after, spots)) == text


def test_changes_next_to_each_other_are_taken_back_together():
    text = "aaa bbb ccc\n"
    after, spots = changed(text, [{"find": "aaa", "replace": "AAAA"}, {"find": "ccc", "replace": "C"}])
    assert after == "AAAA bbb C\n"
    assert spliced(after, undoing(after, spots)) == text


def test_repeated_text_is_told_apart_by_the_words_around_it():
    text = "item: a\nitem: b\nitem: c\n"
    after, spots = changed(text, [{"find": "item: b", "replace": "item: a"}])
    assert after == "item: a\nitem: a\nitem: c\n"
    assert spliced(after, undoing(after, spots)) == text


def test_only_the_latest_changes_are_kept_for_a_while():
    for n in range(ai_edits.KEPT + 3):
        ai_edits.remember("d", f"change {n}", "AI", "x", [(0, 1, "y")])
    kept = ai_edits.recent("d")
    assert len(kept) == ai_edits.KEPT and kept[0].summary == f"change {ai_edits.KEPT + 2}"
    ai_edits.forget("d", kept[0].id)
    assert ai_edits.find("d", kept[0].id) is None


# ------------------------------------------------------------ a visitor in a room


def test_a_change_reaches_every_tab_and_merges_with_typing():
    async def main():
        first = Tab("d", "# 標題 😀\n\nhello\n")
        second = Tab("d")
        await yjs_ws._broadcast(yjs_ws._rooms["d"], second, create_sync_message(second.ydoc))
        await second.send_bytes(create_sync_message(first.ydoc))
        assert second.value == first.value
        visitor = await yjs_ws.visit("d")
        assert visitor.value == first.value
        await first.type(0, "typed ")  # someone types while it is there: it hears that too
        assert visitor.value == first.value
        text = visitor.value
        at = text.index("hello")
        await visitor.replace([(at, at + 5, "你好 🙂")])
        visitor.leave()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert first.value == second.value == "typed # 標題 😀\n\n你好 🙂\n"
        await second.type(0, "more ")
        assert first.value == "more typed # 標題 😀\n\n你好 🙂\n"
        assert yjs_ws._rooms["d"] == {first, second}

    run(main())


def test_the_marks_of_a_change_count_as_yjs_counts():
    """Yjs ids go by UTF-16 units: the mark ends on the last unit of what was written, after an emoji too."""

    async def main():
        tab = Tab("d", "start end")
        visitor = await yjs_ws.visit("d")
        await visitor.show_as("AI", "#7C3AED")
        await visitor.replace([(6, 6, "😀a")])
        message = next(m for m in reversed(tab.seen) if m[0] == yjs_ws.MESSAGE_AWARENESS)
        state_json = yjs_ws._awareness_clients_in(message)
        assert list(state_json) == [visitor.doc.client_id]
        body = message[message.index(b'{"user"'):].decode("utf-8")
        assert '"selection"' in body and '"clock": 0, ' not in body.split('"head"')[1]
        assert f'"client": {visitor.doc.client_id}, "clock": 2}}, "assoc": -1' in body
        visitor.leave()
        await asyncio.sleep(0.01)
        goodbye = tab.seen[-1]
        assert goodbye[0] == yjs_ws.MESSAGE_AWARENESS and yjs_ws._awareness_clients_in(goodbye)[visitor.doc.client_id][1] is False
        assert not yjs_ws.has_tabs("nobody")

    run(main())


def test_a_room_without_tabs_has_no_visitor():
    assert run(yjs_ws.visit("empty")) is None


def test_a_tab_that_never_answers_stops_the_visit(monkeypatch):
    monkeypatch.setattr(yjs_ws, "JOIN_TIMEOUT", 0.05)

    async def main():
        tab = Tab("d", "text", silent=True)
        with pytest.raises(TimeoutError):
            await yjs_ws.visit("d")
        await asyncio.sleep(0.01)
        assert yjs_ws._rooms["d"] == {tab}

    run(main())


def test_a_tab_with_no_text_yet_is_not_the_answer(monkeypatch):
    """A tab that has only just connected answers with an empty document: the one with the text counts."""
    monkeypatch.setattr(yjs_ws, "JOIN_TIMEOUT", 1.0)

    async def main():
        Tab("d")
        full = Tab("d", "the text")
        visitor = await yjs_ws.visit("d")
        assert visitor.value == "the text" and full.value == "the text"
        visitor.leave()
        await asyncio.sleep(0.01)

    run(main())


# ------------------------------------------------------------ the tools


def test_the_tools_change_a_document_nobody_has_open(store):
    save(store, "d", "# Plan\r\n\r\nWe ship in May.\r\n")

    async def main():
        out = await ai_tools.edit(AI, "d", "Moves the date", [{"find": "May", "replace": "June"}])
        assert out["changed"] == 1 and out["first_changed_line"] == 3
        assert store["d"]["content"] == "# Plan\n\nWe ship in June.\n" and store["d"]["version"] == 2
        await ai_tools.append(AI, "d", "Adds a note", "A note.")
        assert store["d"]["content"] == "# Plan\n\nWe ship in June.\n\nA note."
        note = ai_edits.recent("d")[0]
        assert note.summary == "Adds a note" and note.who == "AI"
        assert await ai_tools.take_back("d", note.id) == ""
        assert store["d"]["content"] == "# Plan\n\nWe ship in June.\n"
        assert [c.summary for c in ai_edits.recent("d")] == ["Moves the date"]

    run(main())


def test_the_tools_go_through_the_tabs_when_a_document_is_open(store):
    save(store, "d", "# Plan\n\nWe ship in May.\n")

    async def main():
        tab = Tab("d", store["d"]["content"])
        await ai_tools.edit(AI, "d", "Moves the date", [{"find": "May", "replace": "六月"}])
        assert tab.value == store["d"]["content"] == "# Plan\n\nWe ship in 六月.\n"
        await tab.type(0, "x")
        why = await ai_tools.take_back("d", ai_edits.recent("d")[0].id)
        assert why == "" and tab.value == "x# Plan\n\nWe ship in May.\n"
        await asyncio.sleep(0.01)
        assert yjs_ws._rooms["d"] == {tab}

    run(main())


def test_a_whole_document_is_rewritten_and_put_back(store):
    save(store, "d", "# Plan\n\nWe ship in May.\n")

    async def main():
        await ai_tools.rewrite(AI, "d", "譯成中文", "# 計畫\n\n我們五月出貨。\n")
        assert store["d"]["content"] == "# 計畫\n\n我們五月出貨。\n" and store["d"]["title"] == "計畫"
        assert await ai_tools.take_back("d", ai_edits.recent("d")[0].id) == ""
        assert store["d"]["content"] == "# Plan\n\nWe ship in May.\n"
        with pytest.raises(ValueError, match="empty"):
            await ai_tools.rewrite(AI, "d", "Empties it", "  \n")

    run(main())


def test_a_change_people_wrote_over_says_so(store):
    save(store, "d", "We ship in May.\n")

    async def main():
        await ai_tools.edit(AI, "d", "Moves the date", [{"find": "May", "replace": "June"}])
        store["d"]["content"] = "We ship in July.\n"
        change = ai_edits.recent("d")[0]
        assert "by hand" in await ai_tools.take_back("d", change.id)
        assert store["d"]["content"] == "We ship in July.\n" and ai_edits.find("d", change.id) is not None

    run(main())


def test_a_refused_edit_changes_nothing(store):
    save(store, "d", "text")

    async def main():
        with pytest.raises(ValueError, match="isn't in the document"):
            await ai_tools.edit(AI, "d", "No", [{"find": "nothing like it", "replace": "x"}])
        with pytest.raises(ValueError, match="no document"):
            await ai_tools.read(AI, "other")
        assert store["d"]["content"] == "text" and ai_edits.recent("d") == []

    run(main())


def test_someone_reconnecting_holds_a_change_back(store):
    """They are on the document and their socket is coming back (the server restarted): what is saved
    now would be overwritten from their tab."""
    save(store, "d", "text")
    now = time.time()
    state.SharedState.users["d"] = {"token": {"id": "1", "name": "Amy", "color": "", "last_seen": now, "avatar_url": "", "joined_at": now, "doc_color": ""}}

    async def main():
        with pytest.raises(ValueError, match="reconnecting"):
            await ai_tools.append(AI, "d", "Adds", "more")

    run(main())
    assert store["d"]["content"] == "text"


def test_reading_gives_the_text_or_some_lines(store):
    save(store, "d", "# One\ntwo\nthree\n")

    async def main():
        whole = await ai_tools.read(AI, "d")
        assert whole["text"] == "# One\ntwo\nthree\n" and whole["lines"] == 4 and whole["title"] == "One"
        part = await ai_tools.read(AI, "d", from_line=2, to_line=3)
        assert part["text"] == "two\nthree" and (part["from_line"], part["to_line"]) == (2, 3)
        with pytest.raises(ValueError, match="has 4 lines"):
            await ai_tools.read(AI, "d", from_line=9)

    run(main())


def test_listing_and_searching(store):
    save(store, "a", "# Alpha\n\nabout cats\n")
    save(store, "b", "# Beta\n\nabout dogs\n")

    async def main():
        assert (await ai_tools.list_documents(AI))["total"] == 2
        found = await ai_tools.list_documents(AI, search="DOGS")
        assert [d["room"] for d in found["documents"]] == ["b"]
        assert found["documents"][0]["title"] == "Beta"

    run(main())


def test_a_new_document_starts_with_its_title(store):
    async def main():
        out = await ai_tools.create(AI, "會議紀錄", "今天的重點")
        assert store[out["room"]]["content"] == "# 會議紀錄\n\n今天的重點\n"
        assert store[out["room"]]["created_by_name"] == "AI" and out["address"].endswith(f"/doc/{out['room']}")
        titled = await ai_tools.create(AI, "x", "# Own heading\n\ntext")
        assert store[titled["room"]]["title"] == "Own heading"

    run(main())


def test_the_ai_shows_among_the_people_on_a_document(store):
    save(store, "d", "text")

    async def main():
        await ai_tools.append(ToolContext(user="my-agent", caller="ai-hub"), "d", "Adds", "more")

    run(main())
    people = state.SharedState.get_active_users("d")
    assert [p["name"] for p in people] == ["AI · my-agent"] and "@" not in people[0]["id"]


def test_tools_say_what_they_do_to_the_hub():
    import reflex as rx
    from reflex_ddns_auth import tools

    ai_tools.register(rx.App())
    made = {t["name"]: t for t in tools.manifest()["tools"] if t["name"].startswith("md.")}
    assert sorted(made) == ["md.append", "md.create", "md.edit", "md.guide", "md.list_documents", "md.read", "md.rewrite"]
    assert {made[n]["kind"] for n in ("md.append", "md.edit", "md.rewrite")} == {"danger"}
    assert {made[n]["kind"] for n in ("md.guide", "md.list_documents", "md.read")} == {"read"}
    assert "room" in made["md.edit"]["input_schema"]["required"]


# ------------------------------------------------------------ the writer's words


def test_an_answer_goes_in_without_what_models_put_around_it():
    assert ai.cleaned("```markdown\nnew text\n```", "old") == "new text"
    assert ai.cleaned("<<<\nnew\n>>>", "old") == "new"
    assert ai.cleaned(">>> x >>> y", "old") == ">>> x >>> y", "only the marks of the request go"
    assert ai.cleaned("  new  ", "\n old \n\n") == "\n new \n\n"
    assert ai.cleaned("```python\nprint(1)\n```", "code") == "```python\nprint(1)\n```"
    assert ai.cleaned("```\ncode\n```", "```\nold\n```") == "```\ncode\n```"


def test_an_answer_at_the_caret_does_not_repeat_the_line_it_goes_on():
    assert ai.cleaned("- 完成測試：先跑一次", "", "## 下週\n\n- 完成測試") == "：先跑一次"
    assert ai.cleaned("Next words.", "", "First words. ") == "Next words."


def test_a_change_shows_what_went_and_what_came():
    runs = ai.marks("We ship in May.", "We ship in June.")
    assert {"op": "gone", "text": "May"} in runs and {"op": "new", "text": "June"} in runs
    assert "".join(r["text"] for r in runs if r["op"] != "gone") == "We ship in June."
    assert "".join(r["text"] for r in runs if r["op"] != "new") == "We ship in May."
    assert ai.marks("中文的句子", "This is all new.") == [{"op": "same", "text": "This is all new."}]
    rewrite = ai.marks("這個禮拜我們把登入的功能做完了", "這週我們已完成登入的功能")
    assert "gone" not in {r["op"] for r in rewrite} and {"same", "new"} == {r["op"] for r in rewrite}
    assert "".join(r["text"] for r in rewrite) == "這週我們已完成登入的功能"
    assert ai.marks("", "at the caret") == [{"op": "same", "text": "at the caret"}]


def test_the_request_carries_the_text_around_the_place():
    asked = ai.prompt("Plan", "before ", "the part", " after", "Shorter.")
    assert "the part" in asked and "before [[HERE]] after" in asked and "Instruction: Shorter." in asked
    at_caret = ai.prompt("", "before ", "", " after", "Go on.")
    assert "before [[HERE]] after" in at_caret and "<<<" not in at_caret
