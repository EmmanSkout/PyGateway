# Distributed Rate Limiter Service — Requirements

## Overview
A rate limiting service exposed as a REST API, backed by Redis, implementing multiple rate limiting algorithms with correctness guarantees under concurrent load.

---

## Phase 1 — Core (build this first)

### Functional requirements
1. Expose a REST endpoint: `POST /check`
   - Request body: `{"key": "user:123", "limit": 100, "window_seconds": 60}`
   - Response: `{"allowed": true, "remaining": 42, "reset_at": <timestamp>}` DONE
2. Implement **three algorithms**, selectable per request or per route:
   - Fixed window counter
   - Sliding window log (store timestamps, prune old ones)
   - Token bucket (refill rate + burst capacity)
3. State backend: Redis (`redis-py`, async client). Use Lua scripts (`EVALSHA`) or Redis transactions so check-and-increment is atomic — not racy under concurrent requests.
4. `key` is arbitrary (user id, IP, API key, route name) — the caller decides granularity.

### Non-functional / correctness requirements
5. Must be correct under concurrent load — if 1000 requests hit simultaneously for a key with limit 100, exactly 100 should be allowed, not "approximately." This is the core point of the project.
6. Sub-5ms decision latency at p99 for a single check (locally).

### Deliverables
- FastAPI app with `/check` and `/health`
- Dockerfile + docker-compose (app + Redis)
- Load test script (locust or raw asyncio) proving concurrency correctness — naive impl racing vs Lua-script-fixed impl, clear before/after
- Unit tests for each algorithm's edge cases (window boundaries, burst refill timing)

---

## Phase 2 — Middleware / gateway framing
- Wrap as ASGI middleware so it sits in front of any FastAPI app, not just called out-of-band
- Per-route config (different limits per endpoint)
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (mirror real-world conventions like GitHub's API)

---

## Phase 3 — Distributed / production concerns
- Multiple app instances hitting shared Redis — verify no double-counting
- Redis failure mode: fail-open vs fail-closed, configurable
- Optional: local in-memory cache with short TTL to cut Redis round-trips for hot keys, with correctness tradeoffs documented

---

## Suggested repo structure
```
rate-limiter/
  app/
    main.py
    algorithms/
      fixed_window.py
      sliding_window.py
      token_bucket.py
    redis_client.py
    scripts/          # Lua scripts
  tests/
  loadtest/
  docker-compose.yml
  README.md           # explain the algorithms + benchmark results
```

---

## Suggested build order
1. Fixed window + naive Redis `INCR` — get the endpoint working end to end
2. Swap in the Lua script — measure the race condition disappearing
3. Add sliding window log
4. Add token bucket
5. Load test + write up benchmark results in README
6. Phase 2, then Phase 3 as time allows
