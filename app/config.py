from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "homeworkdrop-super-secure-production-secret-key-change-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "HomeworkDrop"
    APP_ENV: str = "development"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ISSUER: str = "homeworkdrop-api"
    JWT_AUDIENCE: str = "homeworkdrop-frontend"

    AUTH_COOKIE_NAME: str = "access_token"
    AUTH_COOKIE_SECURE: bool = True
    AUTH_COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"
    AUTH_COOKIE_DOMAIN: str | None = None

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.APP_ENV == "production":
            if self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "W środowisku produkcyjnym SECRET_KEY musi być ustawiony na losową wartość (min. 32 znaki)."
                )
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("W środowisku produkcyjnym AUTH_COOKIE_SECURE musi być włączone.")
        if self.AUTH_COOKIE_SAMESITE == "none" and not self.AUTH_COOKIE_SECURE:
            raise ValueError("SameSite=None wymaga flagi Secure.")
        return self


settings = Settings()
