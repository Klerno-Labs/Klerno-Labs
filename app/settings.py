import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and environment variable support."""
    
    # Application
    app_env: str = Field(default="dev", description="Application environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    demo_mode: bool = Field(default=False, description="Enable demo mode")
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # Security
    jwt_secret: str = Field(default="CHANGE_ME_32+", description="JWT secret key")
    access_token_expire_minutes: int = Field(default=60, description="JWT expiration")
    api_key: str = Field(default="dev-api-key", description="API key for authentication")
    
    # Admin
    admin_email: str = Field(default="klerno@outlook.com", description="Admin email")
    boot_admin_password: Optional[str] = Field(default=None, description="Bootstrap admin password")
    
    # Paywall/Stripe
    paywall_code: str = Field(default="Labs2025", description="Paywall bypass code")
    stripe_secret_key: str = Field(default="", description="Stripe secret key")
    stripe_price_id: str = Field(default="", description="Stripe price ID")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook secret")
    
    # External APIs
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model")
    sendgrid_api_key: str = Field(default="", description="SendGrid API key")
    
    # Email settings
    alert_email_from: str = Field(default="alerts@example.com", description="Alert sender email")
    alert_email_to: str = Field(default="you@example.com", description="Alert recipient email")
    
    # Risk analysis
    risk_threshold: float = Field(default=0.75, description="Risk score threshold")
    
    # XRPL settings
    xrpl_rpc_url: str = Field(
        default="https://s2.ripple.com:51234",
        description="XRPL RPC endpoint"
    )
    
    # Database
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    
    # Redis
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(
        default=60,
        description="Rate limit per IP per minute"
    )
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> any:
            """Parse environment variables with type conversion."""
            if field_name == "cors_origins":
                return [origin.strip() for origin in raw_val.split(",")]
            elif field_name in ["debug", "demo_mode", "enable_metrics"]:
                return raw_val.lower() in ("true", "1", "yes", "on")
            return raw_val


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    
    # Validate required settings in production
    if settings.app_env == "production":
        required_prod_settings = [
            ("jwt_secret", "JWT_SECRET"),
            ("api_key", "API_KEY"),
        ]
        
        missing_settings = []
        for field, env_var in required_prod_settings:
            value = getattr(settings, field)
            if not value or value in ["CHANGE_ME_32+", "dev-api-key"]:
                missing_settings.append(env_var)
        
        if missing_settings:
            raise ValueError(f"Missing required production settings: {missing_settings}")
    
    return settings

# Create a global settings instance
settings = get_settings()