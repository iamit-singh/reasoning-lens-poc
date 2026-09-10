# Multi-stage: next build --export -> FastAPI static mount (C2.1, C7.3).
# The frontend stage is a placeholder until FE work starts in W5 (post-G1); it builds
# an empty export so the image shape is proven from W1 rather than discovered in W9.

FROM node:22-alpine AS frontend
WORKDIR /src
COPY frontend/package.json ./
RUN npm install --omit=dev --no-audit --no-fund || true
COPY frontend/ ./
RUN mkdir -p out && [ -f next.config.mjs ] && npx next build || echo "frontend not yet implemented (W5)"

FROM python:3.12-slim AS app
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY analyzer/ ./analyzer/
RUN pip install --no-cache-dir ./analyzer
COPY backend/ ./backend/
COPY --from=frontend /src/out ./static/
EXPOSE 8000
CMD ["python", "-m", "rlens", "--help"]
