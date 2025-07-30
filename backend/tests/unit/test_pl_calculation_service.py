"""
Tests for P/L Calculation Service.

Tests position value calculations, P/L tracking, and stop-loss alerts.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from app.models.db_models import Position, PositionSnapshot
from app.services.pl_calculation_service import PLCalculationService, PositionPLData
from app.models.market import OptionContract, OptionChainResponse, QuoteResponse


class TestPLCalculationService:
    """Test P/L calculation service functionality."""
    
    @pytest.fixture
    def mock_market_service(self):
        """Create a mock market service."""
        mock = Mock()
        return mock
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        mock = Mock()
        mock.query = Mock()
        mock.add = Mock()
        mock.commit = Mock()
        return mock
    
    @pytest.fixture
    def pl_service(self, mock_market_service, mock_db_session):
        """Create P/L calculation service instance."""
        return PLCalculationService(
            market_service=mock_market_service,
            db_session=mock_db_session
        )
    
    @pytest.fixture
    def sample_position(self):
        """Create a sample position for testing."""
        return Position(
            id=1,
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),  # Net debit paid
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50"),
            status="open"
        )
    
    def test_calculate_spread_value_with_bid_ask(self, pl_service):
        """Test spread value calculation using bid/ask prices."""
        # Mock option prices
        long_option = {
            'bid': Decimal("3.45"),
            'ask': Decimal("3.50")
        }
        short_option = {
            'bid': Decimal("0.95"),
            'ask': Decimal("1.00")
        }
        
        # Calculate spread value
        # Formula: (Short Bid - Long Ask) × 100 × Quantity
        value = pl_service.calculate_spread_value(
            long_option=long_option,
            short_option=short_option,
            quantity=5
        )
        
        # Expected: (0.95 - 3.50) × 100 × 5 = -2.55 × 100 × 5 = -1275
        assert value == Decimal("-1275.00")
    
    def test_calculate_spread_value_positive(self, pl_service):
        """Test spread value calculation when spread has positive value."""
        # When spread is in profit
        long_option = {
            'bid': Decimal("5.00"),
            'ask': Decimal("5.05")
        }
        short_option = {
            'bid': Decimal("0.20"),
            'ask': Decimal("0.25")
        }
        
        value = pl_service.calculate_spread_value(
            long_option=long_option,
            short_option=short_option,
            quantity=5
        )
        
        # Expected: (0.20 - 5.05) × 100 × 5 = -4.85 × 100 × 5 = -2425
        assert value == Decimal("-2425.00")
    
    def test_calculate_unrealized_pl(self, pl_service):
        """Test unrealized P/L calculation."""
        # Current value: -200, Entry value: -250
        # Unrealized P/L = -200 - (-250) = 50 (profit)
        unrealized_pl = pl_service.calculate_unrealized_pl(
            current_value=Decimal("-200.00"),
            entry_value=Decimal("-250.00")
        )
        
        assert unrealized_pl == Decimal("50.00")
    
    def test_calculate_unrealized_pl_loss(self, pl_service):
        """Test unrealized P/L calculation for a losing position."""
        # Current value: -400, Entry value: -250
        # Unrealized P/L = -400 - (-250) = -150 (loss)
        unrealized_pl = pl_service.calculate_unrealized_pl(
            current_value=Decimal("-400.00"),
            entry_value=Decimal("-250.00")
        )
        
        assert unrealized_pl == Decimal("-150.00")
    
    def test_calculate_pl_percentage(self, pl_service):
        """Test P/L percentage calculation."""
        # Unrealized P/L: 50, Max Risk: 500
        # P/L % = (50 / 500) × 100 = 10%
        pl_percent = pl_service.calculate_pl_percentage(
            unrealized_pl=Decimal("50.00"),
            max_risk=Decimal("500.00")
        )
        
        assert pl_percent == Decimal("10.00")
    
    def test_calculate_pl_percentage_loss(self, pl_service):
        """Test P/L percentage calculation for loss."""
        # Unrealized P/L: -150, Max Risk: 500
        # P/L % = (-150 / 500) × 100 = -30%
        pl_percent = pl_service.calculate_pl_percentage(
            unrealized_pl=Decimal("-150.00"),
            max_risk=Decimal("500.00")
        )
        
        assert pl_percent == Decimal("-30.00")
    
    def test_calculate_pl_percentage_zero_risk(self, pl_service):
        """Test P/L percentage calculation with zero max risk."""
        # Should return 0 to avoid division by zero
        pl_percent = pl_service.calculate_pl_percentage(
            unrealized_pl=Decimal("50.00"),
            max_risk=Decimal("0.00")
        )
        
        assert pl_percent == Decimal("0.00")
    
    def test_should_trigger_stop_loss_alert(self, pl_service):
        """Test stop-loss alert trigger logic."""
        # Should trigger at -20% or worse
        assert pl_service.should_trigger_stop_loss_alert(
            pl_percent=Decimal("-20.00"),
            current_alert_active=False
        ) is True
        
        assert pl_service.should_trigger_stop_loss_alert(
            pl_percent=Decimal("-25.00"),
            current_alert_active=False
        ) is True
        
        # Should not trigger above -20%
        assert pl_service.should_trigger_stop_loss_alert(
            pl_percent=Decimal("-19.00"),
            current_alert_active=False
        ) is False
    
    def test_should_clear_stop_loss_alert(self, pl_service):
        """Test stop-loss alert clearing logic with hysteresis."""
        # Should clear at -15% or better when alert is active
        assert pl_service.should_clear_stop_loss_alert(
            pl_percent=Decimal("-15.00"),
            current_alert_active=True
        ) is True
        
        assert pl_service.should_clear_stop_loss_alert(
            pl_percent=Decimal("-10.00"),
            current_alert_active=True
        ) is True
        
        # Should not clear below -15%
        assert pl_service.should_clear_stop_loss_alert(
            pl_percent=Decimal("-16.00"),
            current_alert_active=True
        ) is False
        
        # Should not clear if alert not active
        assert pl_service.should_clear_stop_loss_alert(
            pl_percent=Decimal("-10.00"),
            current_alert_active=False
        ) is False
    
    async def test_calculate_position_pl(self, pl_service, sample_position, mock_market_service):
        """Test complete P/L calculation for a position."""
        # Mock SPY price
        mock_market_service.get_spy_quote = AsyncMock(return_value=QuoteResponse(
            ticker="SPY",
            price=451.25,
            volume=1000000,
            timestamp="2025-01-30T10:00:00",
            market_status="regular",
            cached=False
        ))
        
        # Mock option chain with our specific strikes
        mock_option_chain = OptionChainResponse(
            ticker="SPY",
            underlying_price=451.25,
            expiration=str(sample_position.expiration_date),
            options=[
                OptionContract(
                    symbol="SPY250130C00450000",
                    type="call",
                    strike=450.0,
                    expiration=str(sample_position.expiration_date),
                    bid=3.45,
                    ask=3.50,
                    mid=3.475,
                    last=3.47,
                    volume=1000,
                    open_interest=5000
                ),
                OptionContract(
                    symbol="SPY250130C00455000",
                    type="call",
                    strike=455.0,
                    expiration=str(sample_position.expiration_date),
                    bid=0.95,
                    ask=1.00,
                    mid=0.975,
                    last=0.97,
                    volume=500,
                    open_interest=2000
                )
            ],
            cached=False
        )
        
        mock_market_service.get_spy_options = AsyncMock(return_value=mock_option_chain)
        
        # Calculate P/L
        result = await pl_service.calculate_position_pl(sample_position)
        
        # Verify result
        assert isinstance(result, PositionPLData)
        assert result.position_id == 1
        assert result.current_value == Decimal("-1275.00")  # From spread calculation
        assert result.unrealized_pl == Decimal("-1025.00")  # -1275 - (-250)
        assert result.unrealized_pl_percent == Decimal("-205.00")  # (-1025 / 500) × 100
        assert result.spy_price == Decimal("451.25")
        assert result.stop_loss_triggered is True  # Because -205% < -20%
    
    async def test_calculate_position_pl_missing_prices(self, pl_service, sample_position, mock_market_service):
        """Test P/L calculation with missing option prices."""
        # Mock SPY price
        mock_market_service.get_spy_quote = AsyncMock(return_value=QuoteResponse(
            ticker="SPY",
            price=451.25,
            volume=1000000,
            timestamp="2025-01-30T10:00:00",
            market_status="regular",
            cached=False
        ))
        
        # Mock empty option chain (no matching strikes)
        mock_market_service.get_spy_options = AsyncMock(return_value=OptionChainResponse(
            ticker="SPY",
            underlying_price=451.25,
            expiration=str(sample_position.expiration_date),
            options=[],  # Empty options list
            cached=False
        ))
        
        # Calculate P/L - should return None
        result = await pl_service.calculate_position_pl(sample_position)
        
        assert result is None
    
    async def test_calculate_all_positions_pl(self, pl_service, sample_position, mock_db_session, mock_market_service):
        """Test batch P/L calculation for multiple positions."""
        # Create multiple positions
        position2 = Position(
            id=2,
            symbol="SPY",
            long_strike=Decimal("460.00"),
            short_strike=Decimal("465.00"),
            expiration_date=date.today(),
            quantity=3,
            entry_value=Decimal("-150.00"),
            max_risk=Decimal("300.00"),
            max_profit=Decimal("150.00"),
            status="open"
        )
        
        # Mock database query
        mock_db_session.query().filter().all.return_value = [sample_position, position2]
        
        # Mock SPY price
        mock_market_service.get_spy_quote = AsyncMock(return_value=QuoteResponse(
            ticker="SPY",
            price=451.25,
            volume=1000000,
            timestamp="2025-01-30T10:00:00",
            market_status="regular",
            cached=False
        ))
        
        # Mock option chain with all strikes for both positions
        mock_market_service.get_spy_options = AsyncMock(return_value=OptionChainResponse(
            ticker="SPY",
            underlying_price=451.25,
            expiration=str(sample_position.expiration_date),
            options=[
                # Position 1 strikes
                OptionContract(
                    symbol="SPY250130C00450000",
                    type="call",
                    strike=450.0,
                    expiration=str(sample_position.expiration_date),
                    bid=3.45,
                    ask=3.50,
                    mid=3.475,
                    last=3.47,
                    volume=1000,
                    open_interest=5000
                ),
                OptionContract(
                    symbol="SPY250130C00455000",
                    type="call",
                    strike=455.0,
                    expiration=str(sample_position.expiration_date),
                    bid=0.95,
                    ask=1.00,
                    mid=0.975,
                    last=0.97,
                    volume=500,
                    open_interest=2000
                ),
                # Position 2 strikes
                OptionContract(
                    symbol="SPY250130C00460000",
                    type="call",
                    strike=460.0,
                    expiration=str(position2.expiration_date),
                    bid=1.20,
                    ask=1.25,
                    mid=1.225,
                    last=1.22,
                    volume=300,
                    open_interest=1000
                ),
                OptionContract(
                    symbol="SPY250130C00465000",
                    type="call",
                    strike=465.0,
                    expiration=str(position2.expiration_date),
                    bid=0.30,
                    ask=0.35,
                    mid=0.325,
                    last=0.32,
                    volume=200,
                    open_interest=800
                )
            ],
            cached=False
        ))
        
        # Calculate P/L for all positions
        results = await pl_service.calculate_all_positions_pl()
        
        # Verify results
        assert len(results) == 2
        assert results[0].position_id == 1
        assert results[1].position_id == 2
        
        # Position 2 calculation: (0.30 - 1.25) × 100 × 3 = -285
        assert results[1].current_value == Decimal("-285.00")
        assert results[1].unrealized_pl == Decimal("-135.00")  # -285 - (-150)
        assert results[1].unrealized_pl_percent == Decimal("-45.00")  # (-135 / 300) × 100
    
    async def test_update_position_pl_values(self, pl_service, sample_position, mock_db_session):
        """Test updating position with calculated P/L values."""
        # Create P/L data
        pl_data = PositionPLData(
            position_id=1,
            spy_price=Decimal("451.25"),
            current_value=Decimal("-200.00"),
            unrealized_pl=Decimal("50.00"),
            unrealized_pl_percent=Decimal("10.00"),
            long_call_bid=Decimal("3.45"),
            long_call_ask=Decimal("3.50"),
            short_call_bid=Decimal("0.95"),
            short_call_ask=Decimal("1.00"),
            risk_percent=Decimal("-10.00"),
            stop_loss_triggered=False,
            calculation_time=datetime.utcnow()
        )
        
        # Update position
        pl_service.update_position_pl_values(sample_position, pl_data)
        
        # Verify position updated
        assert sample_position.latest_value == Decimal("-200.00")
        assert sample_position.latest_unrealized_pl == Decimal("50.00")
        assert sample_position.latest_unrealized_pl_percent == Decimal("10.00")
        assert sample_position.latest_update_time is not None
        assert sample_position.stop_loss_alert_active is False
    
    async def test_update_position_with_stop_loss_alert(self, pl_service, sample_position, mock_db_session):
        """Test updating position when stop-loss alert triggers."""
        # Create P/L data with stop-loss triggered
        pl_data = PositionPLData(
            position_id=1,
            spy_price=Decimal("448.00"),
            current_value=Decimal("-400.00"),
            unrealized_pl=Decimal("-150.00"),
            unrealized_pl_percent=Decimal("-30.00"),
            risk_percent=Decimal("30.00"),
            stop_loss_triggered=True,
            calculation_time=datetime.utcnow()
        )
        
        # Update position
        pl_service.update_position_pl_values(sample_position, pl_data)
        
        # Verify stop-loss alert activated
        assert sample_position.stop_loss_alert_active is True
        assert sample_position.stop_loss_alert_time is not None
    
    async def test_create_position_snapshot(self, pl_service, sample_position, mock_db_session):
        """Test creating position snapshot for history tracking."""
        # Create P/L data
        pl_data = PositionPLData(
            position_id=1,
            spy_price=Decimal("451.25"),
            current_value=Decimal("-200.00"),
            unrealized_pl=Decimal("50.00"),
            unrealized_pl_percent=Decimal("10.00"),
            long_call_bid=Decimal("3.45"),
            long_call_ask=Decimal("3.50"),
            short_call_bid=Decimal("0.95"),
            short_call_ask=Decimal("1.00"),
            risk_percent=Decimal("-10.00"),
            stop_loss_triggered=False,
            calculation_time=datetime.utcnow()
        )
        
        # Create snapshot
        snapshot = pl_service.create_position_snapshot(sample_position, pl_data)
        
        # Verify snapshot created
        assert snapshot.position_id == 1
        assert snapshot.spy_price == Decimal("451.25")
        assert snapshot.current_value == Decimal("-200.00")
        assert snapshot.unrealized_pl == Decimal("50.00")
        assert snapshot.unrealized_pl_percent == Decimal("10.00")
        assert snapshot.risk_percent == Decimal("-10.00")
        assert snapshot.stop_loss_triggered is False
        
        # Verify snapshot added to session
        mock_db_session.add.assert_called_once()
    
    async def test_calculate_position_pl_with_error_handling(self, pl_service, sample_position, mock_market_service):
        """Test P/L calculation handles errors gracefully."""
        # Mock SPY quote to work
        mock_market_service.get_spy_quote = AsyncMock(return_value=QuoteResponse(
            ticker="SPY",
            price=451.25,
            volume=1000000,
            timestamp="2025-01-30T10:00:00",
            market_status="regular",
            cached=False
        ))
        
        # Mock market service to raise exception on options
        mock_market_service.get_spy_options = AsyncMock(
            side_effect=Exception("API error")
        )
        
        # Calculate P/L - should return None and not raise
        result = await pl_service.calculate_position_pl(sample_position)
        
        assert result is None
    
    def test_format_pl_for_display(self, pl_service):
        """Test formatting P/L data for display."""
        # Create P/L data
        pl_data = PositionPLData(
            position_id=1,
            spy_price=Decimal("451.25"),
            current_value=Decimal("-200.00"),
            unrealized_pl=Decimal("50.00"),
            unrealized_pl_percent=Decimal("10.00"),
            risk_percent=Decimal("-10.00"),
            stop_loss_triggered=False,
            calculation_time=datetime.utcnow()
        )
        
        # Format for display
        display_data = pl_service.format_pl_for_display(pl_data)
        
        # Verify formatting
        assert display_data['position_id'] == 1
        assert display_data['unrealized_pl'] == "$50.00"
        assert display_data['unrealized_pl_percent'] == "10.00%"
        assert display_data['status'] == "profit"
        assert display_data['stop_loss_alert'] is False