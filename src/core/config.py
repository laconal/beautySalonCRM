from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "production"]
    DATABASE_URL: str
    PRIVATE_KEY_PATH: str
    PUBLIC_KEY_PATH: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_SECONDS: int
    REFRESH_TOKEN_EXPIRE_SECONDS: int
    REDIS_BROKER: str
    REDIS_BACKEND: str

    ADMIN_PRIVATE_KEY_PATH: str
    ADMIN_PUBLIC_KEY_PATH: str
    ADMIN_ALGORITHM: str
    ADMIN_ACCESS_TOKEN_EXPIRE_SECONDS: int
    SQLADMIN_SESSION_SECRET: str

    ERROR_ALERTS_BOT_TOKEN: str | None = None
    ERROR_ALERTS_CHAT_ID: str | None = None

    @property
    def PRIVATE_KEY(self) -> str:
        with open(self.PRIVATE_KEY_PATH, 'r') as f: return f.read()

    @property
    def PUBLIC_KEY(self) -> str:
        with open(self.PUBLIC_KEY_PATH, 'r') as f: return f.read()

    @property
    def ADMIN_PRIVATE_KEY(self) -> str:
        with open(self.ADMIN_PRIVATE_KEY_PATH, 'r') as f: return f.read()

    @property
    def ADMIN_PUBLIC_KEY(self) -> str:
        with open(self.ADMIN_PUBLIC_KEY_PATH, 'r') as f: return f.read()

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra = "ignore")

settings = Settings()