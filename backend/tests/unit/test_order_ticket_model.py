"""
Tests for OrderTicket data model and broker format validation.

These tests verify that the OrderTicket Pydantic model correctly validates
order data, handles broker format specifications, and provides proper
error messages for invalid configurations.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import pytest
from pydantic import ValidationError

from app.models.execution import OrderTicket, BrokerFormat, OrderType, TimeInForce


class TestOrderTicketModel:
    """Test OrderTicket Pydantic model validation and serialization."""

    def test_create_valid_order_ticket(self):
        """Test creating a valid order ticket with all required fields."""
        order = OrderTicket(
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
            buying_power_used_pct=Decimal("0.036"),
            total_cost=Decimal("360.00")
        )
        
        assert order.recommendation_id == "test-rec-123"
        assert order.symbol == "SPY"
        assert order.long_strike == Decimal("470.00")
        assert order.short_strike == Decimal("472.00")
        assert order.long_quantity == 2
        assert order.short_quantity == 2
        assert order.order_type == OrderType.LIMIT
        assert order.time_in_force == TimeInForce.DAY
        assert order.broker_format == BrokerFormat.INTERACTIVE_BROKERS
        assert order.net_debit == Decimal("1.80")

    def test_order_ticket_with_minimal_fields(self):
        """Test creating order ticket with only required fields."""
        order = OrderTicket(
            recommendation_id="test-rec-456",
            symbol="SPY",
            long_strike=Decimal("475.00"),
            short_strike=Decimal("477.00"),
            expiration_date=date.today(),
            long_quantity=1,
            short_quantity=1,
            net_debit=Decimal("1.50"),
            max_risk=Decimal("1.50"),
            max_profit=Decimal("0.50"),
            account_size=Decimal("5000.00"),
            buying_power_used_pct=Decimal("0.030")
        )
        
        # Should use default values
        assert order.order_type == OrderType.LIMIT
        assert order.time_in_force == TimeInForce.DAY
        assert order.broker_format == BrokerFormat.INTERACTIVE_BROKERS
        assert order.long_limit_price is None
        assert order.short_limit_price is None

    def test_order_ticket_validation_errors(self):
        """Test validation errors for invalid order configurations."""
        # Test missing required fields
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                symbol="SPY",
                long_strike=Decimal("470.00"),
                # Missing recommendation_id and other required fields
            )
        
        assert "recommendation_id" in str(exc_info.value)
        
        # Test invalid strike relationship
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-789",
                symbol="SPY",
                long_strike=Decimal("472.00"),  # Higher than short strike
                short_strike=Decimal("470.00"),  # Invalid for bull call spread
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "long_strike must be less than short_strike" in str(exc_info.value)

    def test_order_ticket_negative_values_validation(self):
        """Test validation of negative values where not allowed."""
        # Test negative quantities
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-negative",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=-1,  # Invalid
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "long_quantity" in str(exc_info.value)
        
        # Test negative prices
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-negative-price",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                long_limit_price=Decimal("-1.00"),  # Invalid
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "long_limit_price" in str(exc_info.value)

    def test_order_ticket_quantity_mismatch_validation(self):
        """Test validation when long and short quantities don't match."""
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-mismatch",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=2,
                short_quantity=3,  # Mismatch - should be equal for spreads
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "long_quantity must equal short_quantity" in str(exc_info.value)

    def test_order_ticket_expiration_date_validation(self):
        """Test validation of expiration date (must be today or future)."""
        from datetime import timedelta
        
        # Test past expiration date
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-past-date",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today() - timedelta(days=1),  # Past date
                long_quantity=1,
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "expiration_date cannot be in the past" in str(exc_info.value)

    def test_order_ticket_broker_format_enum(self):
        """Test broker format enum validation."""
        # Test valid broker formats
        for broker_format in BrokerFormat:
            order = OrderTicket(
                recommendation_id="test-rec-broker",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                broker_format=broker_format,
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
            assert order.broker_format == broker_format

    def test_order_ticket_risk_metrics_validation(self):
        """Test validation of risk metrics consistency."""
        # Test max_risk greater than net_debit (invalid)
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-risk",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("2.00"),  # Should not exceed net_debit for spreads
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "max_risk cannot exceed net_debit" in str(exc_info.value)

    def test_order_ticket_buying_power_validation(self):
        """Test buying power percentage validation."""
        # Test buying power exceeding 5% limit
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-bp",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                net_debit=Decimal("1.50"),
                max_risk=Decimal("1.50"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.060")  # 6% exceeds 5% limit
            )
        
        assert "less than or equal to 0.05" in str(exc_info.value)

    def test_order_ticket_serialization(self):
        """Test JSON serialization and deserialization."""
        order = OrderTicket(
            recommendation_id="test-rec-serialize",
            symbol="SPY",
            long_strike=Decimal("470.00"),
            short_strike=Decimal("472.00"),
            expiration_date=date.today(),
            long_quantity=2,
            short_quantity=2,
            long_limit_price=Decimal("6.05"),
            short_limit_price=Decimal("4.25"),
            net_debit=Decimal("1.80"),
            max_risk=Decimal("1.80"),
            max_profit=Decimal("0.20"),
            broker_format=BrokerFormat.TD_AMERITRADE,
            account_size=Decimal("10000.00"),
            buying_power_used_pct=Decimal("0.036")
        )
        
        # Test serialization to dict
        order_dict = order.model_dump()
        assert order_dict["recommendation_id"] == "test-rec-serialize"
        assert order_dict["symbol"] == "SPY"
        assert order_dict["broker_format"] == "td_ameritrade"
        
        # Test deserialization from dict
        new_order = OrderTicket.model_validate(order_dict)
        assert new_order.recommendation_id == order.recommendation_id
        assert new_order.broker_format == order.broker_format
        assert new_order.net_debit == order.net_debit

    def test_order_ticket_string_representation(self):
        """Test string representation includes key information."""
        order = OrderTicket(
            recommendation_id="test-rec-str",
            symbol="SPY",
            long_strike=Decimal("470.00"),
            short_strike=Decimal("472.00"),
            expiration_date=date.today(),
            long_quantity=1,
            short_quantity=1,
            net_debit=Decimal("1.50"),
            max_risk=Decimal("1.50"),
            max_profit=Decimal("0.50"),
            account_size=Decimal("5000.00"),
            buying_power_used_pct=Decimal("0.030")
        )
        
        order_str = str(order)
        assert "SPY" in order_str
        assert "470.00/472.00" in order_str
        assert "test-rec-str" in order_str

    def test_order_ticket_price_consistency_validation(self):
        """Test validation of price consistency with strikes and debit."""
        # Test when limit prices don't match calculated net debit
        with pytest.raises(ValidationError) as exc_info:
            OrderTicket(
                recommendation_id="test-rec-price-consistency",
                symbol="SPY",
                long_strike=Decimal("470.00"),
                short_strike=Decimal("472.00"),
                expiration_date=date.today(),
                long_quantity=1,
                short_quantity=1,
                long_limit_price=Decimal("6.00"),
                short_limit_price=Decimal("4.00"),
                net_debit=Decimal("3.00"),  # 6.00 - 4.00 = 2.00, not 3.00
                max_risk=Decimal("3.00"),
                max_profit=Decimal("0.50"),
                account_size=Decimal("5000.00"),
                buying_power_used_pct=Decimal("0.030")
            )
        
        assert "net_debit must equal long_limit_price minus short_limit_price" in str(exc_info.value)


class TestBrokerFormatEnum:
    """Test BrokerFormat enum values and properties."""

    def test_broker_format_values(self):
        """Test that all expected broker formats are available."""
        expected_formats = [
            "interactive_brokers",
            "td_ameritrade", 
            "etrade",
            "schwab",
            "generic"
        ]
        
        actual_formats = [format.value for format in BrokerFormat]
        
        for expected in expected_formats:
            assert expected in actual_formats

    def test_broker_format_display_names(self):
        """Test broker format display names for UI."""
        format_names = {
            BrokerFormat.INTERACTIVE_BROKERS: "Interactive Brokers",
            BrokerFormat.TD_AMERITRADE: "TD Ameritrade",
            BrokerFormat.ETRADE: "E*TRADE",
            BrokerFormat.SCHWAB: "Charles Schwab",
            BrokerFormat.GENERIC: "Generic Format"
        }
        
        for broker_format, expected_name in format_names.items():
            assert broker_format.display_name == expected_name


class TestOrderTypeEnum:
    """Test OrderType enum values."""

    def test_order_type_values(self):
        """Test that all expected order types are available."""
        expected_types = ["limit", "market", "stop_limit"]
        actual_types = [order_type.value for order_type in OrderType]
        
        for expected in expected_types:
            assert expected in actual_types


class TestTimeInForceEnum:
    """Test TimeInForce enum values."""

    def test_time_in_force_values(self):
        """Test that all expected time in force options are available."""
        expected_values = ["day", "gtc", "ioc", "fok"]
        actual_values = [tif.value for tif in TimeInForce]
        
        for expected in expected_values:
            assert expected in actual_values