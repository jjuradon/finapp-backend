from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    app_version: str = "0.1.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    
    allowed_origins: str = ""
    
    db_url_auth: str = ""
    db_url_account: str = ""
    db_url_transaction: str = ""
    db_url_planning: str = ""
    db_url_categorisation: str = ""
    db_url_analytics: str = ""
    
    rabbitmq_url: str = ""
    redis_url: str = ""
    
    auth_private_key: str = ""
    auth_public_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
