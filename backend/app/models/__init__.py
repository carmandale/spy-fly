"""Models package initialization."""

# Import Pydantic models (API schemas)
from app.models.market import (
    Quote,
    QuoteResponse,
    OptionContract as OptionContractSchema,
    OptionChain,
    OptionChainResponse,
    Bar,
    HistoricalDataResponse,
    MarketStatus,
    ErrorResponse
)

from app.models.sentiment import (
    ComponentScore,
    ComponentDetail,
    TechnicalStatus,
    SentimentBreakdown,
    SentimentResult,
    SentimentResponse,
    SentimentConfig
)

# Import SQLAlchemy models (database tables)
from app.models.db_models import (
    MarketDataCache,
    SPYQuote,
    OptionContract,
    HistoricalPrice,
    APIRequestLog
)

__all__ = [
    # Pydantic models
    "Quote",
    "QuoteResponse", 
    "OptionContractSchema",
    "OptionChain",
    "OptionChainResponse",
    "Bar",
    "HistoricalDataResponse",
    "MarketStatus",
    "ErrorResponse",
    "ComponentScore",
    "ComponentDetail",
    "TechnicalStatus",
    "SentimentBreakdown",
    "SentimentResult",
    "SentimentResponse",
    "SentimentConfig",
    # SQLAlchemy models
    "MarketDataCache",
    "SPYQuote",
    "OptionContract",
    "HistoricalPrice",
    "APIRequestLog"
]