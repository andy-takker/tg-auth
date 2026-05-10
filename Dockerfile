# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT="/usr/local/"

WORKDIR /app

# Non-root user for the runtime stage.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

RUN pip install -U pip uv

# Install runtime dependencies (no dev deps inside the image).
COPY pyproject.toml uv.lock /app/
RUN uv sync --no-dev --frozen

# Copy application code.
ARG PROJECT_NAME=tg_auth
COPY ./${PROJECT_NAME} ./${PROJECT_NAME}

USER appuser

EXPOSE 8000

CMD ["python", "-m", "tg_auth"]
