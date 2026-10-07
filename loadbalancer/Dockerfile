# syntax=docker/dockerfile:1
#
# Synapse load balancer image.
#
# Runs the asyncio HTTP Layer 7 proxy that distributes requests across backends
# in round-robin order. Exposes /stats endpoint for dashboard integration.

FROM python:3.10-slim

# Run as an unprivileged user instead of root (container security best practice).
RUN groupadd --system synapse && useradd --system --gid synapse --home /app synapse

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY lb.py .

USER synapse

EXPOSE 8080

CMD ["python", "-u", "lb.py"]