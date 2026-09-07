"""Case notes: the wire shape, and what the client does with it.

The thread is read by people deciding whether to trust a segmentation, so two
properties are worth pinning down here rather than discovering in a lab: the
author is never something the client sent, and a note that fails to send is not
quietly lost.
"""

import sys
from pathlib import Path

import pytest

from segqueue import protocol
from segqueue.protocol import NOTE_MAX_CHARS, CaseNote, clean_note

_EXTENSION = Path(__file__).resolve().parents[1] / "slicer" / "SegQueue"
if str(_EXTENSION) not in sys.path:
    sys.path.insert(0, str(_EXTENSION))

from SegQueueLib import SegQueueError  # noqa: E402

from test_segqueue_client import FakeResponse, FakeSession, makeClient  # noqa: E402


# ------------------------------------------------------------------ the shape

def test_a_note_survives_the_round_trip():
    note = CaseNote(id="1", case_id="c1", author="chris", author_id="u1",
                    text="RCA ostium is behind a stent", created_at=1.5)
    assert CaseNote.from_dict(note.to_dict()) == note


def test_a_note_from_an_empty_payload_is_blank_rather_than_a_crash():
    # The panel renders whatever the server sent. A missing field must not be
    # the reason an annotator cannot see the rest of the thread.
    assert CaseNote.from_dict({}) == CaseNote()


def test_the_notes_path_is_keyed_by_case_not_assignment():
    # Per-case is the whole feature: the rework annotator, the reviewer and
    # whoever had it first all read the same thread.
    assert protocol.path(protocol.CASE_NOTES, case_id="abc") == "segqueue/case/abc/notes"


@pytest.mark.parametrize("raw, expected", [
    ("  hello  ", "hello"),
    ("a\r\nb", "a\nb"),
    ("a\rb", "a\nb"),
    ("", ""),
    ("   \n  ", ""),
    (None, ""),
])
def test_clean_note_normalises_what_a_text_box_collects(raw, expected):
    assert clean_note(raw) == expected


def test_clean_note_truncates_rather_than_refuses():
    # Losing the tail of an over-long note is kinder than losing all of it.
    assert len(clean_note("x" * (NOTE_MAX_CHARS + 500))) == NOTE_MAX_CHARS


# ---------------------------------------------------------------- the client

def test_fetching_a_thread_returns_notes_oldest_first():
    rows = [
        CaseNote(id="1", author="ana", text="seed mask is wrong below the crux",
                 created_at=1.0).to_dict(),
        CaseNote(id="2", author="SegQueue", text="reviewer rejected attempt 1",
                 created_at=2.0, system=True).to_dict(),
    ]
    session = FakeSession({("GET", "/case/c1/notes"): FakeResponse(200, rows)})
    notes = makeClient(session).caseNotes("c1")

    assert [n.id for n in notes] == ["1", "2"]
    assert notes[1].system is True
    assert notes[0].author == "ana"


def test_an_empty_thread_is_an_empty_list_not_an_error():
    session = FakeSession({("GET", "/case/c1/notes"): FakeResponse(200, [])})
    assert makeClient(session).caseNotes("c1") == []


def test_posting_sends_only_the_text():
    stored = CaseNote(id="9", case_id="c1", author="chris", author_id="u1",
                      text="hello", created_at=3.0).to_dict()
    session = FakeSession({("POST", "/case/c1/notes"): FakeResponse(200, stored)})
    note = makeClient(session).addCaseNote("c1", "  hello  ")

    sent = session.calls[-1]["params"]
    assert sent == {"text": "hello"}
    # Identity is the server's to decide. A client that could name the author
    # could name somebody else as the author.
    assert "author" not in sent and "authorId" not in sent
    assert note.author == "chris" and note.id == "9"


def test_posting_nothing_is_refused_before_a_round_trip():
    session = FakeSession()
    with pytest.raises(SegQueueError):
        makeClient(session).addCaseNote("c1", "   ")
    assert session.calls == []


def test_an_over_long_note_is_trimmed_on_the_way_out():
    stored = CaseNote(id="9", text="x").to_dict()
    session = FakeSession({("POST", "/case/c1/notes"): FakeResponse(200, stored)})
    makeClient(session).addCaseNote("c1", "y" * (NOTE_MAX_CHARS + 100))
    assert len(session.calls[-1]["params"]["text"]) == NOTE_MAX_CHARS


def test_a_refusal_keeps_its_code_so_the_panel_can_tell_them_apart():
    from test_segqueue_client import girderError
    session = FakeSession({
        ("GET", "/case/c1/notes"): girderError(protocol.ERR_NOT_YOUR_CASE,
                                               "not your case", status=403)})
    with pytest.raises(SegQueueError) as caught:
        makeClient(session).caseNotes("c1")
    assert getattr(caught.value, "code", None) == protocol.ERR_NOT_YOUR_CASE
