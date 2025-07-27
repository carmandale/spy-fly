"""Market data service layer."""
from datetime import date, datetime, timedelta
from typing import Optional, List

from app.services.polygon_client import PolygonClient
from app.services.cache import MarketDataCache
from app.services.rate_limiter import RateLimiter
from app.models.market import (
    Quote, QuoteResponse, OptionChain, OptionChainResponse,
    HistoricalDataResponse, Bar
)
from app.config import settings
from app.core.exceptions import MarketDataError


class MarketDataService:
    """Service for fetching and caching market data."""
    
    def __init__(
        self,
        polygon_client: PolygonClient,
        cache: MarketDataCache,
        rate_limiter: RateLimiter
    ):
        self.polygon = polygon_client
        self.cache = cache
        self.rate_limiter = rate_limiter
    
    def _check_market_hours(self) -> str:
        """Determine current market session."""
        now = datetime.now()
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        
        if now.weekday() >= 5:  # Weekend
            return "closed"
        elif now < market_open:
            return "pre-market"
        elif now > market_close:
            return "after-hours"
        else:
            return "regular"
    
    async def get_spy_quote(self) -> QuoteResponse:
        """Get SPY quote with caching and rate limiting."""
        cache_key = self.cache.generate_key("quote", "SPY")
        
        # Check cache first
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return QuoteResponse(**cached_data, cached=True)
        
        # Check rate limit
        if not self.rate_limiter.check():
            # If rate limited, return cached data if available
            if cached_data:
                return QuoteResponse(**cached_data, cached=True)
            
            wait_time = self.rate_limiter.get_wait_time()
            raise MarketDataError(
                f"Rate limit exceeded. Please wait {wait_time:.0f} seconds."
            )
        
        # Consume rate limit token
        self.rate_limiter.consume()
        
        try:
            # Fetch from API
            quote = await self.polygon.get_quote("SPY")
            
            # Calculate change from previous close
            # In production, we'd get this from a previous close endpoint
            previous_close = quote.close or quote.price
            change = quote.price - previous_close
            change_percent = (change / previous_close) * 100 if previous_close > 0 else 0
            
            response = QuoteResponse(
                ticker=quote.ticker,
                price=quote.price,
                bid=quote.bid,
                ask=quote.ask,
                bid_size=quote.bid_size,
                ask_size=quote.ask_size,
                volume=quote.volume,
                timestamp=quote.timestamp.isoformat(),
                market_status=self._check_market_hours(),
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                previous_close=previous_close,
                cached=False
            )
            
            # Cache the response
            self.cache.set(
                cache_key,
                response.model_dump(),
                ttl=settings.polygon_cache_ttl_quote
            )
            
            return response
            
        except Exception as e:
            # If API fails and we have cached data, return it
            if cached_data:
                return QuoteResponse(**cached_data, cached=True)
            raise MarketDataError(f"Failed to fetch quote: {str(e)}")
    
    async def get_spy_options(
        self,
        expiration: date,
        option_type: Optional[str] = None,
        strike_range: Optional[int] = None
    ) -> OptionChainResponse:
        """Get SPY option chain with filtering."""
        cache_key = self.cache.generate_key(
            "options",
            "SPY",
            expiration=expiration.isoformat(),
            option_type=option_type,
            strike_range=strike_range
        )
        
        # Check cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return OptionChainResponse(**cached_data, cached=True)
        
        # Check rate limit
        if not self.rate_limiter.check():
            if cached_data:
                return OptionChainResponse(**cached_data, cached=True)
            
            wait_time = self.rate_limiter.get_wait_time()
            raise MarketDataError(
                f"Rate limit exceeded. Please wait {wait_time:.0f} seconds."
            )
        
        self.rate_limiter.consume()
        
        try:
            # Fetch option chain
            chain = await self.polygon.get_option_chain("SPY", expiration)
            
            # Filter options
            filtered_options = chain.options
            
            if option_type:
                filtered_options = [
                    opt for opt in filtered_options
                    if opt.type == option_type
                ]
            
            if strike_range:
                underlying_price = chain.underlying_price
                min_strike = underlying_price - strike_range
                max_strike = underlying_price + strike_range
                
                filtered_options = [
                    opt for opt in filtered_options
                    if min_strike <= opt.strike <= max_strike
                ]
            
            # Sort by strike
            filtered_options.sort(key=lambda x: x.strike)
            
            cache_expires = datetime.now() + timedelta(
                seconds=settings.polygon_cache_ttl_options
            )
            
            response = OptionChainResponse(
                ticker=chain.ticker,
                underlying_price=chain.underlying_price,
                expiration=chain.expiration,
                options=filtered_options,
                cached=False,
                cache_expires_at=cache_expires.isoformat()
            )
            
            # Cache the response
            self.cache.set(
                cache_key,
                response.model_dump(),
                ttl=settings.polygon_cache_ttl_options
            )
            
            return response
            
        except Exception as e:
            if cached_data:
                return OptionChainResponse(**cached_data, cached=True)
            raise MarketDataError(f"Failed to fetch options: {str(e)}")
    
    async def get_historical_data(
        self,
        days: int,
        timeframe: str = "day"
    ) -> HistoricalDataResponse:
        """Get historical SPY data."""
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        
        cache_key = self.cache.generate_key(
            "historical",
            "SPY",
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            timeframe=timeframe
        )
        
        # Check cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return HistoricalDataResponse(**cached_data, cached=True)
        
        # Check rate limit
        if not self.rate_limiter.check():
            if cached_data:
                return HistoricalDataResponse(**cached_data, cached=True)
            
            wait_time = self.rate_limiter.get_wait_time()
            raise MarketDataError(
                f"Rate limit exceeded. Please wait {wait_time:.0f} seconds."
            )
        
        self.rate_limiter.consume()
        
        try:
            # Fetch historical data
            bars = await self.polygon.get_historical_bars(
                "SPY",
                from_date,
                to_date,
                timeframe
            )
            
            # Convert to response format
            bars_data = [
                {
                    "timestamp": bar.timestamp.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "vwap": bar.vwap
                }
                for bar in bars
            ]
            
            response = HistoricalDataResponse(
                ticker="SPY",
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
                timeframe=timeframe,
                bars=bars_data,
                result_count=len(bars_data),
                cached=False
            )
            
            # Cache the response
            self.cache.set(
                cache_key,
                response.model_dump(),
                ttl=settings.polygon_cache_ttl_historical
            )
            
            return response
            
        except Exception as e:
            if cached_data:
                return HistoricalDataResponse(**cached_data, cached=True)
            raise MarketDataError(f"Failed to fetch historical data: {str(e)}")