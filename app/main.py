from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.algo import dispatch_algo
from app.config import Settings, get_settings
from app.redis import get_redis_client

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)


class CheckGatewayRequest(BaseModel):
    key: str
    algo: str


class GatewayResponse(BaseModel):
    allowed: bool
    remaining: int | float
    reset_at: datetime


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/info", tags=["health"])
def app_info(current_settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "app_name": current_settings.app_name,
        "version": current_settings.app_version,
        "environment": current_settings.environment,
    }


@app.post("/check", tags=["testing"])
async def check_testing(request: CheckGatewayRequest) -> GatewayResponse:
    try:
        result = await dispatch_algo(key=request.key, algo_name=request.algo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GatewayResponse(
        allowed=result.allowed,
        remaining=result.remaining,
        reset_at=result.reset_at,
    )


@app.get("/redis-health", tags=["testing"])
async def redis_test() -> dict[str, str]:
    client = get_redis_client()
    try:
        if await client.ping():
            return {"status": "Redis is reachable"}
        else:
            return {"status": "Redis is not reachable"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Redis connection error: {str(exc)}") from exc
