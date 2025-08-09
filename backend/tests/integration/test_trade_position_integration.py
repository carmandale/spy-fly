"""
Integration tests for trade-position integration functionality.

Tests the complete flow from trade creation to position tracking,
including WebSocket notifications and error handling.
"""

import pytest
import asyncio
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.orm import Session

from app.models.trading import Trade, TradeSpread
from app.models.position import Position
from app.services.trade_position_integration_service import (
    TradePositionIntegrationService,
    TradePositionIntegrationError
)
from app.services.trade_to_position_mapper import TradeToPositionMapper
from app.services.market_service import MarketDataService


class TestTradePositionIntegration:
    """Test suite for trade-position integration functionality."""
    
    @pytest.fixture
    def mock_market_service(self):
        """Mock market service for testing."""
        service = AsyncMock(spec=MarketDataService)
        service.get_spy_price.return_value = {"price": 450.00}
        service.get_vix_data.return_value = {"current_level": 18.5}
        return service
    
    @pytest.fixture
    def integration_service(self, db_session: Session, mock_market_service):
        """Create integration service for testing."""
        return TradePositionIntegrationService(
            db=db_session,
            market_service=mock_market_service
        )
    
    @pytest.fixture
    def sample_trade_data(self):
        """Sample trade data for testing."""
        return {
            "trade_date": date.today(),
            "trade_type": "paper",
            "status": "entered",
            "contracts": 2,
            "max_risk": Decimal("350.00"),
            "max_reward": Decimal("650.00"),
            "probability_of_profit": Decimal("65.0"),
            "entry_signal_reason": "Bullish sentiment with low VIX",
            "notes": "Test trade for integration"
        }
    
    @pytest.fixture
    def sample_spread_data(self):
        """Sample spread data for testing."""
        expiration = date.today() + timedelta(days=30)
        return {
            "spread_type": "bull_call_spread",
            "expiration_date": expiration,
            "long_strike": Decimal("445.00"),
            "short_strike": Decimal("450.00"),
            "long_premium": Decimal("3.50"),
            "short_premium": Decimal("1.75"),
            "net_debit": Decimal("1.75"),
            "max_profit": Decimal("325.00"),
            "max_loss": Decimal("175.00"),
            "breakeven": Decimal("446.75"),
            "risk_reward_ratio": Decimal("1.86")
        }
    
    @pytest.mark.asyncio
    async def test_create_position_from_entered_trade(
        self, 
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test creating position from entered trade with spread."""
        # Create trade with spread
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Create position from trade
        position = await integration_service.create_position_from_trade(trade)
        
        # Verify position was created
        assert position is not None
        assert position.symbol == "SPY"
        assert position.position_type == "bull_call_spread"
        assert position.status == "open"
        assert position.contracts == 2
        assert position.long_strike == 445.00
        assert position.short_strike == 450.00
        assert position.entry_total_cost == 350.00  # 1.75 * 2 * 100
        assert position.max_profit == 325.00
        assert position.max_loss == 175.00
        assert position.entry_spy_price == 450.00
        assert position.entry_vix == 18.5
        assert "Created from trade #" in position.notes
    
    @pytest.mark.asyncio
    async def test_skip_position_creation_for_non_entered_trade(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test that positions are not created for non-entered trades."""
        # Create trade with "recommended" status
        trade_data = sample_trade_data.copy()
        trade_data["status"] = "recommended"
        
        trade = Trade(**trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Attempt to create position
        position = await integration_service.create_position_from_trade(trade)
        
        # Verify no position was created
        assert position is None
    
    @pytest.mark.asyncio
    async def test_skip_position_creation_for_trade_without_spread(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data
    ):
        """Test that positions are not created for trades without spreads."""
        # Create trade without spread
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        # Attempt to create position
        position = await integration_service.create_position_from_trade(trade)
        
        # Verify no position was created
        assert position is None
    
    @pytest.mark.asyncio
    async def test_prevent_duplicate_position_creation(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test that duplicate positions are not created for the same trade parameters."""
        # Create first trade with spread
        trade1 = Trade(**sample_trade_data)
        db_session.add(trade1)
        db_session.flush()
        
        spread1 = TradeSpread(trade_id=trade1.id, **sample_spread_data)
        db_session.add(spread1)
        db_session.flush()
        
        # Create first position
        position1 = await integration_service.create_position_from_trade(trade1)
        assert position1 is not None
        
        # Create second trade with identical parameters
        trade2 = Trade(**sample_trade_data)
        db_session.add(trade2)
        db_session.flush()
        
        spread2 = TradeSpread(trade_id=trade2.id, **sample_spread_data)
        db_session.add(spread2)
        db_session.flush()
        
        # Attempt to create second position
        position2 = await integration_service.create_position_from_trade(trade2)
        
        # Verify same position is returned (no duplicate created)
        assert position2 is not None
        assert position2.id == position1.id
    
    @pytest.mark.asyncio
    async def test_close_position_from_exited_trade(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test closing position when trade is exited."""
        # Create and enter trade
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Create position
        position = await integration_service.create_position_from_trade(trade)
        assert position.status == "open"
        
        # Update trade to exited status
        trade.status = "exited"
        trade.exit_time = datetime.utcnow()
        trade.net_pnl = Decimal("150.00")
        db_session.flush()
        
        # Update position from trade
        updated_position = await integration_service.update_position_from_trade(trade)
        
        # Verify position was closed
        assert updated_position is not None
        assert updated_position.status == "closed"
        assert updated_position.exit_date == trade.trade_date
        assert updated_position.exit_time is not None
        assert updated_position.realized_pnl == 150.00
        assert updated_position.realized_pnl_percent is not None
    
    @pytest.mark.asyncio
    async def test_handle_trade_creation_workflow(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test complete trade creation workflow with position integration."""
        # Create trade with spread
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Mock WebSocket service to avoid actual WebSocket calls
        with patch('app.services.trade_position_integration_service.WebSocketService') as mock_ws:
            mock_ws_instance = AsyncMock()
            mock_ws.return_value = mock_ws_instance
            
            # Handle trade creation
            result = await integration_service.handle_trade_creation(trade)
        
        # Verify result
        assert result["trade_id"] == trade.id
        assert result["position_created"] is True
        assert result["position_id"] is not None
        assert result["websocket_event_sent"] is True
        
        # Verify WebSocket event was sent
        mock_ws_instance.broadcast_position_event.assert_called_once()
        
        # Verify position exists in database
        position = db_session.query(Position).filter(Position.id == result["position_id"]).first()
        assert position is not None
        assert position.status == "open"
    
    @pytest.mark.asyncio
    async def test_handle_trade_update_workflow(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test complete trade update workflow with position integration."""
        # Create trade and position
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        position = await integration_service.create_position_from_trade(trade)
        
        # Update trade status
        trade.status = "exited"
        trade.net_pnl = Decimal("200.00")
        
        # Mock WebSocket service
        with patch('app.services.trade_position_integration_service.WebSocketService') as mock_ws:
            mock_ws_instance = AsyncMock()
            mock_ws.return_value = mock_ws_instance
            
            # Handle trade update
            result = await integration_service.handle_trade_update(trade)
        
        # Verify result
        assert result["trade_id"] == trade.id
        assert result["position_updated"] is True
        assert result["position_id"] == position.id
        assert result["websocket_event_sent"] is True
        
        # Verify WebSocket event was sent
        mock_ws_instance.broadcast_position_event.assert_called_once()
        
        # Verify position was updated
        db_session.refresh(position)
        assert position.status == "closed"
        assert position.realized_pnl == 200.00
    
    @pytest.mark.asyncio
    async def test_error_handling_in_position_creation(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test error handling when position creation fails."""
        # Create trade with spread
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Mock mapper to raise an exception
        with patch.object(integration_service.mapper, 'map_trade_to_position') as mock_mapper:
            mock_mapper.side_effect = Exception("Mapping failed")
            
            # Attempt to create position
            with pytest.raises(TradePositionIntegrationError) as exc_info:
                await integration_service.create_position_from_trade(trade)
            
            assert "Position creation failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_market_service_failure_handling(
        self,
        db_session: Session,
        sample_trade_data,
        sample_spread_data
    ):
        """Test handling of market service failures."""
        # Create mock market service that fails
        mock_market_service = AsyncMock(spec=MarketDataService)
        mock_market_service.get_spy_price.side_effect = Exception("Market data unavailable")
        mock_market_service.get_vix_data.side_effect = Exception("VIX data unavailable")
        
        integration_service = TradePositionIntegrationService(
            db=db_session,
            market_service=mock_market_service
        )
        
        # Create trade with spread
        trade = Trade(**sample_trade_data)
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(trade_id=trade.id, **sample_spread_data)
        db_session.add(spread)
        db_session.flush()
        
        # Create position (should handle market service failures gracefully)
        position = await integration_service.create_position_from_trade(trade)
        
        # Verify position was still created with default values
        assert position is not None
        assert position.entry_spy_price == 0.0  # Default when market service fails
        assert position.entry_vix is None  # Default when VIX service fails
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_positions(
        self,
        integration_service: TradePositionIntegrationService,
        db_session: Session
    ):
        """Test cleanup of orphaned positions."""
        # Create a position without corresponding trade
        orphaned_position = Position(
            symbol="SPY",
            position_type="bull_call_spread",
            status="open",
            contracts=1,
            entry_date=date.today(),
            expiration_date=date.today() + timedelta(days=30),
            long_strike=445.00,
            short_strike=450.00,
            entry_long_premium=3.50,
            entry_short_premium=1.75,
            entry_net_debit=1.75,
            entry_total_cost=175.00,
            max_profit=325.00,
            max_loss=175.00,
            breakeven_price=446.75,
            entry_spy_price=450.00
        )
        db_session.add(orphaned_position)
        db_session.flush()
        
        # Run cleanup
        cleaned_count = await integration_service.cleanup_orphaned_positions()
        
        # Verify orphaned position was cleaned up
        assert cleaned_count == 1
        db_session.refresh(orphaned_position)
        assert orphaned_position.status == "cancelled"
        assert "[Auto-cancelled: no corresponding trade]" in orphaned_position.notes


class TestTradeToPositionMapper:
    """Test suite for trade-to-position data mapping."""
    
    @pytest.fixture
    def mapper(self):
        """Create mapper for testing."""
        return TradeToPositionMapper()
    
    @pytest.fixture
    def sample_trade_with_spread(self, db_session: Session):
        """Create sample trade with spread for testing."""
        trade = Trade(
            trade_date=date.today(),
            trade_type="paper",
            status="entered",
            contracts=2,
            probability_of_profit=Decimal("65.0"),
            entry_signal_reason="Test signal",
            notes="Test trade"
        )
        db_session.add(trade)
        db_session.flush()
        
        spread = TradeSpread(
            trade_id=trade.id,
            spread_type="bull_call_spread",
            expiration_date=date.today() + timedelta(days=30),
            long_strike=Decimal("445.00"),
            short_strike=Decimal("450.00"),
            long_premium=Decimal("3.50"),
            short_premium=Decimal("1.75"),
            net_debit=Decimal("1.75"),
            max_profit=Decimal("325.00"),
            max_loss=Decimal("175.00"),
            breakeven=Decimal("446.75"),
            risk_reward_ratio=Decimal("1.86")
        )
        db_session.add(spread)
        db_session.flush()
        
        return trade
    
    def test_map_trade_to_position_success(
        self,
        mapper: TradeToPositionMapper,
        sample_trade_with_spread: Trade
    ):
        """Test successful mapping of trade to position data."""
        current_spy_price = 450.00
        current_vix = 18.5
        
        position_data = mapper.map_trade_to_position(
            trade=sample_trade_with_spread,
            current_spy_price=current_spy_price,
            current_vix=current_vix
        )
        
        # Verify basic fields
        assert position_data["symbol"] == "SPY"
        assert position_data["position_type"] == "bull_call_spread"
        assert position_data["status"] == "open"
        assert position_data["contracts"] == 2
        
        # Verify spread configuration
        assert position_data["long_strike"] == 445.00
        assert position_data["short_strike"] == 450.00
        
        # Verify pricing
        assert position_data["entry_long_premium"] == 3.50
        assert position_data["entry_short_premium"] == 1.75
        assert position_data["entry_net_debit"] == 1.75
        assert position_data["entry_total_cost"] == 350.00  # 1.75 * 2 * 100
        
        # Verify risk metrics
        assert position_data["max_profit"] == 325.00
        assert position_data["max_loss"] == 175.00
        assert position_data["breakeven_price"] == 446.75
        
        # Verify market conditions
        assert position_data["entry_spy_price"] == current_spy_price
        assert position_data["entry_vix"] == current_vix
        
        # Verify position management
        assert position_data["profit_target_percent"] == 55.0  # Based on risk/reward ratio
        assert position_data["stop_loss_percent"] == 20.0
        
        # Verify notes
        assert "Created from trade #" in position_data["notes"]
        assert "Test signal" in position_data["notes"]
    
    def test_map_trade_without_spread_fails(
        self,
        mapper: TradeToPositionMapper,
        db_session: Session
    ):
        """Test that mapping fails for trade without spread."""
        trade = Trade(
            trade_date=date.today(),
            trade_type="paper",
            status="entered",
            contracts=1
        )
        db_session.add(trade)
        db_session.flush()
        
        with pytest.raises(Exception) as exc_info:
            mapper.map_trade_to_position(
                trade=trade,
                current_spy_price=450.00
            )
        
        assert "Trade must have spread data" in str(exc_info.value)
    
    def test_validation_of_mapped_data(
        self,
        mapper: TradeToPositionMapper,
        sample_trade_with_spread: Trade
    ):
        """Test validation of mapped position data."""
        # Test with invalid SPY price
        with pytest.raises(Exception) as exc_info:
            mapper.map_trade_to_position(
                trade=sample_trade_with_spread,
                current_spy_price=-100.00  # Invalid negative price
            )
        
        assert "SPY price must be positive" in str(exc_info.value)
    
    def test_profit_target_calculation_based_on_risk_reward(
        self,
        mapper: TradeToPositionMapper
    ):
        """Test profit target calculation based on risk/reward ratio."""
        # Test high risk/reward ratio
        assert mapper._calculate_profit_target_percent(
            MagicMock(risk_reward_ratio=Decimal("2.5"))
        ) == 60.0
        
        # Test medium risk/reward ratio
        assert mapper._calculate_profit_target_percent(
            MagicMock(risk_reward_ratio=Decimal("1.7"))
        ) == 55.0
        
        # Test low risk/reward ratio
        assert mapper._calculate_profit_target_percent(
            MagicMock(risk_reward_ratio=Decimal("0.8"))
        ) == 40.0
        
        # Test default case
        assert mapper._calculate_profit_target_percent(
            MagicMock(risk_reward_ratio=None)
        ) == 50.0
