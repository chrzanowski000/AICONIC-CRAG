"""Tests for the retry in src/llm.py when OpenRouter puts an error inside a 200 reply."""

import pytest

from src import llm


class FakeRunnable:
    def __init__(self, failures):
        self.failures, self.calls = failures, 0

    def invoke(self, messages):
        self.calls += 1
        if self.calls <= self.failures:
            raise TypeError("'NoneType' object is not iterable")  # what the OpenAI client raises
        return {"parsed": "ok", "raw": None}


def test_an_error_in_the_reply_is_retried(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    runnable = FakeRunnable(failures=2)
    assert llm._invoke_with_retry(runnable, [])["parsed"] == "ok"
    assert runnable.calls == 3


def test_it_gives_up_with_a_clear_error(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    runnable = FakeRunnable(failures=99)
    with pytest.raises(llm.StructuredOutputError, match="error instead of a reply"):
        llm._invoke_with_retry(runnable, [])
    assert runnable.calls == 1 + llm.config.LLM_MAX_RETRIES


def test_other_type_errors_are_not_hidden():
    class Broken:
        def invoke(self, messages):
            raise TypeError("unsupported operand")
    with pytest.raises(TypeError, match="unsupported operand"):
        llm._invoke_with_retry(Broken(), [])
