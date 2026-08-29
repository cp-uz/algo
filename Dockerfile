FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CPUZ_REPO_ROOT=/app \
    CPUZ_DATABASE_PATH=/data/proposals.sqlite3

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY . .
RUN python scripts/build_static.py \
    && useradd --create-home --uid 10001 cpuz \
    && mkdir -p /data \
    && chown -R cpuz:cpuz /data /app

USER cpuz
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
