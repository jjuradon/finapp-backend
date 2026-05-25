from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")

    database_url: str
    auth_private_key: str
    redis_url: str
    rabbitmq_url: str
    service_name: str = "finapp-backend"
    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
