# The image each deploy runs, built once per commit by the `deploy to staging`
# job and promoted unchanged to production.
#
# It starts what the README's launcher starts, `uvicorn mathutrice.app:app`, and
# nothing else: one process, whose lifespan creates the tables, inserts the
# missing reference data, and runs the hourly conversation cleanup on an
# APScheduler thread. One worker only: a second would start a second scheduler.

# The exact Python of .python-version.
FROM python:3.14.7-slim

# uv installs what uv.lock pins: the versions a contributor has locally, with
# nothing resolved at build time.
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /uvx /bin/

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# The dependencies first, without the project: this layer stays cached until
# the lock changes, so a change to the code does not rebuild it.
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# The package carries its templates, static files and reference data.
COPY mathutrice ./mathutrice
RUN uv sync --frozen --no-dev

# No .env in the image (.dockerignore): every setting comes from the app's
# settings, written by each deploy. DATABASE_URL=sqlite:///./mathutrice.db puts
# the database in /app, on the container's own disk: it is created and seeded
# again at every start.

# The commit the image is built from (`--build-arg REVISION=…`). The app sends
# it back in an X-Revision header, so a deploy can tell which image answers,
# not only that one does. Last, so it does not empty the layer cache above.
ARG REVISION=unknown
ENV REVISION=$REVISION

EXPOSE 8000

# App Service terminates TLS in front of the container, at an address known
# only once deployed: uvicorn trusts X-Forwarded-Proto from any address, so
# that a redirect the app builds stays on https.
CMD ["uvicorn", "mathutrice.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
