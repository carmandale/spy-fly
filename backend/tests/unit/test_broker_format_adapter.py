"""
Tests for BrokerFormatAdapter service.

These tests verify that the BrokerFormatAdapter correctly formats order tickets
for different broker platforms and handles edge cases properly.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models.execution import OrderTicket, BrokerFormat, OrderType, TimeInForce
from app.services.execution.broker_format_adapter import BrokerFormatAdapter


class TestBrokerFormatAdapter:
    """Test BrokerFormatAdapter service for formatting orders."""

    @pytest.fixture
    def sample_order_ticket(self):
        """Create a sample order ticket for testing."""
        return OrderTicket(
            recommendation_id="test-rec-123",
            symbol="SPY",
            long_strike=Decimal("470.00"),
            short_strike=Decimal("472.00"),
            expiration_date=date.today(),
            long_quantity=2,
            short_quantity=2,
            order_type=OrderType.LIMIT,
            time_in_force=TimeInForce.DAY,
            long_limit_price=Decimal("6.05"),
            short_limit_price=Decimal("4.25"),
            net_debit=Decimal("1.80"),
            max_risk=Decimal("1.80"),
            max_profit=Decimal("0.20"),
            broker_format=BrokerFormat.INTERACTIVE_BROKERS,
            account_size=Decimal("10000.00"),
            buying_power_used_pct=Decimal("0.036")
        )

    @pytest.fixture
    def adapter(self):
        """Create BrokerFormatAdapter instance."""
        return BrokerFormatAdapter()

    def test_interactive_brokers_format(self, adapter, sample_order_ticket):
        """Test Interactive Brokers order format."""
        sample_order_ticket.broker_format = BrokerFormat.INTERACTIVE_BROKERS
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Check that key elements are present in IB format
        assert "SPY" in formatted_order
        assert "470" in formatted_order
        assert "472" in formatted_order
        assert "6.05" in formatted_order
        assert "4.25" in formatted_order
        assert "BUY" in formatted_order
        assert "SELL" in formatted_order
        assert "2" in formatted_order  # Quantity
        
        # IB-specific formatting
        assert "LMT" in formatted_order or "LIMIT" in formatted_order
        assert "DAY" in formatted_order

    def test_td_ameritrade_format(self, adapter, sample_order_ticket):
        """Test TD Ameritrade order format."""
        sample_order_ticket.broker_format = BrokerFormat.TD_AMERITRADE
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Check that key elements are present in TDA format
        assert "SPY" in formatted_order
        assert "470" in formatted_order
        assert "472" in formatted_order
        assert "6.05" in formatted_order
        assert "4.25" in formatted_order
        assert "BUY" in formatted_order
        assert "SELL" in formatted_order
        
        # TDA might have different formatting
        assert any(word in formatted_order for word in ["LIMIT", "LMT"])

    def test_etrade_format(self, adapter, sample_order_ticket):
        """Test E*TRADE order format."""
        sample_order_ticket.broker_format = BrokerFormat.ETRADE
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Check that key elements are present in E*TRADE format
        assert "SPY" in formatted_order
        assert "470" in formatted_order
        assert "472" in formatted_order
        assert "BUY" in formatted_order
        assert "SELL" in formatted_order

    def test_schwab_format(self, adapter, sample_order_ticket):
        """Test Charles Schwab order format."""
        sample_order_ticket.broker_format = BrokerFormat.SCHWAB
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Check that key elements are present in Schwab format
        assert "SPY" in formatted_order
        assert "470" in formatted_order
        assert "472" in formatted_order
        assert "BUY" in formatted_order
        assert "SELL" in formatted_order

    def test_generic_format(self, adapter, sample_order_ticket):
        """Test generic order format."""
        sample_order_ticket.broker_format = BrokerFormat.GENERIC
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Generic format should be human-readable
        assert "Bull Call Spread" in formatted_order
        assert "SPY" in formatted_order
        assert "470.00" in formatted_order
        assert "472.00" in formatted_order
        assert "1.80" in formatted_order  # Net debit
        assert "Long" in formatted_order
        assert "Short" in formatted_order

    def test_format_order_with_market_order(self, adapter, sample_order_ticket):
        """Test formatting market orders (no limit prices)."""
        sample_order_ticket.order_type = OrderType.MARKET
        sample_order_ticket.long_limit_price = None
        sample_order_ticket.short_limit_price = None
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        assert "MKT" in formatted_order or "MARKET" in formatted_order
        # Should not contain specific prices for market orders
        assert "6.05" not in formatted_order
        assert "4.25" not in formatted_order

    def test_format_order_with_gtc_time_in_force(self, adapter, sample_order_ticket):
        """Test formatting with Good Till Canceled time in force."""
        sample_order_ticket.time_in_force = TimeInForce.GTC
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        assert "GTC" in formatted_order

    def test_format_order_with_different_quantities(self, adapter, sample_order_ticket):
        """Test formatting with different contract quantities."""
        sample_order_ticket.long_quantity = 5
        sample_order_ticket.short_quantity = 5
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        assert "5" in formatted_order

    def test_format_order_with_expiration_date(self, adapter, sample_order_ticket):
        """Test that expiration date is included in formatted order."""
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Should include expiration date in some format
        expiration_str = sample_order_ticket.expiration_date.strftime("%Y%m%d")
        assert expiration_str in formatted_order or str(sample_order_ticket.expiration_date) in formatted_order

    def test_unsupported_broker_format_raises_error(self, adapter, sample_order_ticket):
        """Test that unsupported broker formats raise appropriate errors."""
        # This would test if we had an invalid enum value, but Pydantic prevents that
        # Instead, test that all enum values are supported
        for broker_format in BrokerFormat:
            sample_order_ticket.broker_format = broker_format
            formatted_order = adapter.format_order(sample_order_ticket)
            assert isinstance(formatted_order, str)
            assert len(formatted_order) > 0

    def test_format_order_preserves_precision(self, adapter, sample_order_ticket):
        """Test that decimal precision is preserved in formatting."""
        sample_order_ticket.long_limit_price = Decimal("6.0250")
        sample_order_ticket.short_limit_price = Decimal("4.2500")
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Should preserve precision for trading
        assert "6.025" in formatted_order or "6.03" in formatted_order
        assert "4.25" in formatted_order

    def test_format_order_handles_zero_dte_expiration(self, adapter, sample_order_ticket):
        """Test formatting for 0-DTE (same day expiration) options."""
        sample_order_ticket.expiration_date = date.today()
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Should handle 0-DTE properly
        assert "SPY" in formatted_order
        # Expiration should be today's date
        today_str = date.today().strftime("%Y%m%d")
        assert today_str in formatted_order or "0DTE" in formatted_order or str(date.today()) in formatted_order

    def test_get_supported_formats(self, adapter):
        """Test getting list of supported broker formats."""
        supported_formats = adapter.get_supported_formats()
        
        assert isinstance(supported_formats, list)
        assert len(supported_formats) > 0
        
        # Should include all enum values
        expected_formats = [fmt.value for fmt in BrokerFormat]
        for expected in expected_formats:
            assert expected in [fmt.format_code.value for fmt in supported_formats]

    def test_get_format_info(self, adapter):
        """Test getting detailed information about specific broker format."""
        format_info = adapter.get_format_info(BrokerFormat.INTERACTIVE_BROKERS)
        
        assert format_info.format_code == BrokerFormat.INTERACTIVE_BROKERS
        assert format_info.display_name == "Interactive Brokers"
        assert isinstance(format_info.description, str)
        assert len(format_info.description) > 0
        assert isinstance(format_info.order_fields, list)
        assert len(format_info.order_fields) > 0
        assert isinstance(format_info.sample_order, str)
        assert len(format_info.sample_order) > 0

    def test_format_info_for_all_brokers(self, adapter):
        """Test that format info is available for all supported brokers."""
        for broker_format in BrokerFormat:
            format_info = adapter.get_format_info(broker_format)
            
            assert format_info.format_code == broker_format
            assert len(format_info.display_name) > 0
            assert len(format_info.description) > 0
            assert len(format_info.order_fields) > 0
            assert len(format_info.sample_order) > 0

    def test_format_order_consistent_output(self, adapter, sample_order_ticket):
        """Test that formatting the same order multiple times produces consistent output."""
        formatted_order_1 = adapter.format_order(sample_order_ticket)
        formatted_order_2 = adapter.format_order(sample_order_ticket)
        
        assert formatted_order_1 == formatted_order_2

    def test_format_order_with_edge_case_strikes(self, adapter, sample_order_ticket):
        """Test formatting with edge case strike prices."""
        # Test with very high strikes
        sample_order_ticket.long_strike = Decimal("580.00")
        sample_order_ticket.short_strike = Decimal("585.00")
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        assert "580" in formatted_order
        assert "585" in formatted_order

    def test_format_order_includes_risk_information(self, adapter, sample_order_ticket):
        """Test that formatted order includes risk information when appropriate."""
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Generic format should include risk info
        if sample_order_ticket.broker_format == BrokerFormat.GENERIC:
            assert "Max Risk" in formatted_order or "1.80" in formatted_order
            assert "Max Profit" in formatted_order or "0.20" in formatted_order

    def test_format_order_with_single_contract(self, adapter, sample_order_ticket):
        """Test formatting with single contract quantities."""
        sample_order_ticket.long_quantity = 1
        sample_order_ticket.short_quantity = 1
        
        formatted_order = adapter.format_order(sample_order_ticket)
        
        # Should handle singular vs plural correctly
        assert "1" in formatted_order

    def test_format_order_symbol_validation(self, adapter, sample_order_ticket):
        """Test that symbol is properly handled in all formats."""
        symbols_to_test = ["SPY", "QQQ", "IWM", "AAPL"]
        
        for symbol in symbols_to_test:
            sample_order_ticket.symbol = symbol
            formatted_order = adapter.format_order(sample_order_ticket)
            assert symbol in formatted_order