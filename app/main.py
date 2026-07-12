from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from app.algo import dispatch_algo
from app.config import Settings, get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version=settings.app_version)


class CheckGatewayRequest(BaseModel):
    key: str
    algo: str


class GatewayResponse(BaseModel):
    allowed: bool
    remaining: int
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
def check_testing(request: CheckGatewayRequest) -> GatewayResponse:
    try:
        result = dispatch_algo(key=request.key, algo_name=request.algo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return GatewayResponse(
        allowed=result.allowed,
        remaining=result.remaining,
        reset_at=result.reset_at,
    )
