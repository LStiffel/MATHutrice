# MATHutrice

LLM-based tutor that helps EPF first-year students practise mathematical tools through notions, competences and training.

Students pick a notion (for example Trigonométrie), see their progression and the competences it evaluates, and train on generated exercises (QCM, open questions, fill-in-the-blanks, step-by-step) with feedback from the LLM. Teachers upload course PDFs. The domain vocabulary is defined in [`CONTEXT.md`](CONTEXT.md), and architecture decisions are recorded in [`docs/adr/`](docs/adr/).

The application is a FastAPI app (`mathutrice/app.py`) with Jinja templates, SQLModel for storage, and an OpenAI-compatible client for every LLM call ([ADR 0002](docs/adr/0002-openai-compatible-llm-client.md)).

## Run it locally

You need [uv](https://docs.astral.sh/uv/). It installs the Python version pinned in `.python-version` (3.14) and the dependency versions locked in `uv.lock`.

```sh
git clone -b course-2026 <your fork URL> mathutrice
cd mathutrice
uv sync
cp .env.example .env
```

If `uv sync` reports `No interpreter found for Python 3.14.7`, your uv predates that Python release: run `uv self update`, then `uv sync` again. Without uv, `pip install -e .` in a virtual environment running Python 3.14 installs the project from `pyproject.toml` instead of the lockfile.

In `.env`, set `LLM_API_KEY` to a key for your **LLM endpoint**. The default endpoint is Mistral: get a key at <https://console.mistral.ai> (a free account works). The other defaults in `.env.example` run the app locally as they are: SQLite database, **connexion de développement**, no Microsoft Entra ID.

Start the app from the repository root:

```sh
uv run uvicorn mathutrice.app:app --port 8000
```

Then open <http://localhost:8000/>.

On an empty database, startup seeds the reference data (every notion and competence of the referentiel) and, with `AUTH_MODE=dev` only, one user per role: `etudiant@epfedu.fr` (Student), `enseignant@epf.fr` (Teacher) and `admin@epf.fr` (Admin). Under `entra`, no user is seeded, so that no guessable demo Admin exists in production. As soon as any notion or user exists, it seeds nothing.

Run the tests with `uv run pytest`.

To check that the clone works (startup, dev sign-in, LLM endpoint), follow the [smoke test](docs/smoke-test.md).

## Configuration

The app reads its settings from the environment, and loads `.env` at startup. [`.env.example`](.env.example) lists every variable with a comment. A missing `SESSION_SECRET`, `LLM_*` or (in `entra` mode) Entra variable stops startup with a `ValueError` naming it.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` | always | The **LLM endpoint** every LLM call goes through. Change all three together to switch endpoint. |
| `DATABASE_URL` | always | SQLAlchemy URL: SQLite locally, PostgreSQL when deployed. |
| `SESSION_SECRET` | always | Signing key for the session cookie. See [the caveat below](#session_secret-caveat). |
| `AUTH_MODE` | no | `entra` (default) or `dev`. Case and surrounding spaces are ignored; any other value stops startup. |
| `DEV_LOGIN_KEY` | no | Shared key protecting the connexion de développement. Only used when `AUTH_MODE=dev`. |
| `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID` | when `AUTH_MODE=entra` | Microsoft Entra ID app registration. |
| `REDIRECT_URL`, `POST_LOGOUT_REDIRECT_URL` | when `AUTH_MODE=entra` | Where Entra sends the user back after sign-in (the app's `/auth` route) and after logout. |

## Authentication

### Microsoft Entra ID (`AUTH_MODE=entra`, the default)

Production signs users in through Microsoft Entra ID. Only `@epf.fr` and `@epfedu.fr` addresses are accepted. An Admin can use **impersonation** to view the app as another user.

A fork deployed at its own URL needs its own Entra app registration, with `REDIRECT_URL` pointing at `<your URL>/auth`. Without one, use the connexion de développement.

### Connexion de développement (`AUTH_MODE=dev`)

Sign-in without an identity provider: you pick an email address and a role (Student, Teacher or Admin) and are signed in as that user, with no proof of identity. It works without any Entra variable and with an empty database, over plain `http://localhost`. **Never use it in production.**

- `GET /dev/login` lists the existing users grouped by role, each signed in with one click, plus a form for any email, an optional name and a role. Pages that need a signed-in user redirect there (through `/test_login`); JSON endpoints answer `401` instead.
- The email must end in `@epf.fr` or `@epfedu.fr`, as with Entra. A new email creates the user.
- A chosen role is saved on the user. Without a role, an existing user keeps theirs and a new user becomes Student.
- Teachers and Admins land on `/teacher`, Students on `/`.
- Once signed in, a red banner on every page shows who you are signed in as, with a "Changer d'utilisateur" link. `/logout` clears the session and returns to `/`.
- At startup, the app prints `WARNING: AUTH_MODE=dev` and whether `DEV_LOGIN_KEY` is set.

Set `DEV_LOGIN_KEY` on a deployed fork so that casual visitors can't sign in as an Admin. `/dev/login` then asks for the key. Leave it empty locally for open access. In `entra` mode it is ignored, with a warning.

#### Scripted sign-in

`POST /dev/login` takes form fields `email`, and optionally `name`, `role` (case-insensitive) and `key`. On success it answers `303` with the session cookie. Keep the cookie in a jar and send it with later requests. The example reads the key from the shell, not from `.env`: export `DEV_LOGIN_KEY` first, or drop `key` when none is set.

```sh
# Sign in as a Teacher, storing the session cookie in cookies.txt
curl -s -o /dev/null -w '%{http_code}\n' -c cookies.txt \
  --data-urlencode email=alice.martin@epf.fr --data-urlencode 'name=Alice Martin'   --data-urlencode role=Teacher --data-urlencode "key=$DEV_LOGIN_KEY" \
  http://localhost:8000/dev/login

# Act as that user
curl -s -b cookies.txt -c cookies.txt http://localhost:8000/teacher
```

Failures have distinct status codes: `401` for a wrong or missing key, `403` for an email outside the allowed domains, `400` for an invalid role.

#### `SESSION_SECRET` caveat

`DEV_LOGIN_KEY` only guards the sign-in form. The session is a cookie signed with `SESSION_SECRET`, so anyone who knows that secret can forge a session cookie for any user and role and skip `DEV_LOGIN_KEY` entirely. The value in `.env.example` is a public placeholder: on any deployed environment, replace it with a long random secret, for example the output of `python -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Deployment checklist

Before deploying to production:

- [ ] `AUTH_MODE` non défini ou `entra`.
- [ ] `CLIENT_ID`, `CLIENT_SECRET`, `TENANT_ID`, `REDIRECT_URL` and `POST_LOGOUT_REDIRECT_URL` set for the deployed URL.
- [ ] `SESSION_SECRET` set to a random secret, not the placeholder from `.env.example`.
- [ ] `DATABASE_URL` pointing at PostgreSQL.
- [ ] `LLM_API_KEY` set, and `LLM_BASE_URL` / `LLM_MODEL` matching the intended endpoint.

## Contributing

Package boundaries under `mathutrice/` are machine-checked: read [`mathutrice/README.md`](mathutrice/README.md) before adding a package or importing across one.

## License

[MIT](LICENSE)
