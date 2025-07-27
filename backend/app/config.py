from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import field_validator
import json


class Settings(BaseSettings):
    project_name: str = "SPY-FLY"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./spy_fly.db"
    environment: str = "development"
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:3000"]
    
    # Polygon.io settings
    polygon_api_key: str = ""
    polygon_use_sandbox: bool = False
    polygon_rate_limit: int = 5
    polygon_cache_ttl_quote: int = 60
    polygon_cache_ttl_options: int = 300
    polygon_cache_ttl_historical: int = 3600
    
    # Sentiment settings
    sentiment_cache_ttl: int = 300  # 5 minutes
    vix_low_threshold: float = 16.0
    vix_high_threshold: float = 20.0
    futures_bullish_threshold: float = 0.001  # 0.1%
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    bollinger_inner_range: float = 0.4
    sentiment_minimum_score: int = 60
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()