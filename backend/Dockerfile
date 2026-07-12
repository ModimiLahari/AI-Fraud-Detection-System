# Optional: use this instead of render.yaml's native python runtime if you
# prefer a containerized deploy (works on Render "Docker" runtime, Railway,
# Fly.io, or any host that runs a Dockerfile).
#
# Place this file at the root of the backend repo, next to requirements.txt.

FROM python:3.11-slim

WORKDIR /app

# System deps for reportlab font rendering (kept minimal for fast builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Render/Railway inject $PORT at runtime — fall back to 8000 for local docker run
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
