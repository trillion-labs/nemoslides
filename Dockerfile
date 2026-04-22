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

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY assets/renderer/package.json assets/renderer/package-lock.json ./assets/renderer/
RUN cd assets/renderer && npm ci

COPY . .

EXPOSE ${PORT}

CMD /app/.venv/bin/uvicorn nemoslides.demo.app:app --host 0.0.0.0 --port ${PORT:-8080}
