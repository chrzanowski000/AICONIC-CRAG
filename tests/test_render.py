"""Tests for src/render.py: every document shown to the user carries its creation date."""

from src.render import render

CITE_D03 = {"doc_id": "D03", "date": "2025-01-10", "source": "HR Handbook", "claim": "16 weeks."}
CITE_D04 = {"doc_id": "D04", "date": "2025-02-20", "source": "People Ops wiki", "claim": "12 weeks."}


def test_answer_sources_and_outdated_note_show_dates():
    text = render("q", {
        "status": "answered", "answer": "Three days [D02].",
        "citations": [{"doc_id": "D02", "date": "2025-06-15", "source": "HR Handbook",
                       "claim": "Three days."}],
        "outdated": [{"old_id": "D01", "old_date": "2024-03-01", "old_claim": "Two days.",
                      "new_id": "D02", "new_date": "2025-06-15"}],
    })
    assert "[D02] HR Handbook (created 2025-06-15): Three days." in text
    assert "[D01] (created 2024-03-01) said" in text
    assert "replaced by [D02] (created 2025-06-15)" in text


def test_dispute_shows_both_dates():
    text = render("q", {
        "status": "disputed", "versions": [CITE_D03, CITE_D04],
        "differences": ["[D03] (created 2025-01-10) vs [D04] (created 2025-02-20): "
                        "D03 says 16 weeks, D04 says 12 weeks."],
    })
    assert "[D03] HR Handbook (created 2025-01-10): 16 weeks." in text
    assert "[D04] People Ops wiki (created 2025-02-20): 12 weeks." in text
    assert "What differs:" in text
    assert "(created 2025-01-10) vs [D04] (created 2025-02-20)" in text
