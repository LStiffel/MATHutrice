"""Lets the tests run with no `.env`, as on CI.

Runs before the first import of the Project: `load_dotenv` becomes a no-op, so
a developer's own `.env` cannot leak into a test, and the three LLM settings
`llm_client.py` requires get dummy values, so importing it never fails and never
reaches a real endpoint.
"""

import os

import dotenv

dotenv.load_dotenv = lambda *args, **kwargs: False

os.environ["LLM_BASE_URL"] = "https://llm.invalid/v1"
os.environ["LLM_API_KEY"] = "dummy-key"
os.environ["LLM_MODEL"] = "dummy-model"
