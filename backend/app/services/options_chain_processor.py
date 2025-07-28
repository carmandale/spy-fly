"""
Options Chain Processor for parsing and filtering 0-DTE SPY options.

This module handles the parsing, validation, and structuring of options data
from Polygon.io API responses for use in spread selection algorithms.
"""

from datetime import date, datetime, time

import numpy as np
import pandas as pd

from app.models.market import OptionChainResponse, OptionContract


class OptionsChainProcessor:
    """
    Process and structure options chain data for spread analysis.

    This class handles parsing raw options data from Polygon.io,
    filtering for 0-DTE options, calculating liquidity metrics,
    and preparing data for spread generation.
    """

    def __init__(self):
        """Initialize the options chain processor."""
        self.market_close_time = time(16, 0)  # 4 PM ET market close

    def parse_option_chain(
        self,
        option_chain_response: OptionChainResponse,
        filter_zero_dte: bool = False,
        validate_data: bool = False,
    ) -> pd.DataFrame:
        """
        Parse Polygon.io option chain response into structured DataFrame.

        Args:
                option_chain_response: Raw option chain data from Polygon.io
                filter_zero_dte: Filter for 0-DTE options only
                validate_data: Remove options with invalid/missing pricing data

        Returns:
                DataFrame with structured option data sorted by strike price
        """
        # Convert options to DataFrame
        if not option_chain_response.options:
            return self._create_empty_dataframe()

        options_data = []
        today = date.today()

        for option in option_chain_response.options:
            # Skip non-call options for bull-call-spreads
            if option.type.lower() != "call":
                continue

            # Parse expiration date
            exp_date = date.fromisoformat(option.expiration)

            # Filter for 0-DTE if requested
            if filter_zero_dte and exp_date != today:
                continue

            # Skip if validation enabled and data is invalid
            if validate_data and not self._is_valid_option_data(option):
                continue

            option_dict = {
                "symbol": option.symbol,
                "strike": float(option.strike),
                "expiration": option.expiration,
                "bid": float(option.bid),
                "ask": float(option.ask),
                "mid": float(option.mid),
                "last": float(option.last) if option.last else option.mid,
                "volume": int(option.volume),
                "open_interest": int(option.open_interest),
                "bid_ask_spread": float(option.ask - option.bid),
            }

            options_data.append(option_dict)

        if not options_data:
            return self._create_empty_dataframe()

        # Create DataFrame and sort by strike
        df = pd.DataFrame(options_data)
        df = df.sort_values("strike").reset_index(drop=True)

        return df

    def add_liquidity_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add liquidity metrics to options DataFrame.

        Args:
                df: Options DataFrame

        Returns:
                DataFrame with additional liquidity metrics
        """
        if df.empty:
            return df

        # Calculate bid-ask spread as percentage of mid price
        df["bid_ask_spread_pct"] = (df["bid_ask_spread"] / df["mid"]) * 100

        # Calculate composite liquidity score (0-100)
        # Based on volume, open interest, and bid-ask spread
        volume_score = np.clip(df["volume"] / 1000, 0, 1) * 40  # 40% weight
        oi_score = np.clip(df["open_interest"] / 500, 0, 1) * 30  # 30% weight
        spread_score = (
            np.clip(1 - (df["bid_ask_spread_pct"] / 10), 0, 1) * 30
        )  # 30% weight

        df["liquidity_score"] = volume_score + oi_score + spread_score

        return df

    def filter_by_moneyness(
        self,
        df: pd.DataFrame,
        spot_price: float,
        min_otm_points: float = 0,
        max_otm_points: float = 20,
    ) -> pd.DataFrame:
        """
        Filter options by moneyness relative to spot price.

        Args:
                df: Options DataFrame
                spot_price: Current SPY spot price
                min_otm_points: Minimum out-of-the-money points
                max_otm_points: Maximum out-of-the-money points

        Returns:
                Filtered DataFrame
        """
        if df.empty:
            return df

        # Calculate OTM distance
        otm_distance = df["strike"] - spot_price

        # Filter by OTM range
        mask = (otm_distance >= min_otm_points) & (otm_distance <= max_otm_points)

        return df[mask].reset_index(drop=True)

    def filter_by_liquidity(
        self,
        df: pd.DataFrame,
        min_volume: int = 10,
        min_open_interest: int = 10,
        min_bid_ask_spread_pct: float = 0,
        max_bid_ask_spread_pct: float = 5.0,
        require_both: bool = False,
    ) -> pd.DataFrame:
        """
        Filter options by liquidity requirements.

        Args:
                df: Options DataFrame
                min_volume: Minimum volume requirement
                min_open_interest: Minimum open interest requirement
                min_bid_ask_spread_pct: Minimum bid-ask spread percentage
                max_bid_ask_spread_pct: Maximum bid-ask spread percentage
                require_both: If True, require both volume AND open interest minimums

        Returns:
                Filtered DataFrame
        """
        if df.empty:
            return df

        # Ensure we have spread percentage calculated
        if "bid_ask_spread_pct" not in df.columns:
            df = self.add_liquidity_metrics(df)

        # Volume and open interest filter
        if require_both:
            liquidity_mask = (df["volume"] >= min_volume) & (
                df["open_interest"] >= min_open_interest
            )
        else:
            liquidity_mask = (df["volume"] >= min_volume) | (
                df["open_interest"] >= min_open_interest
            )

        # Bid-ask spread filter
        spread_mask = (df["bid_ask_spread_pct"] >= min_bid_ask_spread_pct) & (
            df["bid_ask_spread_pct"] <= max_bid_ask_spread_pct
        )

        # Combine filters
        mask = liquidity_mask & spread_mask

        return df[mask].reset_index(drop=True)

    def add_time_to_expiry(
        self, df: pd.DataFrame, current_time: datetime | None = None
    ) -> pd.DataFrame:
        """
        Add time to expiry in hours for each option.

        Args:
                df: Options DataFrame
                current_time: Current datetime (uses now() if not provided)

        Returns:
                DataFrame with hours_to_expiry column
        """
        if df.empty:
            return df

        if current_time is None:
            current_time = datetime.now()

        # Calculate hours to market close for each expiration
        hours_to_expiry = []

        for exp_str in df["expiration"]:
            exp_date = date.fromisoformat(exp_str)
            market_close = datetime.combine(exp_date, self.market_close_time)

            time_diff = market_close - current_time
            hours = time_diff.total_seconds() / 3600
            hours_to_expiry.append(max(0, hours))  # Don't go negative

        df["hours_to_expiry"] = hours_to_expiry

        return df

    def prepare_for_spread_generation(
        self,
        option_chain_response: OptionChainResponse,
        spot_price: float,
        config: dict | None = None,
    ) -> pd.DataFrame:
        """
        Complete pipeline to prepare options for spread generation.

        Args:
                option_chain_response: Raw option chain data
                spot_price: Current SPY spot price
                config: Optional configuration overrides

        Returns:
                Processed DataFrame ready for spread generation
        """
        # Default configuration
        default_config = {
            "filter_zero_dte": True,
            "validate_data": True,
            "min_volume": 10,
            "min_open_interest": 10,
            "max_bid_ask_spread_pct": 5.0,
            "min_otm_points": -5,  # Allow slightly ITM
            "max_otm_points": 15,  # Up to 15 points OTM
        }

        if config:
            default_config.update(config)

        # Parse option chain
        df = self.parse_option_chain(
            option_chain_response,
            filter_zero_dte=default_config["filter_zero_dte"],
            validate_data=default_config["validate_data"],
        )

        if df.empty:
            return df

        # Add metrics
        df = self.add_liquidity_metrics(df)
        df = self.add_time_to_expiry(df)

        # Apply filters
        df = self.filter_by_moneyness(
            df,
            spot_price=spot_price,
            min_otm_points=default_config["min_otm_points"],
            max_otm_points=default_config["max_otm_points"],
        )

        df = self.filter_by_liquidity(
            df,
            min_volume=default_config["min_volume"],
            min_open_interest=default_config["min_open_interest"],
            max_bid_ask_spread_pct=default_config["max_bid_ask_spread_pct"],
        )

        return df.reset_index(drop=True)

    def _is_valid_option_data(self, option: OptionContract) -> bool:
        """Check if option has valid pricing data."""
        return all(
            [
                option.bid > 0,
                option.ask > 0,
                option.bid < option.ask,
                option.volume >= 0,
                option.open_interest >= 0,
            ]
        )

    def _create_empty_dataframe(self) -> pd.DataFrame:
        """Create empty DataFrame with correct structure."""
        return pd.DataFrame(
            columns=[
                "symbol",
                "strike",
                "expiration",
                "bid",
                "ask",
                "mid",
                "last",
                "volume",
                "open_interest",
                "bid_ask_spread",
            ]
        )
