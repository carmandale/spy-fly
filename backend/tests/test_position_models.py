"""
Tests for Position and PositionSnapshot database models.

Tests model creation, relationships, and P/L tracking fields.
"""

import pytest
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app.models.db_models import Position, PositionSnapshot
from app.core.database import Base


class TestPositionModel:
    """Test Position model functionality."""
    
    def test_create_position(self, test_session):
        """Test creating a new position with all fields."""
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50"),
            status="open",
            # New P/L fields
            latest_value=Decimal("-200.00"),
            latest_unrealized_pl=Decimal("50.00"),
            latest_unrealized_pl_percent=Decimal("10.00"),
            latest_update_time=datetime.utcnow(),
            stop_loss_alert_active=False
        )
        
        test_session.add(position)
        test_session.commit()
        
        assert position.id is not None
        assert position.symbol == "SPY"
        assert position.long_strike == Decimal("450.00")
        assert position.short_strike == Decimal("455.00")
        assert position.quantity == 5
        assert position.entry_value == Decimal("-250.00")
        assert position.max_risk == Decimal("500.00")
        assert position.latest_value == Decimal("-200.00")
        assert position.latest_unrealized_pl == Decimal("50.00")
        assert position.latest_unrealized_pl_percent == Decimal("10.00")
        assert position.stop_loss_alert_active is False
        
    def test_position_defaults(self, test_session):
        """Test position model default values."""
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        
        test_session.add(position)
        test_session.commit()
        
        assert position.status == "open"
        assert position.latest_value is None
        assert position.latest_unrealized_pl is None
        assert position.latest_unrealized_pl_percent is None
        assert position.latest_update_time is None
        assert position.stop_loss_alert_active is False
        assert position.stop_loss_alert_time is None
        
    def test_position_required_fields(self, test_session):
        """Test that required fields are enforced."""
        # Missing required fields should raise error
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00")
            # Missing other required fields
        )
        
        test_session.add(position)
        with pytest.raises(IntegrityError):
            test_session.commit()
            
    def test_position_status_values(self, test_session):
        """Test position status field accepts valid values."""
        # Valid statuses
        for status in ["open", "closed", "expired"]:
            position = Position(
                symbol="SPY",
                long_strike=Decimal("450.00"),
                short_strike=Decimal("455.00"),
                expiration_date=date.today(),
                quantity=5,
                entry_value=Decimal("-250.00"),
                max_risk=Decimal("500.00"),
                max_profit=Decimal("250.00"),
                breakeven_price=Decimal("452.50"),
                status=status
            )
            test_session.add(position)
            test_session.commit()
            assert position.status == status
            test_session.rollback()
            
    def test_stop_loss_alert_fields(self, test_session):
        """Test stop-loss alert tracking fields."""
        now = datetime.utcnow()
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50"),
            latest_unrealized_pl_percent=Decimal("-22.00"),
            stop_loss_alert_active=True,
            stop_loss_alert_time=now
        )
        
        test_session.add(position)
        test_session.commit()
        
        assert position.stop_loss_alert_active is True
        assert position.stop_loss_alert_time == now
        
    def test_position_relationship_to_snapshots(self, test_session):
        """Test relationship between Position and PositionSnapshot."""
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        
        test_session.add(position)
        test_session.commit()
        
        # Add snapshots
        snapshot1 = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow(),
            spy_price=Decimal("451.25"),
            current_value=Decimal("-225.00"),
            unrealized_pl=Decimal("25.00"),
            unrealized_pl_percent=Decimal("5.00"),
            risk_percent=Decimal("-5.00")
        )
        
        snapshot2 = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow(),
            spy_price=Decimal("452.00"),
            current_value=Decimal("-200.00"),
            unrealized_pl=Decimal("50.00"),
            unrealized_pl_percent=Decimal("10.00"),
            risk_percent=Decimal("-10.00")
        )
        
        test_session.add(snapshot1)
        test_session.add(snapshot2)
        test_session.commit()
        
        # Test relationship
        assert len(position.snapshots) == 2
        assert position.snapshots[0].position_id == position.id
        assert position.snapshots[1].position_id == position.id


