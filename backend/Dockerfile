# syntax=docker/dockerfile:1
#
# Synapse backend image.
#
# Each backend container runs the same FastAPI app; the load balancer spreads
# requests across the instances in round-robin order.

FROM python:3.10-slim

# Run as an unprivileged user instead of root (container security best practice).
RUN groupadd --system synapse && useradd --system --gid synapse --home /app synapse

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first so the pip layer is cached and only rebuilt when
# requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY --chown=synapse:synapse main.py .

USER synapse

EXPOSE 8000

# For development you can append "--reload" to hot-reload on code changes.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]