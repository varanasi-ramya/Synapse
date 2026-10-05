"""Synapse backend service.

A minimal FastAPI application that acts as an origin server behind the
Synapse Layer 7 load balancer. Each container runs an identical instance of
this app; the load balancer distributes client requests across them in
round-robin order.

The application exposes two routes:

* ``GET /``       - Returns the container's hostname and backend name so that a
                    client (or the load balancer's log) can prove *which*
                    backend served the request. This is the round-robin
                    verification endpoint used throughout the project.
* ``GET /health`` - A lightweight liveness probe that returns a static
                    ``{"status": "healthy"}`` payload without touching the
                    load-balancing machinery.

The ``BACKEND_NAME`` environment variable is supplied by ``docker-compose.yml``
so each service can identify itself (``backend1``, ``backend2``, ...). If it is
not set the backend name falls back to the container hostname, which keeps the
service usable when run directly with ``uvicorn`` for local debugging.
"""

from __future__ import annotations

import os
import socket

from fastapi import FastAPI

__all__ = ["app", "backend_name", "hostname", "root", "health"]

app = FastAPI(
    title="Synapse Backend",
    version="1.0.0",
    description="Origin server for the Synapse Layer 7 load balancer.",
)


def hostname() -> str:
    """Return the hostname of the machine or container running this service.

    Returns:
        str: The value of the ``HOSTNAME`` environment variable when present,
            otherwise the hostname reported by the operating system via
            :func:`socket.gethostname`.
    """
    return os.getenv("HOSTNAME") or socket.gethostname()


def backend_name() -> str:
    """Return a stable identifier for this backend instance.

    Prefers the ``BACKEND_NAME`` environment variable so that responses read
    ``backend1``, ``backend2`` and so on, and falls back to the container
    hostname when the variable is absent.

    Returns:
        str: The configured backend name, or the container hostname.
    """
    return os.getenv("BACKEND_NAME") or hostname()


@app.get("/")
async def root() -> dict[str, str]:
    """Identify the backend that served this request.

    Returns:
        dict[str, str]: A mapping with the container ``hostname`` and the
            logical ``backend`` name.
    """
    return {"hostname": hostname(), "backend": backend_name()}


@app.get("/health")
async def health() -> dict[str, str]:
    """Report backend liveness.

    Returns:
        dict[str, str]: A mapping with a ``status`` of ``"healthy"``.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # For local development add "--reload" to pick up code changes on save.
    uvicorn.run(app, host="0.0.0.0", port=8000)