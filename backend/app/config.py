from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", ".env.local", "../.env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str = "redis://redis:6379"

    # App
    client_cors_origin_url: str = "http://localhost:5173"

    gcs_service_account_json: str
    gcs_bucket_name: str
    gcs_bucket_prefix: str = ""

    elevenlabs_api_key: str
    bhashini_api_key: str = ""
    bhashini_user_id: str = ""
    anthropic_api_key: str = ""

    # Auth — Stage 5 (Clerk)
    clerk_secret_key: str
    clerk_jwks_public_key: str

    # Frontend (Stage 4)
    vite_api_server_url: str = "http://localhost:8000"

settings = Settings()
