"""Tests for the refusal path: a question with no relevant support in the
indexed corpus must be refused, never answered with an ungrounded guess."""

from __future__ import annotations

from compliance_copilot.service.query_service import REFUSAL_TEXT, QueryService


def test_out_of_corpus_question_triggers_refusal(query_service: QueryService) -> None:
    answer = query_service.answer_query(
        "What is the best topping to put on a birthday cake for a party?"
    )

    assert answer.refused is True
    assert answer.answer_text == REFUSAL_TEXT
    assert answer.citations == []


def test_in_corpus_question_does_not_trigger_refusal(query_service: QueryService) -> None:
    answer = query_service.answer_query(
        "What is required for enhanced due diligence on high risk customers?"
    )

    assert answer.refused is False
    assert len(answer.citations) > 0