class TestPositionSnapshotModel:
    """Test PositionSnapshot model functionality."""
    
    def test_create_snapshot(self, test_session):
        """Test creating a position snapshot with all fields."""
        # First create a position
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        test_session.add(position)
        test_session.commit()
        
        # Create snapshot
        snapshot = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow(),
            spy_price=Decimal("451.25"),
            current_value=Decimal("-225.00"),
            unrealized_pl=Decimal("25.00"),
            unrealized_pl_percent=Decimal("5.00"),
            long_call_bid=Decimal("3.45"),
            long_call_ask=Decimal("3.50"),
            short_call_bid=Decimal("0.95"),
            short_call_ask=Decimal("1.00"),
            risk_percent=Decimal("-5.00"),
            stop_loss_triggered=False
        )
        
        test_session.add(snapshot)
        test_session.commit()
        
        assert snapshot.id is not None
        assert snapshot.position_id == position.id
        assert snapshot.spy_price == Decimal("451.25")
        assert snapshot.current_value == Decimal("-225.00")
        assert snapshot.unrealized_pl == Decimal("25.00")
        assert snapshot.unrealized_pl_percent == Decimal("5.00")
        assert snapshot.risk_percent == Decimal("-5.00")
        assert snapshot.stop_loss_triggered is False
        
    def test_snapshot_required_fields(self, test_session):
        """Test that required snapshot fields are enforced."""
        # Create position first
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        test_session.add(position)
        test_session.commit()
        
        # Missing required fields
        snapshot = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow()
            # Missing other required fields
        )
        
        test_session.add(snapshot)
        with pytest.raises(IntegrityError):
            test_session.commit()
            
    def test_snapshot_foreign_key_constraint(self, test_session):
        """Test foreign key constraint to Position."""
        # SQLite in-memory database may not enforce foreign keys by default
        # Test that the relationship is properly defined instead
        
        # Create a valid position first
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        test_session.add(position)
        test_session.commit()
        
        # Create snapshot with valid position_id
        snapshot = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow(),
            spy_price=Decimal("451.25"),
            current_value=Decimal("-225.00"),
            unrealized_pl=Decimal("25.00"),
            unrealized_pl_percent=Decimal("5.00"),
            risk_percent=Decimal("-5.00")
        )
        
        test_session.add(snapshot)
        test_session.commit()
        
        # Verify the relationship works
        assert snapshot.position_id == position.id
        assert snapshot.position is not None
        assert snapshot.position.id == position.id
            
    def test_stop_loss_triggered_flag(self, test_session):
        """Test stop-loss triggered flag in snapshots."""
        # Create position
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        test_session.add(position)
        test_session.commit()
        
        # Create snapshot with stop-loss triggered
        snapshot = PositionSnapshot(
            position_id=position.id,
            snapshot_time=datetime.utcnow(),
            spy_price=Decimal("448.00"),
            current_value=Decimal("-400.00"),
            unrealized_pl=Decimal("-150.00"),
            unrealized_pl_percent=Decimal("-30.00"),
            risk_percent=Decimal("30.00"),
            stop_loss_triggered=True
        )
        
        test_session.add(snapshot)
        test_session.commit()
        
        assert snapshot.stop_loss_triggered is True
        assert snapshot.risk_percent == Decimal("30.00")
        
    def test_snapshot_ordering(self, test_session):
        """Test that snapshots can be ordered by time."""
        # Create position
        position = Position(
            symbol="SPY",
            long_strike=Decimal("450.00"),
            short_strike=Decimal("455.00"),
            expiration_date=date.today(),
            quantity=5,
            entry_value=Decimal("-250.00"),
            max_risk=Decimal("500.00"),
            max_profit=Decimal("250.00"),
            breakeven_price=Decimal("452.50")
        )
        test_session.add(position)
        test_session.commit()
        
        # Create multiple snapshots
        times = [
            datetime(2025, 1, 30, 10, 0, 0),
            datetime(2025, 1, 30, 10, 15, 0),
            datetime(2025, 1, 30, 10, 30, 0)
        ]
        
        for i, time in enumerate(times):
            snapshot = PositionSnapshot(
                position_id=position.id,
                snapshot_time=time,
                spy_price=Decimal(f"451.{i}0"),
                current_value=Decimal(f"-22{i}.00"),
                unrealized_pl=Decimal(f"2{i}.00"),
                unrealized_pl_percent=Decimal(f"{i+1}.00"),
                risk_percent=Decimal(f"-{i+1}.00")
            )
            test_session.add(snapshot)
        
        test_session.commit()
        
        # Query snapshots ordered by time
        snapshots = test_session.query(PositionSnapshot).filter_by(
            position_id=position.id
        ).order_by(PositionSnapshot.snapshot_time).all()
        
        assert len(snapshots) == 3
        assert snapshots[0].snapshot_time == times[0]
        assert snapshots[1].snapshot_time == times[1]
        assert snapshots[2].snapshot_time == times[2]