# Multi-stage: next build --export -> FastAPI static mount.
#
# ADR-003 deleted the cloud deploy, so this image is no longer a release artifact -- it
# exists only so `docker compose up` gives a one-command local demo. The frontend stage is
# a placeholder until FE work starts in W5 (post-G1).
#
# The generation model is NOT baked in or reached from here by default: it is served
# natively on the host so it keeps Metal access. See docker-compose.yml.

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
