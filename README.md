# Software-Defined Load Balancer Using Python Asyncio and Docker

A custom Layer 7 (application layer) load balancer, written from scratch with raw TCP sockets in Python, that distributes incoming HTTP traffic across multiple containerized backend servers.

Computer Networks academic project (PBL).

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Testing](#testing)
- [Packet Analysis with Wireshark](#packet-analysis-with-wireshark)
- [Networking Concepts Demonstrated](#networking-concepts-demonstrated)
- [References](#references)

## Overview

- Accepts client connections on port 8080 using `asyncio.start_server()`
- Selects a backend using Round-Robin
- Opens a new TCP connection to the chosen backend (`asyncio.open_connection()`)
- Forwards raw HTTP request bytes and relays the response back to the client
- Runs 3 FastAPI backends in Docker containers on a private bridge network
- Includes a live dashboard showing which backend served each request

No existing load balancer (Nginx, HAProxy) or high-level HTTP library is used for the forwarding logic.

## Features

Core:
- TCP-based load balancer server
- Round-Robin distribution
- Raw byte-stream forwarding
- 3 Dockerized FastAPI backends
- Backends return their own hostname for identification

Advanced (optional):
- Health checks (skip dead backends, resume on recovery)
- Weighted Round-Robin
- Least-Connections algorithm
- Connection retry and failover
- Basic rate limiting

Visualization:
- Live web dashboard (Chart.js) polling `/stats`
- Request counter per backend
- Wireshark capture walkthrough

## Architecture

```
[ Client: Browser / curl / load test script ]
                    |
                    | 1. TCP connection + HTTP request (localhost:8080)
                    v
     +-----------------------------------------+
     |   LOAD BALANCER (Python asyncio, lb.py) |
     |   - Listens on 0.0.0.0:8080             |
     |   - Reads raw HTTP bytes                |
     |   - Round-Robin selects backend         |
     |   - Opens new TCP socket to backend     |
     |   - Logs client IP, backend, timestamp  |
     +-----------------------------------------+
                    |
                    | 2. Forwards bytes over lb_network (Docker bridge)
        +-----------+-----------+
        |           |           |
        v           v           v
   +----------+ +----------+ +----------+
   | backend1 | | backend2 | | backend3 |
   | FastAPI  | | FastAPI  | | FastAPI  |
   |  :8000   | |  :8000   | |  :8000   |
   +----------+ +----------+ +----------+
        |           |           |
        +-----------+-----------+
                    | 3. HTTP response bytes
                    v
     Load balancer writes response to client,
     closes both sockets
                    |
                    v
             [ Client ]

(Optional) Dashboard  <--- polls ---  LB /stats endpoint
```

Request flow:
1. Client opens a TCP connection to `localhost:8080`.
2. `handle_client(reader, writer)` is invoked for that connection.
3. The load balancer reads the raw HTTP request bytes.
4. Round-Robin computes the next backend index.
5. The load balancer opens a new TCP connection to the backend (for example `backend2:8000`) via Docker DNS.
6. Request bytes are written to the backend socket.
7. The backend responds with JSON containing its hostname.
8. Response bytes are read from the backend and written to the client.
9. Both sockets are closed and the event is logged.

## Tech Stack

- Load balancer: Python 3.10+, `asyncio` (standard library)
- Backends: FastAPI, Uvicorn
- Containers: Docker Engine, Docker Compose
- Dashboard: HTML, JavaScript, Chart.js
- Load testing: Apache Bench (`ab`) or a Python script
- Packet analysis: Wireshark
- Version control: Git, GitHub

## Project Structure

```
project/
├── backend/
│   ├── main.py              # FastAPI app: "/" and "/health" routes
│   ├── Dockerfile
│   └── requirements.txt
├── loadbalancer/
│   ├── lb.py                # asyncio TCP server, forwarding, Round-Robin
│   ├── config.py            # Loads backend list
│   ├── health.py            # (Advanced) health-check logic
│   └── backends.json        # Backend targets (host:port)
├── dashboard/
│   ├── index.html
│   ├── app.js               # Polls /stats, renders Chart.js
│   └── style.css
├── tests/
│   ├── test_round_robin.py
│   └── load_test.sh
├── docs/
│   ├── stats_schema.md      # JSON schema for /stats
│   ├── architecture.md
│   └── wireshark/           # .pcapng captures and screenshots
├── docker-compose.yml
├── README.md
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Docker Engine or Docker Desktop
- Docker Compose
- Git
- Wireshark (for packet analysis)
- Apache Bench (optional, for load testing)

Verify installation:

```bash
python3 --version
docker --version
docker-compose --version
git --version
```

### Installation

```bash
git clone <repository-url>
cd project
docker-compose up --build
```

This starts the load balancer, `backend1`, `backend2`, `backend3`, and the private `lb_network` bridge network.

## Usage

Send requests to the load balancer:

```bash
curl http://localhost:8080/
```

Repeat the command; the returned hostname should cycle:
`backend1` -> `backend2` -> `backend3` -> `backend1` ...

Open the dashboard in a browser (see `dashboard/index.html`) to view live request distribution per backend.

Ports:
- `8080`: load balancer (client-facing)
- `8000`: backend containers (internal)

## Testing

| Test | Command / Condition | Expected Result |
|------|---------------------|-----------------|
| Single request | `curl http://localhost:8080/` | 200 OK with one backend hostname |
| Round-Robin | 6 sequential requests | Hostnames cycle 1,2,3,1,2,3 |
| Concurrent clients | `ab -n 100 -c 10 http://localhost:8080/` | All succeed, roughly even distribution |
| Backend down | `docker stop backend2`, then request | Backend skipped (health checks) or clear error logged, no crash |
| Backend recovery | `docker start backend2` | Routing resumes to backend2 |
| Client disconnect | Ctrl+C `curl` mid-request | Backend socket cleaned up, no hang |
| Garbage input | `printf 'garbage' \| nc localhost 8080` | Load balancer does not crash |
| Port conflict | Start a second LB on port 8080 | Clear `OSError`, no silent hang |
| High volume | `ab -n 1000 -c 50 http://localhost:8080/` | Stays responsive; note degradation |
| Oversized payload | POST a very large body | Handled via buffered reads or documented limitation |

Unit tests:

```bash
python -m pytest tests/
```

Report only values actually observed on your machine when documenting performance results.

## Packet Analysis with Wireshark

- Client to load balancer: capture on the loopback interface (`lo` on Linux, `Npcap Loopback Adapter` on Windows) with filter `tcp.port == 8080`
- Load balancer to backend: capture on the Docker bridge interface (for example `docker0`) or run `tcpdump` inside the LB container with filter `tcp.port == 8000`
- Look for: the 3-way handshake (SYN, SYN-ACK, ACK), the plaintext HTTP request (Follow -> TCP Stream), the HTTP response, and FIN/ACK teardown
- Captures and annotated screenshots are stored in `docs/wireshark/`

## Networking Concepts Demonstrated

- TCP three-way handshake and connection lifecycle
- Client-server architecture
- Socket programming with non-blocking `asyncio` sockets
- Ports and IP addressing, including Docker bridge networking and internal DNS
- HTTP message structure over TCP
- Concurrency and multiplexing (many clients, one event loop)
- Load distribution algorithms
- Basic network security (input validation, timeouts, exposed ports)

## References

- Python `asyncio` Streams documentation
- Python `socket` module documentation
- FastAPI and Uvicorn documentation
- Docker Compose and Docker networking documentation
- Wireshark documentation
- RFC 793 (TCP)
- RFC 9110 (HTTP Semantics)
- Apache Bench documentation
- Chart.js documentation
