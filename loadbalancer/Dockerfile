# syntax=docker/dockerfile:1
#
# Synapse load balancer image.
#
# Runs the asyncio TCP proxy that distributes connections across backends
# in round-robin order.

FROM python:3.10-slim

# Run as an unprivileged user instead of root (container security best practice).
RUN groupadd --system synapse && useradd --system --gid synapse --home /app synapse

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY lb.py .

USER synapse

EXPOSE 8080

CMD ["python", "-u", "lb.py"]