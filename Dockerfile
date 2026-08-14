FROM python:3.11-slim@sha256:a630a63cdb314e2d138a2fca3e375e319e8568346ffafac5b980f888630ac4f1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.12.1 \
    && uv sync --frozen --no-dev

COPY app ./app
USER 65532:65532
EXPOSE 8080
CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
