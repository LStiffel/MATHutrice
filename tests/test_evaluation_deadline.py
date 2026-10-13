"""A student waits at most 5 minutes for an evaluation test, however slow the LLM.

The number is assumption D of the Design Document, EPF-MDE/MATHutrice#64: a
student in the 30-minute session slot gives up after 5 minutes. The calls are
assumption A: 40 for the longest test, 20 questions at about 2 calls each.

The LLM is a fake client, and time passes on a fake clock, so the test takes no
real time and calls no real LLM.
"""

import math
from types import SimpleNamespace

import httpx
import openai
import pytest

from mathutrice.evaluation_deadline import DeadlinePassed, EvaluationDeadline

FIVE_MINUTES = 300.0
CALLS_PER_EVALUATION = 40


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class SlowFakeLLM:
    """Stands in for `openai.OpenAI`: every answer takes `seconds_per_answer`.

    Like the real client, a client nobody configured waits 600 s per attempt and
    retries twice, and a call that outlasts its timeout raises
    `openai.APITimeoutError` once its retries are spent.
    """

    def __init__(
        self,
        clock: FakeClock,
        seconds_per_answer: float,
        timeout: float = 600.0,
        max_retries: int = 2,
        calls_started_at: list[float] | None = None,
    ) -> None:
        self._clock = clock
        self._seconds_per_answer = seconds_per_answer
        self._timeout = timeout
        self._max_retries = max_retries
        self.calls_started_at = [] if calls_started_at is None else calls_started_at
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def with_options(self, *, timeout: float, max_retries: int) -> "SlowFakeLLM":
        return SlowFakeLLM(
            self._clock,
            self._seconds_per_answer,
            timeout,
            max_retries,
            self.calls_started_at,
        )

    def _create(self, *, model: str, messages: list[dict]):
        self.calls_started_at.append(self._clock.now)
        if self._seconds_per_answer <= self._timeout:
            self._clock.now += self._seconds_per_answer
            message = SimpleNamespace(content="une question")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])
        self._clock.now += self._timeout * (1 + self._max_retries)
        raise openai.APITimeoutError(
            request=httpx.Request("POST", "https://llm.invalid/v1/chat/completions")
        )


def sit_longest_evaluation(llm: SlowFakeLLM, clock: FakeClock) -> list[str]:
    """Makes every call of the longest evaluation test, under one deadline."""
    deadline = EvaluationDeadline(llm, "fake-model", clock=clock)
    return [
        deadline.ask("Pose une question.") for _ in range(CALLS_PER_EVALUATION)
    ]


# 20 s an answer is a quick call, but 40 of them take 800 s. Stopping at exactly
# 5 minutes is what tells one deadline over the whole test from a timeout per
# call, and stopping at 5 minutes rather than 30 is what tells it from no
# timeout at all.
@pytest.mark.parametrize(
    "seconds_per_answer",
    [20.0, 90.0, math.inf],
    ids=[
        "each-answer-takes-20-seconds",
        "each-answer-takes-90-seconds",
        "the-first-call-hangs",
    ],
)
def test_a_slow_evaluation_stops_at_five_minutes(seconds_per_answer):
    clock = FakeClock()
    llm = SlowFakeLLM(clock, seconds_per_answer)

    with pytest.raises(DeadlinePassed):
        sit_longest_evaluation(llm, clock)

    assert clock.now == FIVE_MINUTES
    assert all(started < FIVE_MINUTES for started in llm.calls_started_at)


def test_an_evaluation_at_the_measured_speed_gets_every_call():
    # 2.3 s a call is assumption B, measured on 25 September 2026.
    clock = FakeClock()
    llm = SlowFakeLLM(clock, seconds_per_answer=2.3)

    answers = sit_longest_evaluation(llm, clock)

    assert len(answers) == CALLS_PER_EVALUATION
    assert clock.now < FIVE_MINUTES
