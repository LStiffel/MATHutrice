"""One deadline over every LLM call of an evaluation test.

A student waits at most `seconds` for a test: 5 minutes by default, assumption D
of the Design Document, EPF-MDE/MATHutrice#64.
"""

from ._deadline import DEFAULT_SECONDS, DeadlinePassed, EvaluationDeadline

__all__ = ["DEFAULT_SECONDS", "DeadlinePassed", "EvaluationDeadline"]
