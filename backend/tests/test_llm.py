import pytest

pytest.importorskip("httpx")

from app.llm import build_prompt, parse_reasons  # noqa: E402


def test_parse_reasons_handles_good_and_bad_output():
    good = '{"reasons": [{"id": 1, "reason": "You will love it."}, {"id": 99, "reason": "not ours"}]}'
    assert parse_reasons(good, {1, 2}) == {1: "You will love it."}
    assert parse_reasons("not json", {1}) == {}
    assert parse_reasons('{"reasons": [{"id": "x"}]}', {1}) == {}


def test_build_prompt_contains_books():
    prompt = build_prompt("Mood: Cozy", [{"id": 3, "title": "T", "authors": "A", "genres": ["G"], "description": "D"}])
    assert "[id=3] T by A" in prompt and "Mood: Cozy" in prompt
