FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# System packages required for lightgbm wheels (libgomp) and build tooling
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY backend/scripts/android_backend_requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Copy backend code and trained models.
# IMPORTANT: do NOT bake .env (or any secrets) into the image. Pass them at
# deploy time via `gcloud run deploy --set-env-vars` or, preferably,
# `--set-secrets` against Google Secret Manager. Anyone with pull access to
# the container registry can extract files baked into the image.
COPY backend ./backend
COPY trained_models ./backend/trained_models

EXPOSE 8000

CMD ["uvicorn", "backend.scripts.android_backend_server:app", "--host", "0.0.0.0", "--port", "8000"]

