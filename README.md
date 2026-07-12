# PyGateway

Starter FastAPI project scaffold.

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r requirements-dev.txt`
3. Run the API:
   - `uvicorn app.main:app --reload`
4. Open docs:
   - Swagger UI: http://127.0.0.1:8000/docs
   - ReDoc: http://127.0.0.1:8000/redoc

## Run checks

- Lint: `ruff check .`
- Tests: `pytest`
