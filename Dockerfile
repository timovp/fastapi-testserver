# syntax=docker/dockerfile:1

##################################################
# 1) Base image with uv pre-installed
##################################################
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

##################################################
# 2) Set workdir
##################################################
WORKDIR /app

##################################################
# 3) Copy only lockfile + manifest
##################################################
# This creates a cacheable layer for your deps
COPY uv.lock pyproject.toml ./

##################################################
# 4) Install exactly what's in your lockfile
##################################################
RUN uv sync --locked   # ← will error out if uv.lock is stale :contentReference[oaicite:0]{index=0}

##################################################
# 5) Copy the rest of your application code
##################################################
COPY . .

##################################################
# 6) Expose and run
##################################################
EXPOSE 5711
CMD ["uv", "run", "uvicorn main:app --host 0.0.0.0 --port 5711 --workers 4"]

