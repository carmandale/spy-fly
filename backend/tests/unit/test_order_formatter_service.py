"""
Tests for OrderFormatter service.

These tests verify that the OrderFormatter service correctly integrates
spread recommendations with order ticket generation and broker formatting.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.models.execution import OrderTicket, BrokerFormat, OrderType, TimeInForce
from app.models.spread import SpreadRecommendation
from app.services.execution.order_formatter import OrderFormatter, OrderFormatterError


class TestOrderFormatter:
    """Test OrderFormatter service integration."""

    @pytest.fixture
    def sample_spread_recommendation(self):
        """Create a sample spread recommendation for testing."""
        return SpreadRecommendation(
            long_strike=470.0,
            short_strike=472.0,
            long_premium=6.05,
            short_premium=4.25,
            net_debit=1.80,
            max_risk=1.80,
            max_profit=0.20,
            risk_reward_ratio=0.11,
            probability_of_profit=0.65,
            breakeven_price=471.80,
            long_bid=6.00,
            long_ask=6.10,
            short_bid=4.20,
            short_ask=4.30,
            long_volume=1500,
            short_volume=1200,
            expected_value=0.05,
            sentiment_score=0.6,
            ranking_score=0.78,
            timestamp=datetime.now(),
            contracts_to_trade=2,
            total_cost=360.0,
            buying_power_used_pct=0.036,
        )

    @pytest.fixture
    def mock_broker_adapter(self):
        """Create mock BrokerFormatAdapter."""
        mock_adapter = Mock()
        mock_adapter.format_order.return_value = "Formatted order text"
        return mock_adapter

    @pytest.fixture
    def order_formatter(self, mock_broker_adapter):
        """Create OrderFormatter with mocked dependencies."""
        return OrderFormatter(broker_adapter=mock_broker_adapter)

    def test_create_order_ticket_from_recommendation(self, order_formatter, sample_spread_recommendation):
        """Test creating order ticket from spread recommendation."""
        recommendation_id = "test-rec-123"
        account_size = Decimal("10000.00")
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id=recommendation_id,
            recommendation=sample_spread_recommendation,
            account_size=account_size
        )
        
        assert isinstance(order_ticket, OrderTicket)
        assert order_ticket.recommendation_id == recommendation_id
        assert order_ticket.symbol == "SPY"
        assert order_ticket.long_strike == Decimal("470.0")
        assert order_ticket.short_strike == Decimal("472.0")
        assert order_ticket.long_quantity == 2
        assert order_ticket.short_quantity == 2
        assert order_ticket.net_debit == Decimal("1.8")
        assert order_ticket.max_risk == Decimal("1.8")
        assert order_ticket.max_profit == Decimal("0.2")
        assert order_ticket.account_size == account_size
        assert order_ticket.buying_power_used_pct == Decimal("0.036")

    def test_create_order_ticket_with_custom_broker_format(self, order_formatter, sample_spread_recommendation):
        """Test creating order ticket with specific broker format."""
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-456",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            broker_format=BrokerFormat.TD_AMERITRADE
        )
        
        assert order_ticket.broker_format == BrokerFormat.TD_AMERITRADE

    def test_create_order_ticket_with_custom_order_type(self, order_formatter, sample_spread_recommendation):
        """Test creating order ticket with market order type."""
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-789",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            order_type=OrderType.MARKET
        )
        
        assert order_ticket.order_type == OrderType.MARKET
        assert order_ticket.long_limit_price is None
        assert order_ticket.short_limit_price is None

    def test_create_order_ticket_with_custom_quantity(self, order_formatter, sample_spread_recommendation):
        """Test creating order ticket with custom contract quantity."""
        custom_quantity = 5
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-custom",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("25000.00"),
            custom_quantity=custom_quantity
        )
        
        assert order_ticket.long_quantity == custom_quantity
        assert order_ticket.short_quantity == custom_quantity
        # Total cost should be recalculated
        expected_cost = sample_spread_recommendation.net_debit * custom_quantity * 100
        assert float(order_ticket.total_cost) == expected_cost

    def test_create_order_ticket_validates_buying_power(self, order_formatter, sample_spread_recommendation):
        """Test that order ticket creation validates buying power limits."""
        small_account = Decimal("1000.00")
        
        with pytest.raises(OrderFormatterError) as exc_info:
            order_formatter.create_order_ticket(
                recommendation_id="test-rec-bp",
                recommendation=sample_spread_recommendation,
                account_size=small_account
            )
        
        assert "buying power" in str(exc_info.value).lower()

    def test_create_order_ticket_with_limit_price_adjustment(self, order_formatter, sample_spread_recommendation):
        """Test creating order ticket with limit price adjustments."""
        adjustment = Decimal("0.05")  # 5 cent adjustment
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-adj",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            limit_price_adjustment=adjustment
        )
        
        # Limit prices should be adjusted
        expected_long_price = Decimal("6.10")  # 6.05 + 0.05
        expected_short_price = Decimal("4.30")  # 4.25 + 0.05
        expected_net_debit = expected_long_price - expected_short_price
        
        assert order_ticket.long_limit_price == expected_long_price
        assert order_ticket.short_limit_price == expected_short_price
        assert order_ticket.net_debit == expected_net_debit

    def test_format_order_for_broker(self, order_formatter, sample_spread_recommendation, mock_broker_adapter):
        """Test formatting order for specific broker."""
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-format",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            broker_format=BrokerFormat.INTERACTIVE_BROKERS
        )
        
        formatted_order = order_formatter.format_order(order_ticket)
        
        # Should call broker adapter
        mock_broker_adapter.format_order.assert_called_once_with(order_ticket)
        assert formatted_order == "Formatted order text"

    def test_generate_complete_order_package(self, order_formatter, sample_spread_recommendation):
        """Test generating complete order package with all components."""
        recommendation_id = "test-rec-complete"
        account_size = Decimal("10000.00")
        
        order_package = order_formatter.generate_order_package(
            recommendation_id=recommendation_id,
            recommendation=sample_spread_recommendation,
            account_size=account_size,
            broker_format=BrokerFormat.GENERIC
        )
        
        assert "order_ticket" in order_package
        assert "formatted_order" in order_package
        assert "execution_checklist" in order_package
        assert "risk_summary" in order_package
        
        # Verify order ticket
        order_ticket = order_package["order_ticket"]
        assert isinstance(order_ticket, OrderTicket)
        assert order_ticket.recommendation_id == recommendation_id
        
        # Verify formatted order
        assert isinstance(order_package["formatted_order"], str)
        assert len(order_package["formatted_order"]) > 0
        
        # Verify execution checklist
        checklist = order_package["execution_checklist"]
        assert isinstance(checklist, list)
        assert len(checklist) > 0
        
        # Verify risk summary
        risk_summary = order_package["risk_summary"]
        assert isinstance(risk_summary, dict)
        assert "max_risk" in risk_summary
        assert "max_profit" in risk_summary

    def test_generate_execution_checklist(self, order_formatter, sample_spread_recommendation):
        """Test generating execution checklist."""
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-checklist",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        checklist = order_formatter.generate_execution_checklist(order_ticket)
        
        assert isinstance(checklist, list)
        assert len(checklist) >= 5  # Should have multiple steps
        
        # Check that important steps are included
        checklist_text = " ".join(checklist)
        assert "market" in checklist_text.lower()
        assert "account" in checklist_text.lower() or "buying power" in checklist_text.lower()
        assert "risk" in checklist_text.lower()
        assert "order" in checklist_text.lower()

    def test_generate_risk_summary(self, order_formatter, sample_spread_recommendation):
        """Test generating risk summary."""
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-risk",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        risk_summary = order_formatter.generate_risk_summary(order_ticket)
        
        assert isinstance(risk_summary, dict)
        
        # Check required fields
        required_fields = [
            "max_risk", "max_profit", "risk_reward_ratio",
            "breakeven_price", "probability_of_profit",
            "buying_power_used", "total_cost"
        ]
        
        for field in required_fields:
            assert field in risk_summary
        
        # Verify data types and values
        assert isinstance(risk_summary["max_risk"], (int, float, Decimal))
        assert isinstance(risk_summary["max_profit"], (int, float, Decimal))
        assert risk_summary["max_risk"] > 0
        assert risk_summary["max_profit"] > 0

    @patch('app.services.execution.order_formatter.datetime')
    def test_create_order_ticket_expiration_date(self, mock_datetime, order_formatter, sample_spread_recommendation):
        """Test that order ticket uses correct expiration date for 0-DTE."""
        # Mock current date
        mock_datetime.now.return_value = datetime(2025, 7, 29, 10, 0, 0)
        mock_datetime.date = date
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-expiry",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        # Should use today's date for 0-DTE options
        assert order_ticket.expiration_date == date(2025, 7, 29)

    def test_handle_invalid_recommendation_data(self, order_formatter):
        """Test handling of invalid recommendation data."""
        invalid_recommendation = Mock()
        invalid_recommendation.net_debit = -1.0  # Invalid negative debit
        
        with pytest.raises(OrderFormatterError) as exc_info:
            order_formatter.create_order_ticket(
                recommendation_id="test-rec-invalid",
                recommendation=invalid_recommendation,
                account_size=Decimal("10000.00")
            )
        
        assert "invalid" in str(exc_info.value).lower()

    def test_handle_zero_contracts_recommendation(self, order_formatter, sample_spread_recommendation):
        """Test handling recommendation with zero contracts."""
        sample_spread_recommendation.contracts_to_trade = 0
        
        with pytest.raises(OrderFormatterError) as exc_info:
            order_formatter.create_order_ticket(
                recommendation_id="test-rec-zero",
                recommendation=sample_spread_recommendation,
                account_size=Decimal("10000.00")
            )
        
        assert "contract" in str(exc_info.value).lower()

    def test_create_order_ticket_preserves_precision(self, order_formatter, sample_spread_recommendation):
        """Test that decimal precision is preserved in order ticket creation."""
        # Set precise decimal values
        sample_spread_recommendation.net_debit = 1.8250
        sample_spread_recommendation.long_premium = 6.0750
        sample_spread_recommendation.short_premium = 4.2500
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-precision",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        assert order_ticket.net_debit == Decimal("1.8250")
        assert order_ticket.long_limit_price == Decimal("6.0750")
        assert order_ticket.short_limit_price == Decimal("4.2500")

    def test_format_order_handles_broker_adapter_errors(self, order_formatter, sample_spread_recommendation, mock_broker_adapter):
        """Test handling of broker adapter formatting errors."""
        # Configure mock to raise exception
        mock_broker_adapter.format_order.side_effect = Exception("Broker formatting failed")
        
        order_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-error",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        with pytest.raises(OrderFormatterError) as exc_info:
            order_formatter.format_order(order_ticket)
        
        assert "format" in str(exc_info.value).lower()

    def test_validate_order_parameters(self, order_formatter, sample_spread_recommendation):
        """Test validation of order parameters."""
        # Test invalid account size
        with pytest.raises(OrderFormatterError):
            order_formatter.create_order_ticket(
                recommendation_id="test-rec-validate",
                recommendation=sample_spread_recommendation,
                account_size=Decimal("-1000.00")  # Negative account size
            )
        
        # Test invalid custom quantity
        with pytest.raises(OrderFormatterError):
            order_formatter.create_order_ticket(
                recommendation_id="test-rec-validate",
                recommendation=sample_spread_recommendation,
                account_size=Decimal("10000.00"),
                custom_quantity=-1  # Negative quantity
            )

    def test_execution_checklist_customization_by_broker(self, order_formatter, sample_spread_recommendation):
        """Test that execution checklist is customized for different brokers."""
        # Test Interactive Brokers checklist
        ib_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-ib",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            broker_format=BrokerFormat.INTERACTIVE_BROKERS
        )
        ib_checklist = order_formatter.generate_execution_checklist(ib_ticket)
        
        # Test TD Ameritrade checklist
        tda_ticket = order_formatter.create_order_ticket(
            recommendation_id="test-rec-tda",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00"),
            broker_format=BrokerFormat.TD_AMERITRADE
        )
        tda_checklist = order_formatter.generate_execution_checklist(tda_ticket)
        
        # Checklists should be different for different brokers
        assert ib_checklist != tda_checklist
        
        # But both should contain essential steps
        for checklist in [ib_checklist, tda_checklist]:
            checklist_text = " ".join(checklist).lower()
            assert any(word in checklist_text for word in ["verify", "check", "confirm"])

    def test_order_package_includes_metadata(self, order_formatter, sample_spread_recommendation):
        """Test that order package includes useful metadata."""
        order_package = order_formatter.generate_order_package(
            recommendation_id="test-rec-metadata",
            recommendation=sample_spread_recommendation,
            account_size=Decimal("10000.00")
        )
        
        # Should include metadata about generation
        assert "generated_at" in order_package
        assert "expires_at" in order_package
        assert isinstance(order_package["generated_at"], datetime)
        assert isinstance(order_package["expires_at"], datetime)
        
        # Expiration should be after generation
        assert order_package["expires_at"] > order_package["generated_at"]


class TestOrderFormatterError:
    """Test OrderFormatterError exception handling."""

    def test_order_formatter_error_creation(self):
        """Test creating OrderFormatterError with message."""
        error = OrderFormatterError("Test error message")
        assert str(error) == "Test error message"

    def test_order_formatter_error_with_details(self):
        """Test OrderFormatterError with additional details."""
        error = OrderFormatterError("Validation failed", details={"field": "account_size", "value": -1000})
        assert "Validation failed" in str(error)
        assert hasattr(error, 'details')
        assert error.details["field"] == "account_size"