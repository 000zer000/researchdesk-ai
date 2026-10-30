FROM node:22-bookworm-slim AS frontend
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
COPY alembic.ini ./
COPY alembic ./alembic
COPY data/sources.json data/manifest.json ./data/
COPY evaluation ./evaluation
COPY --from=frontend /web/dist ./frontend/dist
RUN useradd --uid 10001 --create-home desk && chown -R desk:desk /app
USER desk
EXPOSE 8000
CMD ["uvicorn", "researchdesk.api:app", "--host", "0.0.0.0", "--port", "8000"]
