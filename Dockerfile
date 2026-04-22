FROM node:20-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/local/bin/python \
    && python -m pip install --break-system-packages --no-cache-dir --upgrade pip uv

WORKDIR /app

# Cache dependency resolution (re-runs only when lock changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Renderer npm deps (re-runs only when package-lock changes).
COPY assets/renderer/package.json assets/renderer/package-lock.json ./assets/renderer/
RUN cd assets/renderer && npm ci

# Copy full source and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD /app/.venv/bin/uvicorn nemoslides.demo.app:app --host 0.0.0.0 --port ${PORT:-8080}
