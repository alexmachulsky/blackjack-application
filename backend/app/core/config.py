from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    # Pydantic v2 style — replaces inner class Config
    model_config = SettingsConfigDict(
        # Search .env in CWD first, then parent dir.
        # Works when pytest runs from backend/ (finds ../.env)
        # and when Docker mounts .env at the container working dir.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        # Ignore env vars (e.g. POSTGRES_USER) not declared as Settings fields
        extra="ignore",
    )

    # --- Database (required — no default prevents accidental misconfiguration) ---
    DATABASE_URL: str

    # --- Security (required — must be explicitly set in every environment) ---
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- Game ---
    INITIAL_BALANCE: float = 1000.0

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"  # development | staging | production

    # --- CORS (comma-separated string parsed into a list) ---
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        """Reject weak or placeholder secret keys at startup."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        weak_values = {"your-secret-key-change-in-production", "secret", "changeme"}
        if v.lower() in weak_values:
            raise ValueError("SECRET_KEY is set to an insecure placeholder value")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def log_level_must_be_valid(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}")
        return v.upper()

    def get_cors_origins(self) -> List[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]


settings = Settings()
