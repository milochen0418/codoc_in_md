"""ReflexGrid in a document: what `{%grid ...%}` becomes. The line leaves only an empty box in the
document (assets/embed_frames.js keeps the frame over it), and goes through the whole render as typed."""

import re
from urllib.parse import parse_qs, urlparse

import pytest

from codoc_in_md import embeds, state


@pytest.fixture(autouse=True)
def grid(monkeypatch):
    monkeypatch.delenv("DDNS_INTENT_URL_GRID", raising=False)
    monkeypatch.delenv("GRID_BACKEND_URL", raising=False)


def box(line):
    """The frame's address and kind in what the line renders to; None when it stays text."""
    out = state.render_markdown_for_export(line)
    m = re.search(r'data-embed-src="([^"]*)" data-embed-kind="(\w+)"', out)
    if m is None:
        assert line.strip() in out
        return None
    return m[1].replace("&amp;", "&"), m[2]


def test_a_form_is_grid_s_intent_page():
    src, kind = box("{%grid a2094d9b90 form=OrderForm %}")
    url = urlparse(src)
    assert kind == "form"
    assert (url.scheme, url.netloc, url.path) == ("https", "grid.reflex-ddns.com", "/intent/grid-form")
    assert parse_qs(url.query) == {"book": ["a2094d9b90"], "form": ["OrderForm"]}


@pytest.mark.parametrize("ref", ["Orders", "Sheet1!A1:D", "Sheet1!A1:D20", "'Q1 Sales'!A1:D", "'名單 2026'!$A$3:$B", "'It''s'!A:B"])
def test_cells_are_its_read_only_page(ref):
    src, kind = box("{%grid a2094d9b90 range=" + ref + " %}")
    url = urlparse(src)
    assert kind == "table"
    assert url.path == "/_reflex_grid/embed/table"
    assert parse_qs(url.query) == {"book": ["a2094d9b90"], "range": [ref]}


def test_only_a_box_goes_in_the_document():
    out = state.render_markdown_for_export("{%grid b1 range=Orders %}")
    assert "<iframe" not in out and "ReflexGrid: Orders" in out


@pytest.mark.parametrize("line", [
    "{%grid %}",
    "{%grid b1 %}",
    "{%grid b1 other=x %}",
    "{%grid b1 form= %}",
    "{%grid ../x range=A1 %}",
    "{%grid https://example.com/x range=A1 %}",
])
def test_what_it_cant_read_stays_text(line):
    assert box(line) is None


def test_nothing_in_the_line_can_leave_the_attribute():
    out = embeds.GridEmbed().render(embeds.EmbedDirective("grid", 'b1 range="><script>alert(1)</script>', "raw"))
    assert "<script>" not in out


def test_the_address_follows_the_environment(monkeypatch):
    monkeypatch.setenv("DDNS_INTENT_URL_GRID", "http://127.0.0.1:3320")
    monkeypatch.setenv("GRID_BACKEND_URL", "http://127.0.0.1:8320")
    assert box("{%grid b1 form=F %}")[0].startswith("http://127.0.0.1:3320/intent/grid-form?")
    assert box("{%grid b1 range=A1 %}")[0].startswith("http://127.0.0.1:8320/_reflex_grid/embed/table?")


def test_two_on_a_line_and_text_around():
    out = state.render_markdown_for_export("Before\n\n{%grid b1 form=F %}\n{%grid b1 range=T %}\n\nAfter\n")
    assert out.count("data-embed-src") == 2 and "Before" in out and "After" in out
