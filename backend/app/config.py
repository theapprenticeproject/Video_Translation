from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str

    # App
    client_cors_origin_url: str

    gcs_service_account_json: str
    gcs_bucket_name: str

    elevenlabs_api_key: str
    bhashini_api_key: str

    # Frontend (Stage 4)
    vite_api_server_url: str

settings = Settings()
