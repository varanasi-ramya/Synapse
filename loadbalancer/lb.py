# loadbalancer/lb.py
import asyncio
import itertools
import sys

# Define backend target instances matching docker-compose service names
BACKENDS = [
    ("backend1", 8000),
    ("backend2", 8000),
    ("backend3", 8000)
]

# Round-robin iterator cycling through backend target indices (0 -> 1 -> 2 -> 0 ...)
rr_cycle = itertools.cycle(BACKENDS)

# Shared counter dictionary for /stats endpoint (Member 2's dashboard integration)
stats = {
    "backend1": 0,
    "backend2": 0,
    "backend3": 0,
    "total_requests": 0
}

async def forward_stream(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Helper function to stream data continuously from reader to writer until EOF.
    """
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass

async def handle_client(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
    """
    Handles incoming TCP client connections on port 8080.
    """
    global stats
    
    # 1. Pick next backend in Round-Robin order
    backend_host, backend_port = next(rr_cycle)
    print(f"[LB] [->] Routing new connection to {backend_host}:{backend_port}", flush=True)

    try:
        # 2. Open an upstream TCP socket connection to the selected backend container
        backend_reader, backend_writer = await asyncio.open_connection(backend_host, backend_port)

        # 3. Increment internal stats counter
        stats[backend_host] += 1
        stats["total_requests"] += 1

        # 4. Bidirectional raw byte forwarding using concurrent tasks
        # Task A: Client -> Backend (Request bytes)
        # Task B: Backend -> Client (Response bytes)
        client_to_backend = asyncio.create_task(forward_stream(client_reader, backend_writer))
        backend_to_client = asyncio.create_task(forward_stream(backend_reader, client_writer))

        # Wait until both streaming directions finish
        await asyncio.gather(client_to_backend, backend_to_client, return_exceptions=True)

        # Gracefully close backend writer
        backend_writer.close()
        await backend_writer.wait_closed()

    except Exception as e:
        print(f"[LB Error] Could not connect or forward to {backend_host}:{backend_port} -> {e}", flush=True)

    finally:
        # Gracefully close client connection
        client_writer.close()
        await client_writer.wait_closed()

async def main():
    # Start non-blocking TCP server listening on port 8080
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8080)
    print("==================================================", flush=True)
    print("[LB Started] Listening on TCP 0.0.0.0:8080 ...", flush=True)
    print(f"[LB Configuration] Active Backends: {BACKENDS}", flush=True)
    print("==================================================", flush=True)

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[LB Shutdown] Server stopped gracefully.")
        sys.exit(0)