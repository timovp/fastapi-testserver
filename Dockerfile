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
# RUNTIME: only prod deps & your app code
##################################################
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# 1) Copy just your lockfile and pyproject so we get a cacheable layer
COPY pyproject.toml uv.lock ./

# 2) Install only your locked, non-dev dependencies
RUN uv sync --locked --no-dev --no-install-project

# 3) Copy your application code
COPY --from=builder /app/main.py      ./main.py
COPY --from=builder /app/static       ./static
# (and any other folders your app needs)

# 4) Expose & run
EXPOSE 5711
CMD ["uv", "run", "uvicorn", "main:app","--host", "0.0.0.0", "--port", "5711", "--workers", "4"]

