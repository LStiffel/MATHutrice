import time
from collections.abc import Callable

import openai

# Assumption D: a student in the 30-minute slot gives up after 5 minutes.
DEFAULT_SECONDS = 300.0


class DeadlinePassed(Exception):
    """The evaluation's deadline passed: no further LLM call will be made."""


class EvaluationDeadline:
    """Makes the LLM calls of one evaluation test, all under one deadline.

    The clock starts when the deadline is created, at the student's click. Each
    call gets only the time left, as its timeout, with no retry: a retry would
    start the time over. Once the time is up, `ask` starts no call and raises
    `DeadlinePassed`; a call cut short by its timeout raises it too.
    """

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        seconds: float = DEFAULT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._model = model
        self._clock = clock
        self._ends_at = clock() + seconds

    def seconds_left(self) -> float:
        return max(0.0, self._ends_at - self._clock())

    def ask(self, prompt: str) -> str:
        """Returns the LLM's answer to `prompt`, or raises `DeadlinePassed`."""
        left = self.seconds_left()
        if left <= 0:
            raise DeadlinePassed("the evaluation's deadline has passed")
        client = self._client.with_options(timeout=left, max_retries=0)
        try:
            response = client.chat.completions.create(
                model=self._model, messages=[{"role": "user", "content": prompt}]
            )
        except openai.APITimeoutError as error:
            raise DeadlinePassed("the evaluation's deadline has passed") from error
        return response.choices[0].message.content
