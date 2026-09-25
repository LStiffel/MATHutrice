# Smoke test

Manual check that a fresh clone of `course-2026` runs, with no Entra credentials and no committed LLM key. Run it locally and on the Linux host you deploy to.

## 1. Set up

Clone `course-2026` and set it up as described in [Run it locally](../README.md#run-it-locally), up to and including setting `LLM_API_KEY` in `.env`. Leave everything else in `.env` as it is.

## 2. Start

From the repository root:

```sh
uv run uvicorn mathutrice.app:app --port 8000
```

Expected: a `WARNING: AUTH_MODE=dev` line, then `Application startup complete`.

The application must refuse to start when a required setting is missing: with `LLM_API_KEY` emptied, startup fails with `ValueError: LLM_API_KEY missing`.

## 3. Check in the browser

1. Open <http://localhost:8000/>. You are redirected to `/dev/login`, and a red dev-mode banner shows on every page.
2. Sign in as a Student with an address ending in `@epfedu.fr`. You land on the home page.
3. Open the chat and ask a question. The answer appears word by word (streaming).

On a fresh database, `/dev/login` already lists one seeded user per role, and the modules page lists the seeded notions.

Step 3 calls the **LLM endpoint**. An `Erreur: ...` message in the chat means the endpoint, key or model in `.env` is wrong.

## 4. Check from the command line

With the application running:

```sh
curl -s -H 'Content-Type: application/json' -d '{"message":"bonjour"}' \
  http://localhost:8000/chat/complete
```

Expected: `{"ok":true,"response":"..."}` with an answer from the model.
