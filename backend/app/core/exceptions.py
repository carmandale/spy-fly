"""Custom exceptions for the application."""


class AppException(Exception):
    """Base exception for application errors."""

    pass


class PolygonAPIError(AppException):
    """Raised when Polygon API returns an error."""

    pass


class RateLimitError(AppException):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class ConfigurationError(AppException):
    """Raised when there's a configuration issue."""

    pass


class MarketDataError(AppException):
    """Raised when market data cannot be retrieved."""

    pass
