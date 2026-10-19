# Image for the API and the one-shot migrate service. Layout follows uv's Docker guide:
# https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.14.8-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
# Compile bytecode at build time, copy files out of uv's cache mount, and use the image's own Python.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
# Dependencies first, from the lockfile alone, so a code change reuses this layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-editable

FROM python:3.14.8-slim-trixie
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
# Root owns the code and its dependencies; the app user can read them but never change them, read-only filesystem or not.
COPY --from=build /app/.venv /app/.venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
# The root filesystem is read-only at run time, so Python must not try to write .pyc files.
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001
EXPOSE 8000
# One process per container; scale with replicas. Flags: https://www.uvicorn.org/settings/
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", \
     "--loop", "uvloop", "--http", "httptools", "--lifespan", "on", \
     "--limit-concurrency", "200", "--timeout-graceful-shutdown", "20", "--timeout-keep-alive", "75", \
     "--no-access-log", "--no-server-header"]
