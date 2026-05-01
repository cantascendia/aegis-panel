FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# curl is required by the docker-compose healthcheck (curl -fsS /openapi.json).
# Without it the panel container reports unhealthy even when API is fine.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["sh", "-c", "alembic upgrade head && python3 main.py"]
