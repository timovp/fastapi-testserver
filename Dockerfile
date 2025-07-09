# syntax=docker/dockerfile:1

##################################################
# BUILDER: sync deps & run tests
##################################################
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# 1) Copy lock/manifests
COPY pyproject.toml uv.lock ./

# 2) Install both prod & dev deps
RUN uv sync --locked

# 3) Copy code + tests
COPY . .

# 4)Run pytest suite
RUN uv run pytest -q

##################################################
# RUNTIME: only prod deps & app code
##################################################
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# 1) Copy lock/manifests
COPY pyproject.toml uv.lock ./

# 2) Install prod deps only
RUN uv sync --locked --production

# 3) Copy app code (no tests)
COPY --from=builder /app/main.py ./main.py
COPY --from=builder /app/static ./static
# (and any other folders, e.g. Dockerfile, compose.yml, etc.)

# 4) Expose & run
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app",
     "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

