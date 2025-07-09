# 1) Start from Astral’s uv image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# 2) Copy only pyproject.toml & uv.lock
COPY pyproject.toml uv.lock ./

# 3) Install exactly what's locked
RUN uv sync --locked

# 4) Copy your app code
COPY . .

# 5) Expose & run via uv run
EXPOSE 5711
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5711", "--workers", "4"]

