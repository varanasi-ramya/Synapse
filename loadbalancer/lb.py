"""Synapse Layer 7 Load Balancer.

HTTP/1.1 reverse proxy with round-robin load balancing across backends.
Exposes a /stats endpoint for dashboard integration per docs/stats_schema.md.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from aiohttp import ClientSession, ClientTimeout, web
from aiohttp.typedefs import JSONEncoder


BACKENDS: List[str] = ["backend1", "backend2", "backend3"]
BACKEND_PORT = 8000

rr_cycle = itertools.cycle(BACKENDS)

@dataclass
class Stats:
    total_requests: int = 0
    backend_requests: Dict[str, int] = field(default_factory=lambda: {b: 0 for b in BACKENDS})
    active_connections: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def record_request(self, backend: str) -> None:
        async with self._lock:
            self.total_requests += 1
            self.backend_requests[backend] = self.backend_requests.get(backend, 0) + 1

    async def inc_active(self) -> None:
        async with self._lock:
            self.active_connections += 1

    async def dec_active(self) -> None:
        async with self._lock:
            self.active_connections = max(0, self.active_connections - 1)

    async def snapshot(self) -> Dict:
        async with self._lock:
            return {
                "total_requests": self.total_requests,
                "backend_requests": dict(self.backend_requests),
                "active_connections": self.active_connections,
                "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            }


stats = Stats()


async def get_backend_session() -> ClientSession:
    timeout = ClientTimeout(total=10, connect=3, sock_read=10)
    return ClientSession(timeout=timeout)


def pick_backend() -> str:
    return next(rr_cycle)


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return web.Response(
            status=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
            },
        )
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


async def proxy_handler(request: web.Request) -> web.Response:
    backend_name = pick_backend()
    await stats.record_request(backend_name)
    await stats.inc_active()

    backend_url = f"http://{backend_name}:{BACKEND_PORT}{request.path_qs}"

    start = time.perf_counter()
    try:
        async with await get_backend_session() as session:
            async with session.request(
                method=request.method,
                url=backend_url,
                headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
                data=await request.read() if request.can_read_body else None,
                allow_redirects=False,
            ) as resp:
                body = await resp.read()
                elapsed = time.perf_counter() - start
                print(
                    f"[LB] {request.method} {request.path_qs} -> {backend_name} "
                    f"{resp.status} ({elapsed*1000:.1f}ms)",
                    flush=True,
                )
                return web.Response(
                    status=resp.status,
                    headers=dict(resp.headers),
                    body=body,
                )
    except asyncio.TimeoutError:
        await stats.dec_active()
        return web.Response(status=504, text="Gateway Timeout")
    except Exception as e:
        await stats.dec_active()
        print(f"[LB Error] {backend_name}: {e}", flush=True)
        return web.Response(status=502, text="Bad Gateway")
    finally:
        await stats.dec_active()


async def stats_handler(request: web.Request) -> web.Response:
    snapshot = await stats.snapshot()
    return web.json_response(snapshot)


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy"})


async def init_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/stats", stats_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_route("*", "/{tail:.*}", proxy_handler)
    return app


async def main() -> None:
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    print("==================================================", flush=True)
    print("[LB Started] Layer 7 HTTP proxy on 0.0.0.0:8080", flush=True)
    print(f"[LB Config] Backends: {BACKENDS}:{BACKEND_PORT}", flush=True)
    print("[LB Routes]  GET  /stats   -> dashboard metrics", flush=True)
    print("[LB Routes]  GET  /health  -> LB health", flush=True)
    print("[LB Routes]  *    /*       -> round-robin proxy", flush=True)
    print("==================================================", flush=True)

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await runner.cleanup()
        print("\n[LB Shutdown] Server stopped gracefully.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())