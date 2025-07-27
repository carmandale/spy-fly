"""Polygon.io API client."""
import httpx
from datetime import date, datetime
from typing import Optional, Dict, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models.market import Quote, OptionChain, OptionContract, Bar
from app.core.exceptions import PolygonAPIError, RateLimitError


class PolygonClient:
    """Client for interacting with Polygon.io API."""
    
    def __init__(self, api_key: str, use_sandbox: bool = False):
        self.api_key = api_key
        self.use_sandbox = use_sandbox
        self.base_url = "https://api.polygon.io"
        self._client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
    )
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request to Polygon API with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self._client.get(
                url,
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get("X-RateLimit-Reset", 60))
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=retry_after
                )
            
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
        """Get real-time quote for a ticker."""
        endpoint = f"/v2/aggs/ticker/{ticker}/prev"
        
        data = await self._make_request(endpoint)
        
        if not data.get("results") or len(data["results"]) == 0:
            raise PolygonAPIError(f"No quote data found for {ticker}")
        
        result = data["results"][0]
        
        # Get additional quote details
        quote_endpoint = f"/v3/quotes/{ticker}"
        quote_data = await self._make_request(quote_endpoint)
        
        quote_result = quote_data.get("results", {})
        
        return Quote(
            ticker=ticker,
            price=result.get("c", 0),
            bid=quote_result.get("bid_price"),
            ask=quote_result.get("ask_price"),
            bid_size=quote_result.get("bid_size"),
            ask_size=quote_result.get("ask_size"),
            volume=result.get("v", 0),
            high=result.get("h"),
            low=result.get("l"),
            open=result.get("o"),
            close=result.get("c"),
            vwap=result.get("vw"),
            timestamp=datetime.fromtimestamp(result.get("t", 0) / 1000)
        )
    
    async def get_option_chain(self, ticker: str, expiration: date) -> OptionChain:
        """Get option chain for a specific expiration date."""
        exp_str = expiration.strftime("%Y-%m-%d")
        endpoint = "/v3/reference/options/contracts"
        
        params = {
            "underlying_ticker": ticker,
            "expiration_date": exp_str,
            "limit": 250
        }
        
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
                    mid=(quote_data.get("bid_price", 0) + quote_data.get("ask_price", 0)) / 2,
                    last=quote_data.get("last_price"),
                    volume=quote_data.get("day_volume", 0),
                    open_interest=quote_data.get("open_interest", 0)
                )
                options.append(option)
            except Exception:
                # Skip contracts that fail to get quotes
                continue
        
        return OptionChain(
            ticker=ticker,
            expiration=exp_str,
            underlying_price=quote.price,
            options=options
        )
    
    async def get_historical_bars(
        self,
        ticker: str,
        from_date: date,
        to_date: date,
        timeframe: str = "day"
    ) -> list[Bar]:
        """Get historical price bars."""
        timespan_map = {
            "minute": "minute",
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month"
        }
        
        timespan = timespan_map.get(timeframe, "day")
        multiplier = 1
        
        endpoint = f"/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 5000
        }
        
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
                vwap=bar_data.get("vw")
            )
            bars.append(bar)
        
        return bars
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()