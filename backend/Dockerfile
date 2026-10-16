# Avoid ghcr.io/astral-sh/uv (slow/unstable from CN VPS). Install uv from a PyPI mirror.
FROM python:3.13-slim

WORKDIR /app

# Tsinghua PyPI mirror + longer timeout (default 30s fails on VPS).
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
    UV_HTTP_TIMEOUT=120 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir "uv==0.9.15"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# CJK fonts for export PNG titles / dialogue (PIL default font cannot render 中文).
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/var/images /app/.data \
    && chown -R app:app /app

USER app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
