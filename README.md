# PyGateway

Simple FastAPI rate-limiter playground.

## What It Does

- Exposes a `/check` endpoint that evaluates a key with a selected algorithm.
- Supports:
  - `fixed_window`
  - `sliding_window`
  - `token_bucket`

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Start the API:
   - `uvicorn app.main:app --reload`
4. Open docs:
   - Swagger UI: http://127.0.0.1:8000/docs

## API

- `GET /health`
  - Basic health check.
- `GET /info`
  - Shows app name/version/environment from settings.
- `POST /check`
  - Request body:
    - `key` (string)
    - `algo` (string)
  - Returns:
    - `allowed`
    - `remaining`
    - `reset_at`

Example request:

```json
{
  "key": "user-123",
  "algo": "fixed_window"
}
```

## Configuration

Settings are defined in `app/config.py` and can be overridden via environment variables.

Core settings:

- `APP_NAME`
- `APP_VERSION`
- `ENVIRONMENT`
- `ALLOWED_ALGOS`

Fixed window:

- `FIXED_WINDOW_LENGTH`
- `FIXED_WINDOW_LIMIT`

Sliding window:

- `SLIDING_WINDOW_LENGTH`
- `SLIDING_WINDOW_THRESHOLD`

Token bucket:

- `TOKEN_BUCKET_REFILL_RATE`
- `TOKEN_BUCKET_BURST_CAPACITY`
- `TOKEN_BUCKET_REFILL_TIME`

## Dev Commands

- Format: `python -m ruff format .`
- Lint: `python -m ruff check .`
- Tests: `pytest`

## Auto-Lint On Commit

To run Ruff auto-fixes and include those fixes in the same commit:

1. Enable repository hooks once:
  - `git config core.hooksPath .githooks`
2. Commit as normal.

The pre-commit hook will:

- run `ruff check . --fix`
- stage tracked file changes from Ruff (`git add -u`)
- run `ruff check .` and block the commit only if lint still fails
