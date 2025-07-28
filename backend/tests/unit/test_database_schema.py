"""Tests for database schema creation and migration."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.db_models import (
    APIRequestLog,
    HistoricalPrice,
    MarketDataCache,
    OptionContract,
    SPYQuote,
)


class TestDatabaseSchema:
    """Test database schema creation and table structures."""

    def test_create_all_tables(self, test_engine):
        """Test that all tables are created successfully."""
        # Create all tables
        Base.metadata.create_all(bind=test_engine)

        # Get inspector to check tables
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()

        # Verify all expected tables exist
        expected_tables = [
            "market_data_cache",
            "spy_quotes",
            "option_contracts",
            "historical_prices",
            "api_requests_log",
        ]

        for table_name in expected_tables:
            assert table_name in tables, f"Table {table_name} not created"

    def test_market_data_cache_schema(self, test_engine):
        """Test market_data_cache table schema."""
        Base.metadata.create_all(bind=test_engine)
        inspector = inspect(test_engine)

        columns = {
            col["name"]: col for col in inspector.get_columns("market_data_cache")
        }

        # Check column existence and types
        assert "id" in columns
        # Note: SQLite inspector doesn't return primary_key in columns dict
        # Check primary key via constraints instead
        pk_constraint = inspector.get_pk_constraint("market_data_cache")
        assert "id" in pk_constraint["constrained_columns"]

        assert "cache_key" in columns
        assert columns["cache_key"]["nullable"] is False

        assert "data_type" in columns
        assert "raw_data" in columns
        assert "created_at" in columns
        assert "expires_at" in columns

        # Check indexes
        indexes = inspector.get_indexes("market_data_cache")
        index_columns = [idx["column_names"] for idx in indexes]

        assert ["cache_key"] in index_columns
        assert ["expires_at"] in index_columns
        assert ["data_type"] in index_columns

    def test_spy_quotes_schema(self, test_engine):
        """Test spy_quotes table schema."""
        Base.metadata.create_all(bind=test_engine)
        inspector = inspect(test_engine)

        columns = {col["name"]: col for col in inspector.get_columns("spy_quotes")}

        # Check required columns
        required_columns = ["id", "symbol", "price", "timestamp", "source"]
        for col in required_columns:
            assert col in columns, f"Column {col} missing"

        # Check optional columns
        assert "bid" in columns
        assert "ask" in columns
        assert "volume" in columns

        # Check indexes
        indexes = inspector.get_indexes("spy_quotes")
        index_columns = [idx["column_names"] for idx in indexes]

        assert ["timestamp"] in index_columns
        assert ["symbol", "timestamp"] in index_columns

    def test_option_contracts_schema(self, test_engine):
        """Test option_contracts table schema."""
        Base.metadata.create_all(bind=test_engine)
        inspector = inspect(test_engine)

        columns = {
            col["name"]: col for col in inspector.get_columns("option_contracts")
        }

        # Check all columns exist
        expected_columns = [
            "id",
            "symbol",
            "underlying",
            "strike",
            "option_type",
            "expiration_date",
            "bid",
            "ask",
            "last_price",
            "volume",
            "open_interest",
            "timestamp",
            "created_at",
        ]

        for col in expected_columns:
            assert col in columns, f"Column {col} missing"

        # Check constraints
        unique_constraints = inspector.get_unique_constraints("option_contracts")
        unique_columns = [constr["column_names"] for constr in unique_constraints]
        assert ["symbol", "timestamp"] in unique_columns

    def test_historical_prices_schema(self, test_engine):
        """Test historical_prices table schema."""
        Base.metadata.create_all(bind=test_engine)
        inspector = inspect(test_engine)

        columns = {
            col["name"]: col for col in inspector.get_columns("historical_prices")
        }

        # Check OHLCV columns
        ohlcv_columns = [
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
        ]
        for col in ohlcv_columns:
            assert col in columns, f"OHLCV column {col} missing"

        # Check other required columns
        assert "symbol" in columns
        assert "date" in columns
        assert "timeframe" in columns

        # Check unique constraint
        unique_constraints = inspector.get_unique_constraints("historical_prices")
        unique_columns = [constr["column_names"] for constr in unique_constraints]
        assert ["symbol", "date", "timeframe"] in unique_columns


class TestDatabaseModels:
    """Test SQLAlchemy model operations."""

    def test_market_data_cache_crud(self, test_session: Session):
        """Test CRUD operations on MarketDataCache model."""
        # Create
        cache_entry = MarketDataCache(
            cache_key="SPY_QUOTE_2025-07-27",
            data_type="quote",
            raw_data='{"symbol": "SPY", "price": 580.50}',
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        test_session.add(cache_entry)
        test_session.commit()

        # Read
        retrieved = (
            test_session.query(MarketDataCache)
            .filter_by(cache_key="SPY_QUOTE_2025-07-27")
            .first()
        )

        assert retrieved is not None
        assert retrieved.data_type == "quote"
        assert retrieved.raw_data == '{"symbol": "SPY", "price": 580.50}'

        # Update
        retrieved.expires_at = datetime.now(UTC) + timedelta(minutes=10)
        test_session.commit()

        # Delete expired entries
        expired_time = datetime.now(UTC) - timedelta(minutes=1)
        test_session.query(MarketDataCache).filter(
            MarketDataCache.expires_at < expired_time
        ).delete()
        test_session.commit()

    def test_spy_quote_crud(self, test_session: Session):
        """Test CRUD operations on SPYQuote model."""
        # Create
        quote = SPYQuote(
            price=Decimal("580.50"),
            bid=Decimal("580.48"),
            ask=Decimal("580.52"),
            volume=1000000,
            timestamp=datetime.now(UTC),
        )
        test_session.add(quote)
        test_session.commit()

        # Read
        latest_quote = (
            test_session.query(SPYQuote).order_by(SPYQuote.timestamp.desc()).first()
        )

        assert latest_quote is not None
        assert latest_quote.price == Decimal("580.50")
        assert latest_quote.symbol == "SPY"  # Check default
        assert latest_quote.source == "polygon"  # Check default

    def test_option_contract_crud(self, test_session: Session):
        """Test CRUD operations on OptionContract model."""
        # Create
        contract = OptionContract(
            symbol="SPY250727C00580000",
            strike=Decimal("580.00"),
            option_type="call",
            expiration_date=datetime.strptime("2025-07-27", "%Y-%m-%d").date(),
            bid=Decimal("2.50"),
            ask=Decimal("2.55"),
            last_price=Decimal("2.52"),
            volume=5000,
            open_interest=10000,
            timestamp=datetime.now(UTC),
        )
        test_session.add(contract)
        test_session.commit()

        # Read - find 0-DTE options
        today = datetime.now(UTC).date()
        zero_dte = (
            test_session.query(OptionContract)
            .filter(
                OptionContract.expiration_date == today,
                OptionContract.underlying == "SPY",
            )
            .all()
        )

        # Verify defaults
        assert contract.underlying == "SPY"

    def test_historical_price_crud(self, test_session: Session):
        """Test CRUD operations on HistoricalPrice model."""
        # Create
        price = HistoricalPrice(
            date=datetime.now(UTC).date(),
            timeframe="daily",
            open_price=Decimal("579.00"),
            high_price=Decimal("581.00"),
            low_price=Decimal("578.50"),
            close_price=Decimal("580.50"),
            volume=50000000,
            vwap=Decimal("579.75"),
        )
        test_session.add(price)
        test_session.commit()

        # Read - find daily data
        daily_prices = (
            test_session.query(HistoricalPrice)
            .filter(
                HistoricalPrice.timeframe == "daily", HistoricalPrice.symbol == "SPY"
            )
            .all()
        )

        assert len(daily_prices) > 0
        assert daily_prices[0].symbol == "SPY"  # Check default

    def test_api_request_log_crud(self, test_session: Session):
        """Test CRUD operations on APIRequestLog model."""
        # Create success log
        success_log = APIRequestLog(
            endpoint="/v3/quotes/SPY",
            method="GET",
            status_code=200,
            response_time_ms=150,
        )
        test_session.add(success_log)

        # Create error log
        error_log = APIRequestLog(
            endpoint="/v3/options/SPY",
            method="GET",
            status_code=429,
            response_time_ms=50,
            error_message="Rate limit exceeded",
        )
        test_session.add(error_log)
        test_session.commit()

        # Read - find errors
        errors = (
            test_session.query(APIRequestLog)
            .filter(APIRequestLog.status_code >= 400)
            .all()
        )

        assert len(errors) == 1
        assert errors[0].error_message == "Rate limit exceeded"

    def test_cascade_deletes(self, test_session: Session):
        """Test that no cascade deletes are configured (independent tables)."""
        # These tables should not have foreign key relationships
        # so deleting from one should not affect others

        # Create entries in multiple tables
        quote = SPYQuote(price=Decimal("580.50"), timestamp=datetime.now(UTC))
        test_session.add(quote)
        test_session.commit()

        cache = MarketDataCache(
            cache_key="test_key",
            data_type="quote",
            raw_data="{}",
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        test_session.add(cache)
        test_session.commit()

        # Delete quote - should not affect cache
        test_session.delete(quote)
        test_session.commit()

        # Cache should still exist
        assert test_session.query(MarketDataCache).count() == 1


class TestDatabaseMigration:
    """Test Alembic migration functionality."""

    def test_alembic_init(self, tmp_path):
        """Test Alembic can be initialized."""
        # This will be implemented when we set up Alembic
        # For now, just verify we can import alembic
        try:
            import alembic

            assert alembic is not None
        except ImportError:
            pytest.skip("Alembic not installed yet")

    def test_migration_up_down(self, test_engine):
        """Test migration can be applied and rolled back."""
        # This will be implemented after creating the migration
        # For now, just ensure tables can be created and dropped
        Base.metadata.create_all(bind=test_engine)
        Base.metadata.drop_all(bind=test_engine)

        # Verify tables are gone
        inspector = inspect(test_engine)
        tables = inspector.get_table_names()
        assert len(tables) == 0
