# Synapse Architecture

Synapse is a Layer 7 (application-layer) HTTP load balancer written in Python
with `asyncio`. It terminates client TCP connections itself, parses the HTTP
request, picks a backend in round-robin order, forwards the request, and
streams the response back — without ever handing the raw socket to the kernel's
load-balancing machinery.

## Architecture Diagram

```
                            ┌──────────────────────────────┐
                            │           Client             │
                            │   (browser / curl / ab)      │
                            └───────────────┬──────────────┘
                                            │
                                   HTTP (TCP :8080)
                                            │
                            ┌───────────────▼──────────────┐
                            │      Load Balancer (LB)      │
                            │      Python + asyncio         │
                            │      Layer 7, round-robin     │
                            │   SYNALB:8080 -> 127.0.0.1:8080│
                            └───────────────┬──────────────┘
                                            │
                      ┌─────────────────────┼─────────────────────┐
                      │                     │                     │
              ┌───────▼────────┐  ┌─────────▼───────┐  ┌──────────▼─────┐
              │   backend1     │  │    backend2     │  │    backend3    │
              │   FastAPI      │  │    FastAPI      │  │    FastAPI     │
              │   :8000        │  │    :8000        │  │    :8000       │
              └────────────────┘  └─────────────────┘  └────────────────┘
                      \                   |                   /
                       \__________________|__________________/
                                          │
                              ┌───────────▼───────────────┐
                              │      lb_network           │
                              │  (Docker bridge network)  │
                              └───────────────────────────┘
```

All three backends and the load balancer share the `lb_network` bridge network.
Containers reach each other by service name (`backend1`, `backend2`,
`backend3`), which Docker's embedded DNS server resolves — no hardcoded IP
addresses anywhere in the project.

## Request Flow

1. The client opens a TCP connection to the load balancer on port `8080`
   (for example `curl http://localhost:8080/`).
2. The client and the load balancer complete the **TCP three-way handshake**
   (`SYN` → `SYN-ACK` → `ACK`), so the LB now owns an established socket.
3. The client sends an **HTTP request** over that connection: a request line
   (`GET / HTTP/1.1`), headers, and a blank line.
4. The load balancer's `asyncio` event loop reads the request bytes off the
   socket and parses them — it is a Layer 7 proxy, so it understands the
   application protocol rather than just relaying packets.
5. The round-robin selector picks the next backend and returns its target
   (for example `backend2:8000`).
6. The load balancer opens a **new TCP connection** to the chosen backend and
   performs another three-way handshake. The DNS lookup for `backend2` is
   resolved by Docker's embedded DNS on `lb_network`.
7. The LB forwards the parsed HTTP request to the backend and awaits the
   response. Because the server is `asyncio`-based, many of these flows are
   in flight concurrently on a single thread.
8. The backend replies with `{"hostname": "synapse_backend2", "backend":
   "backend2"}`, proving which instance served the request. The LB streams
   those bytes back to the client on the original connection.
9. The connections are closed (or returned to a keep-alive pool) and the next
   client request advances the round-robin cursor to `backend3`.

Running several requests with `tests/load_test.sh` makes the cycle visible: the
`backend` field in the responses should read `backend1`, `backend2`,
`backend3`, `backend1`, … in order.

## Networking Concepts Demonstrated

- **TCP three-way handshake** — the load balancer explicitly accepts
  connections and establishes upstream ones, so both halves of every proxied
  request involve a full `SYN`/`SYN-ACK`/`ACK` exchange that can be inspected
  in Wireshark (see `wireshark/`).
- **Sockets and file descriptors** — the LB manages raw TCP sockets itself
  rather than delegating to an OS-level balancer; each client and upstream
  connection consumes a file descriptor, which is why `active_connections` is a
  meaningful metric.
- **Docker bridge networking and embedded DNS** — `lb_network` is a bridge
  network; containers on it address each other by service name, resolved by
  Docker's internal DNS server at `127.0.0.11`.
- **HTTP over TCP** — HTTP is shown to be a text protocol layered on a byte
  stream, which is exactly why a Layer 7 proxy can parse and rewrite requests.
- **Concurrency without threads** — `asyncio` multiplexes thousands of
  in-flight connections on one event loop, giving non-blocking I/O with far
  less memory than a thread-per-connection model.
- **Layer 4 vs Layer 7 balancing** — a Layer 4 balancer would copy packets
  without reading them; a Layer 7 balancer understands the request, which is
  what makes per-request routing, inspection and statistics possible.

Captured traces for these steps belong in `docs/wireshark/`.