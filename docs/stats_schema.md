# Stats Endpoint Schema (Proposed)

This document defines the proposed contract for a `GET /stats` endpoint on the
Synapse load balancer. **This is the interface between the load balancer and the
dashboard**: the dashboard polls `/stats` and renders the payload defined below,
so any change here requires a matching change in `dashboard/`.

Status: **proposed**. The endpoint is not implemented yet.

## Endpoint

```
GET http://<lb-host>:8080/stats
```

The response is `200 OK` with `Content-Type: application/json`.

## JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "SynapseLoadBalancerStats",
  "type": "object",
  "required": [
    "total_requests",
    "backend_requests",
    "active_connections",
    "last_updated"
  ],
  "additionalProperties": false,
  "properties": {
    "total_requests": {
      "type": "integer",
      "minimum": 0,
      "description": "Total requests handled by the load balancer since start."
    },
    "backend_requests": {
      "type": "object",
      "description": "Per-backend request counts keyed by backend hostname.",
      "additionalProperties": {
        "type": "integer",
        "minimum": 0
      }
    },
    "active_connections": {
      "type": "integer",
      "minimum": 0,
      "description": "Client connections currently open by the load balancer."
    },
    "last_updated": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of when these counters were sampled."
    }
  }
}
```

## Fields

| Field | Type | Description |
| --- | --- | --- |
| `total_requests` | integer | Requests the load balancer has accepted and forwarded since process start. Monotonically increasing; resets on restart. |
| `backend_requests` | object | Request count per backend, keyed by the backend's container hostname (for example `synapse_backend1`). Useful for verifying round-robin fairness. |
| `active_connections` | integer | TCP connections the load balancer currently holds open to clients and backends. Acts as the concurrency gauge on the dashboard. |
| `last_updated` | string | ISO 8601 timestamp (for example `2026-10-03T15:04:26Z`) marking when the counters were last refreshed. The dashboard uses it to display data freshness. |

## Example

```json
{
  "total_requests": 1500,
  "backend_requests": {
    "synapse_backend1": 500,
    "synapse_backend2": 500,
    "synapse_backend3": 500
  },
  "active_connections": 42,
  "last_updated": "2026-10-03T15:04:26Z"
}
```

## Notes

- `backend_requests` keys are backend **hostnames**, matching the `hostname`
  value returned by `GET /` on each backend container. The dashboard can join
  the two directly.
- Under an even distribution the per-backend counts stay within one request of
  each other; a wider spread indicates requests were lost or a backend is down.
- Consumers must tolerate unknown extra fields being added later. Producers
  should not remove or rename existing fields without a version bump.
- Timestamps are UTC with a trailing `Z`, so the dashboard does not need to
  guess a timezone.