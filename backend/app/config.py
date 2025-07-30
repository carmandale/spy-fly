import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "SPY-FLY"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./spy_fly.db"
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = Field(default_factory=list)
    api_port: int = Field(ge=1, le=65535)

    # Polygon.io settings
    polygon_api_key: str = ""
    polygon_use_sandbox: bool = False
    polygon_rate_limit: int = Field(default=5, gt=0)
    polygon_cache_ttl_quote: int = Field(default=60, gt=0)
    polygon_cache_ttl_options: int = Field(default=300, gt=0)
    polygon_cache_ttl_historical: int = Field(default=3600, gt=0)

    # Sentiment settings
    sentiment_cache_ttl: int = Field(default=300, gt=0)  # 5 minutes
    vix_low_threshold: float = Field(default=16.0, gt=0.0)
    vix_high_threshold: float = Field(default=20.0, gt=0.0)
    futures_bullish_threshold: float = Field(default=0.001, gt=0.0)  # 0.1%
    rsi_oversold: int = Field(default=30, ge=1, le=100)
    rsi_overbought: int = Field(default=70, ge=1, le=100)
    bollinger_inner_range: float = Field(default=0.4, gt=0.0, le=1.0)
    sentiment_minimum_score: int = Field(default=60, ge=0, le=100)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            # Try to parse as JSON first
            try:
                origins = json.loads(v)
                if isinstance(origins, list):
                    return origins
            except json.JSONDecodeError:
                pass
            # If not JSON, treat as single origin
            return [v]
        return v

    @field_validator("polygon_api_key")
    @classmethod
    def validate_polygon_api_key(cls, v: str) -> str:
        """Validate Polygon API key format if provided"""
        # Allow empty or short keys for development/testing
        # Actual validation happens in validate_startup_configuration
        return v

    @field_validator("vix_high_threshold")
    @classmethod
    def validate_vix_thresholds(cls, v: float, info) -> float:
        """Ensure VIX high threshold is greater than low threshold"""
        if "vix_low_threshold" in info.data and v <= info.data["vix_low_threshold"]:
            raise ValueError("VIX high threshold must be greater than low threshold")
        return v

    @field_validator("rsi_overbought")
    @classmethod
    def validate_rsi_thresholds(cls, v: int, info) -> int:
        """Ensure RSI overbought is greater than oversold"""
        if "rsi_oversold" in info.data and v <= info.data["rsi_oversold"]:
            raise ValueError("RSI overbought must be greater than oversold")
        return v

    def validate_api_key_for_production(self) -> bool:
        """Check if API key is configured for production use"""
        if self.environment == "production" and not self.polygon_api_key:
            return False
        return True

    def validate_startup_configuration(self) -> tuple[bool, list[str]]:
        """Validate configuration on startup and return status with error messages"""
        errors = []

        # Check API key configuration
        if not self.polygon_api_key:
            errors.append(
                "POLYGON_API_KEY is not configured. Get your free API key at https://polygon.io/"
            )
        elif len(self.polygon_api_key) < 10:
            errors.append("POLYGON_API_KEY appears to be invalid (too short)")

        # Check database configuration
        if not self.database_url:
            errors.append("DATABASE_URL is not configured")

        # Check port configuration
        if self.api_port < 1 or self.api_port > 65535:
            errors.append(f"API_PORT {self.api_port} is invalid (must be 1-65535)")

        # Check VIX thresholds make sense
        if self.vix_high_threshold <= self.vix_low_threshold:
            errors.append(
                f"VIX_HIGH_THRESHOLD ({self.vix_high_threshold}) must be greater than VIX_LOW_THRESHOLD ({self.vix_low_threshold})"
            )

        # Check RSI thresholds make sense
        if self.rsi_overbought <= self.rsi_oversold:
            errors.append(
                f"RSI_OVERBOUGHT ({self.rsi_overbought}) must be greater than RSI_OVERSOLD ({self.rsi_oversold})"
            )

        return len(errors) == 0, errors

    def get_masked_api_key(self) -> str:
        """Return API key with masking for logging purposes"""
        if not self.polygon_api_key:
            return "NOT_SET"
        if len(self.polygon_api_key) < 8:
            return "***"
        return f"{self.polygon_api_key[:4]}...{self.polygon_api_key[-4:]}"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        validate_assignment=True,
         
    )


settings = Settings()
