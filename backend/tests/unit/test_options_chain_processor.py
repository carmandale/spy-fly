"""
Unit tests for OptionsChainProcessor.

Tests data parsing, validation, and filtering for 0-DTE SPY options
from Polygon.io API responses.
"""

from datetime import date, datetime, time

import pandas as pd
import pytest

from app.models.market import OptionChainResponse, OptionContract
from app.services.options_chain_processor import OptionsChainProcessor


class TestOptionsChainProcessor:
    """Test options chain processing and validation."""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.processor = OptionsChainProcessor()
        self.test_date = date(2025, 7, 28)

    def create_mock_option_contract(
        self,
        strike: float,
        bid: float,
        ask: float,
        volume: int = 100,
        open_interest: int = 50,
        contract_type: str = "call",
    ) -> OptionContract:
        """Helper to create mock option contracts."""
        return OptionContract(
            symbol=f"SPY{self.test_date.strftime('%y%m%d')}C{int(strike*1000):08d}",
            type=contract_type,
            strike=strike,
            expiration=self.test_date.isoformat(),
            bid=bid,
            ask=ask,
            mid=(bid + ask) / 2,
            last=(bid + ask) / 2,
            volume=volume,
            open_interest=open_interest,
        )

    def test_parse_polygon_option_chain(self):
        """Test parsing of Polygon.io option chain response."""
        # Create mock option chain response
        options = [
            self.create_mock_option_contract(470.0, 5.20, 5.30),
            self.create_mock_option_contract(475.0, 3.10, 3.20),
            self.create_mock_option_contract(480.0, 1.50, 1.60),
            self.create_mock_option_contract(485.0, 0.50, 0.60),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.50,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        # Parse the response
        df = self.processor.parse_option_chain(mock_response)

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        assert all(
            col in df.columns
            for col in [
                "strike",
                "bid",
                "ask",
                "mid",
                "volume",
                "open_interest",
                "bid_ask_spread",
            ]
        )

        # Verify data integrity
        assert df["strike"].tolist() == [470.0, 475.0, 480.0, 485.0]
        assert df.loc[0, "bid"] == 5.20
        assert df.loc[0, "ask"] == 5.30
        assert df.loc[0, "mid"] == 5.25
        assert df.loc[0, "bid_ask_spread"] == pytest.approx(0.10, abs=0.001)

    def test_filter_zero_dte_options(self):
        """Test filtering for 0-DTE options only."""
        # Create options with different expirations
        today = date.today()
        tomorrow = date(today.year, today.month, today.day + 1)

        options = [
            OptionContract(
                symbol="SPY_TODAY",
                type="call",
                strike=475.0,
                expiration=today.isoformat(),
                bid=3.0,
                ask=3.1,
                mid=3.05,
                volume=100,
                open_interest=50,
            ),
            OptionContract(
                symbol="SPY_TOMORROW",
                type="call",
                strike=475.0,
                expiration=tomorrow.isoformat(),
                bid=4.0,
                ask=4.1,
                mid=4.05,
                volume=100,
                open_interest=50,
            ),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=today.isoformat(),
            options=options,
            cached=False,
        )

        # Filter for 0-DTE
        df = self.processor.parse_option_chain(mock_response, filter_zero_dte=True)

        # Should only have today's option
        assert len(df) == 1
        assert df.iloc[0]["strike"] == 475.0
        assert df.iloc[0]["bid"] == 3.0

    def test_handle_missing_data(self):
        """Test handling of missing or invalid data in option chain."""
        # Create options with missing data
        options = [
            self.create_mock_option_contract(470.0, 0, 0, volume=0),  # No bid/ask
            self.create_mock_option_contract(475.0, 3.0, 0),  # No ask
            self.create_mock_option_contract(480.0, 0, 2.0),  # No bid
            self.create_mock_option_contract(485.0, 1.0, 1.1),  # Valid
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        # Parse with validation
        df = self.processor.parse_option_chain(mock_response, validate_data=True)

        # Should only have valid option
        assert len(df) == 1
        assert df.iloc[0]["strike"] == 485.0

    def test_calculate_liquidity_metrics(self):
        """Test calculation of liquidity metrics for options."""
        options = [
            self.create_mock_option_contract(
                475.0, 3.00, 3.10, volume=1000, open_interest=500
            ),
            self.create_mock_option_contract(
                480.0, 1.50, 1.70, volume=50, open_interest=20
            ),
            self.create_mock_option_contract(
                485.0, 0.50, 0.80, volume=5, open_interest=2
            ),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=477.0,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)

        # Add liquidity metrics
        df = self.processor.add_liquidity_metrics(df)

        # Verify liquidity calculations
        assert "bid_ask_spread_pct" in df.columns
        assert "liquidity_score" in df.columns

        # First option should have best liquidity
        assert df.loc[0, "bid_ask_spread_pct"] == pytest.approx(
            (0.10 / 3.05) * 100, abs=0.01
        )
        assert df.loc[0, "liquidity_score"] > df.loc[2, "liquidity_score"]

    def test_sort_and_structure_data(self):
        """Test proper sorting and structuring of option data."""
        # Create unsorted options
        options = [
            self.create_mock_option_contract(485.0, 0.50, 0.60),
            self.create_mock_option_contract(475.0, 3.10, 3.20),
            self.create_mock_option_contract(480.0, 1.50, 1.60),
            self.create_mock_option_contract(470.0, 5.20, 5.30),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.50,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)

        # Verify sorting by strike
        strikes = df["strike"].tolist()
        assert strikes == sorted(strikes)
        assert strikes == [470.0, 475.0, 480.0, 485.0]

    def test_filter_by_moneyness(self):
        """Test filtering options by moneyness (ITM/OTM)."""
        spot_price = 475.0
        options = [
            self.create_mock_option_contract(465.0, 10.20, 10.30),  # Deep ITM
            self.create_mock_option_contract(470.0, 5.20, 5.30),  # ITM
            self.create_mock_option_contract(475.0, 3.10, 3.20),  # ATM
            self.create_mock_option_contract(480.0, 1.50, 1.60),  # OTM
            self.create_mock_option_contract(490.0, 0.10, 0.20),  # Deep OTM
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=spot_price,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)

        # Filter for reasonable OTM options (0-10 points OTM)
        filtered_df = self.processor.filter_by_moneyness(
            df, spot_price=spot_price, min_otm_points=0, max_otm_points=10
        )

        # Should have ATM and reasonable OTM options
        assert len(filtered_df) == 2
        assert filtered_df["strike"].tolist() == [475.0, 480.0]

    def test_empty_option_chain_handling(self):
        """Test handling of empty option chains."""
        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=self.test_date.isoformat(),
            options=[],
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert all(col in df.columns for col in ["strike", "bid", "ask"])

    def test_dataframe_dtypes(self):
        """Test that DataFrame has correct data types."""
        options = [
            self.create_mock_option_contract(475.0, 3.10, 3.20, volume=100),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)

        # Verify data types
        assert df["strike"].dtype == "float64"
        assert df["bid"].dtype == "float64"
        assert df["ask"].dtype == "float64"
        assert df["volume"].dtype == "int64"
        assert df["open_interest"].dtype == "int64"

    @pytest.mark.parametrize(
        "volume,oi,expected_liquid",
        [
            (1000, 500, True),  # High volume and OI
            (10, 5, False),  # Low volume and OI
            (500, 10, True),  # Good volume, low OI
            (10, 500, True),  # Low volume, good OI
        ],
    )
    def test_liquidity_filtering(self, volume, oi, expected_liquid):
        """Test liquidity-based filtering with various thresholds."""
        options = [
            self.create_mock_option_contract(
                475.0, 3.00, 3.10, volume=volume, open_interest=oi
            ),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=self.test_date.isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)
        filtered = self.processor.filter_by_liquidity(
            df, min_volume=50, min_open_interest=50, require_both=False
        )

        if expected_liquid:
            assert len(filtered) == 1
        else:
            assert len(filtered) == 0

    def test_time_to_expiry_calculation(self):
        """Test calculation of time to expiry in hours."""
        # Create option expiring today
        now = datetime.now()
        market_close = datetime.combine(date.today(), time(16, 0))  # 4 PM ET

        options = [
            self.create_mock_option_contract(475.0, 3.00, 3.10),
        ]

        mock_response = OptionChainResponse(
            ticker="SPY",
            underlying_price=475.0,
            expiration=date.today().isoformat(),
            options=options,
            cached=False,
        )

        df = self.processor.parse_option_chain(mock_response)
        df = self.processor.add_time_to_expiry(df, current_time=now)

        assert "hours_to_expiry" in df.columns
        # Should be positive if before market close
        if now < market_close:
            assert df.iloc[0]["hours_to_expiry"] > 0
        else:
            assert df.iloc[0]["hours_to_expiry"] <= 0
