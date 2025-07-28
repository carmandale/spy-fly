"""Polygon.io API client."""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.exceptions import PolygonAPIError, RateLimitError
from app.models.market import Bar, OptionChain, OptionContract, Quote
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class PolygonClient:
    """Client for interacting with Polygon.io API."""

    def __init__(self, api_key: str, use_sandbox: bool = False):
        self.api_key = api_key
        self.use_sandbox = use_sandbox
        self.base_url = "https://api.polygon.io"
        self._client = httpx.AsyncClient(timeout=30.0)

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _make_request(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make HTTP request to Polygon API with retry logic."""
        url = f"{self.base_url}{endpoint}"

        try:
            response = await self._client.get(
                url, headers=self._get_headers(), params=params
            )

            if response.status_code == 429:
                retry_after = int(response.headers.get("X-RateLimit-Reset", 60))
                raise RateLimitError("Rate limit exceeded", retry_after=retry_after)

            response.raise_for_status()
            data = response.json()

            if data.get("status") == "error":
                raise PolygonAPIError(data.get("message", "Unknown API error"))

            return data

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                raise PolygonAPIError("Invalid API key or insufficient permissions")
            elif e.response.status_code == 404:
                raise PolygonAPIError("Resource not found")
            else:
                raise PolygonAPIError(f"API error: {e.response.status_code}")

    async def get_quote(self, ticker: str) -> Quote:
        """Get real-time quote for a ticker using free tier endpoints."""
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"

        data = await self._make_request(endpoint)

        if not data.get("results") or len(data["results"]) == 0:
            raise PolygonAPIError(f"No quote data found for {ticker}")

        result = data["results"][0]

        # Free tier doesn't include v3/quotes, so use what we have from v2/aggs
        return Quote(
            ticker=ticker,
            price=result.get("c", 0),  # Close price as current price
            bid=None,  # Not available in free tier
            ask=None,  # Not available in free tier
            bid_size=None,  # Not available in free tier
            ask_size=None,  # Not available in free tier
            volume=result.get("v", 0),
            high=result.get("h"),
            low=result.get("l"),
            open=result.get("o"),
            close=result.get("c"),
            vwap=result.get("vw"),
            timestamp=datetime.fromtimestamp(result.get("t", 0) / 1000),
        )

    async def get_option_chain(self, ticker: str, expiration: date) -> OptionChain:
        """Get option chain for a specific expiration date."""
        exp_str = expiration.strftime("%Y-%m-%d")
        endpoint = "/v3/reference/options/contracts"

        params = {"underlying_ticker": ticker, "expiration_date": exp_str, "limit": 250}

        data = await self._make_request(endpoint, params)

        if not data.get("results"):
            raise PolygonAPIError(f"No options found for {ticker} expiring {exp_str}")

        # Get current price for underlying
        quote = await self.get_quote(ticker)

        options = []
        for contract in data["results"]:
            # Get option quote
            option_ticker = contract["ticker"]
            try:
                option_quote = await self._make_request(f"/v3/quotes/{option_ticker}")
                quote_data = option_quote.get("results", {})

                option = OptionContract(
                    symbol=option_ticker,
                    type=contract["contract_type"],
                    strike=contract["strike_price"],
                    expiration=exp_str,
                    bid=quote_data.get("bid_price", 0),
                    ask=quote_data.get("ask_price", 0),
                    mid=(
                        quote_data.get("bid_price", 0) + quote_data.get("ask_price", 0)
                    )
                    / 2,
                    last=quote_data.get("last_price"),
                    volume=quote_data.get("day_volume", 0),
                    open_interest=quote_data.get("open_interest", 0),
                )
                options.append(option)
            except Exception:
                # Skip contracts that fail to get quotes
                continue

        return OptionChain(
            ticker=ticker,
            expiration=exp_str,
            underlying_price=quote.price,
            options=options,
        )

    async def get_historical_bars(
        self, ticker: str, from_date: date, to_date: date, timeframe: str = "day"
    ) -> list[Bar]:
        """Get historical price bars."""
        timespan_map = {
            "minute": "minute",
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month",
        }

        timespan = timespan_map.get(timeframe, "day")
        multiplier = 1

        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"

        params = {"adjusted": "true", "sort": "asc", "limit": 5000}

        data = await self._make_request(endpoint, params)

        if not data.get("results"):
            raise PolygonAPIError(f"No historical data found for {ticker}")

        bars = []
        for bar_data in data["results"]:
            bar = Bar(
                timestamp=datetime.fromtimestamp(bar_data["t"] / 1000),
                open=bar_data["o"],
                high=bar_data["h"],
                low=bar_data["l"],
                close=bar_data["c"],
                volume=bar_data["v"],
                vwap=bar_data.get("vw"),
            )
            bars.append(bar)

        return bars

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class PolygonDataService:
    """
    Enhanced Polygon.io service with caching and rate limiting.

    This service wraps the PolygonClient to add:
    - Intelligent caching with TTL support
    - Rate limiting compliance
    - Graceful error handling with fallback to cache
    - Structured logging for monitoring
    """

    def __init__(
        self,
        api_key: str,
        cache_manager: MarketDataCache | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        """
        Initialize the data service with dependencies.

        Args:
            api_key: Polygon.io API key
            cache_manager: Cache manager instance (creates new if None)
            rate_limiter: Rate limiter instance (creates new if None)
        """
        self.client = PolygonClient(api_key=api_key)
        self.cache_manager = cache_manager or MarketDataCache(max_size=1000)
        self.rate_limiter = rate_limiter or RateLimiter(
            requests_per_minute=settings.polygon_rate_limit
        )
        self.api_key = api_key

    async def get_spy_quote(self) -> Quote:
        """
        Get current SPY quote with caching and rate limiting.

        Returns:
            Quote object with current SPY price and metadata

        Raises:
            PolygonAPIError: If API fails and no cached data available
        """
        cache_key = self.cache_manager.generate_key("quote", "SPY")

        # Check cache first
        cached_quote = self.cache_manager.get(cache_key)
        if cached_quote:
            logger.debug(f"Returning cached SPY quote, price: {cached_quote.price}")
            return cached_quote

        # Check rate limit
        wait_time = self.rate_limiter.get_wait_time()
        if wait_time > 0:
            logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)

        try:
            # Consume rate limit token
            if not self.rate_limiter.consume():
                raise RateLimitError("Rate limit exceeded", retry_after=60)

            # Fetch from API
            quote = await self.client.get_quote("SPY")

            # Cache the result
            self.cache_manager.set(
                cache_key, quote, ttl=settings.polygon_cache_ttl_quote
            )

            logger.info(f"Fetched fresh SPY quote: ${quote.price}")
            return quote

        except Exception as e:
            logger.error(f"Failed to fetch SPY quote: {e}")

            # Try to return stale cached data
            stale_quote = self.cache_manager.get(cache_key)
            if stale_quote:
                logger.warning("Returning stale cached quote due to API error")
                return stale_quote

            # Re-raise if no fallback available
            raise PolygonAPIError(f"Failed to fetch SPY quote: {str(e)}")

    async def get_option_chain(
        self, expiration_date: date | None = None
    ) -> list[OptionContract]:
        """
        Get 0-DTE option chain for SPY with caching.

        Args:
            expiration_date: Specific expiration date (defaults to today)

        Returns:
            List of option contracts for the specified date

        Raises:
            PolygonAPIError: If no options found or API error
        """
        # Default to today for 0-DTE
        if expiration_date is None:
            expiration_date = date.today()

        cache_key = self.cache_manager.generate_key(
            "options", "SPY", expiration_date.isoformat()
        )

        # Check cache
        cached_chain = self.cache_manager.get(cache_key)
        if cached_chain:
            logger.debug(f"Returning cached option chain for {expiration_date}")
            return cached_chain

        # Check rate limit
        wait_time = self.rate_limiter.get_wait_time()
        if wait_time > 0:
            logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)

        try:
            # Consume rate limit token
            if not self.rate_limiter.consume():
                raise RateLimitError("Rate limit exceeded", retry_after=60)

            # Fetch from API
            option_chain = await self.client.get_option_chain("SPY", expiration_date)

            # Filter for minimum volume if needed
            filtered_options = [
                opt
                for opt in option_chain.options
                if opt.volume >= 10  # Minimum volume threshold
            ]

            # Cache the result
            self.cache_manager.set(
                cache_key, filtered_options, ttl=settings.polygon_cache_ttl_options
            )

            logger.info(
                f"Fetched {len(filtered_options)} SPY options for {expiration_date}"
            )
            return filtered_options

        except Exception as e:
            logger.error(f"Failed to fetch option chain: {e}")

            # Try stale cache
            stale_chain = self.cache_manager.get(cache_key)
            if stale_chain:
                logger.warning("Returning stale cached option chain due to API error")
                return stale_chain

            raise PolygonAPIError(f"Failed to fetch option chain: {str(e)}")

    async def get_historical_data(self, days: int = 30) -> list[Bar]:
        """
        Get historical price data for SPY with caching.

        Args:
            days: Number of days to look back (default 30, max 90)

        Returns:
            List of price bars for the specified period

        Raises:
            ValueError: If days > 90
            PolygonAPIError: If API fails
        """
        if days > 90:
            raise ValueError("Maximum historical lookback is 90 days")

        to_date = date.today()
        from_date = to_date - timedelta(days=days)

        cache_key = self.cache_manager.generate_key("historical", "SPY", f"{days}d")

        # Check cache
        cached_bars = self.cache_manager.get(cache_key)
        if cached_bars:
            logger.debug(f"Returning cached historical data for {days} days")
            return cached_bars

        # Check rate limit
        wait_time = self.rate_limiter.get_wait_time()
        if wait_time > 0:
            logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)

        try:
            # Consume rate limit token
            if not self.rate_limiter.consume():
                raise RateLimitError("Rate limit exceeded", retry_after=60)

            # Fetch from API
            bars = await self.client.get_historical_bars(
                "SPY", from_date, to_date, "day"
            )

            # Cache the result
            self.cache_manager.set(
                cache_key, bars, ttl=settings.polygon_cache_ttl_historical
            )

            logger.info(f"Fetched {len(bars)} days of historical data")
            return bars

        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")

            # Try stale cache
            stale_bars = self.cache_manager.get(cache_key)
            if stale_bars:
                logger.warning(
                    "Returning stale cached historical data due to API error"
                )
                return stale_bars

            raise PolygonAPIError(f"Failed to fetch historical data: {str(e)}")

    async def health_check(self) -> bool:
        """
        Check if Polygon.io API is accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Use a lightweight endpoint for health check
            await self.client._make_request("/v1/marketstatus/now")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def close(self):
        """Clean up resources."""
        await self.client.close()
