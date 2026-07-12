# Multi-stage build: Node builds the frontend, Python serves everything.
# Avoids depending on whether the deploy platform's Python image happens to
# have Node available -- this Dockerfile brings its own.

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000
# $PORT is injected by Render (and most PaaS hosts) at runtime; default to
# 8000 for local `docker run` without one set.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
