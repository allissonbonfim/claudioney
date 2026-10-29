# --- site (Vite) ---
FROM node:22-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# --- API + workers ---
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir ".[postgres]"
COPY scripts ./scripts
RUN python scripts/fetch_models.py
COPY --from=web /web/dist ./web/dist
ENV FLASH_ENV=production FLASH_DATA_DIR=/data FLASH_MODELS_DIR=/app/models FLASH_WEB_DIST=/app/web/dist
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "flash.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
