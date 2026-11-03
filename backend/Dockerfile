FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

RUN useradd --system --uid 10001 --no-create-home app
RUN chown -R app:app /app
USER app
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://0.0.0.0:8080/healthz || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080"]
