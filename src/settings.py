from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    default_headers: dict[str, str] = {
        "Cache-Control": "no-cache",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
