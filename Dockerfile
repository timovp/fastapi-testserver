# syntax=docker/dockerfile:1

##################################################
# 1) Base image: pinned and slim
##################################################
FROM python:3.11-slim-buster

##################################################
# 2) Create a non-root user
##################################################
RUN groupadd --gid 1000 appuser \
 && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

##################################################
# 3) Environment tweaks
##################################################
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

##################################################
# 4) Set working directory
##################################################
WORKDIR /home/appuser/app

##################################################
# 5) Install dependencies
#    - if you use pip/requirements.txt
##################################################
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# If you’re using Poetry instead, swap in:
# COPY pyproject.toml poetry.lock ./
# RUN pip install --no-cache-dir poetry \
#  && poetry config virtualenvs.create false \
#  && poetry install --no-dev

##################################################
# 6) Copy your application code
##################################################
COPY --chown=appuser:appuser . .

##################################################
# 7) Switch to non-root user
##################################################
USER appuser

##################################################
# 8) Expose internal port
##################################################
EXPOSE 8000

##################################################
# 9) Run the app with Gunicorn + Uvicorn workers
##################################################
CMD ["gunicorn", "main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--keep-alive", "30"]

