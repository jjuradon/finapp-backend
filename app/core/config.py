from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    # Database
    database_url: str = ""

    # Redis
    redis_url: str = ""

    # RabbitMQ
    rabbitmq_url: str = ""

    # Application
    service_name: str = "finapp-backend"
    log_level: str = "INFO"
    environment: str = "development"

    # OIDC — all required; service fails to start if any is missing
    issuer_url: str = "https://example.com"  # default placeholder
    auth_private_key: str = ""
    auth_public_key: str = ""
    frontend_login_url: str = "http://localhost:5173/login"
    oidc_clients: str = (
        '[{"client_id": "my-client", "redirect_uris": ["https://frontend.example.com/callback"]}]'
    )

    # Token TTLs
    access_token_ttl_seconds: int = 900  # 15 minutes
    id_token_ttl_seconds: int = 900  # 15 minutes
    refresh_token_ttl_days: int = 7
    authorization_code_ttl_seconds: int = 60


settings = Settings()
