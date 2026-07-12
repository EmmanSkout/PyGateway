from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PyGateway API"
    app_version: str = "0.1.0"
    environment: str = "dev"
    allowed_algos: list[str] = ["fixed_window", "sliding_window"]
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    fixed_window_length: int = 10
    fixed_window_limit: int = 5
    sliding_window_length: int = 10
    sliding_window_threshold: int = 10
    token_bucket_refill_rate: float = 0.5
    token_bucket_burst_capacity: int = 5
    token_bucket_refill_time: int = 2


@lru_cache()
def get_settings() -> Settings:
    return Settings()
