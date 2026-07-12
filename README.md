# PyGateway

Starter FastAPI project scaffold.

## Quickstart

1. Create and activate a virtual environment.
2. Create your local env file:
   - Copy `.env.example` to `.env`
3. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
4. Run the API:
   - `uvicorn app.main:app --reload`
5. Open docs:
   - Swagger UI: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc

## Configuration

- Runtime settings are defined in `app/config.py`.
- Values are loaded from environment variables and optional `.env`.
- Use `.env.example` as the template for local development.

Available settings:

- `APP_NAME`
- `APP_VERSION`
- `ENVIRONMENT`

You can check the active values at `GET /info`.

## Run checks

- Lint: `ruff check .`
- Tests: `pytest`
