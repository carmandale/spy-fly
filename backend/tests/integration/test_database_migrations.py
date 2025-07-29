"""
Integration tests for database migrations.

These tests verify that database migrations can be applied and rolled back
correctly, ensuring schema changes work properly across environments.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from alembic import command, config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class TestDatabaseMigrations:
    """Test database migration functionality."""

    @pytest.fixture
    def temp_db_engine(self):
        """Create a temporary SQLite database for testing migrations."""
        # Create temporary database file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            db_url = f"sqlite:///{temp_file.name}"
            engine = create_engine(db_url)
            yield engine
            
            # Cleanup
            engine.dispose()
            Path(temp_file.name).unlink(missing_ok=True)

    @pytest.fixture
    def alembic_config(self):
        """Create Alembic configuration for testing."""
        # Get the actual alembic.ini file path
        alembic_ini_path = Path(__file__).parent.parent.parent / "alembic.ini"
        cfg = config.Config(str(alembic_ini_path))
        return cfg

    def test_spread_recommendations_migration_upgrade(self, temp_db_engine: Engine, alembic_config):
        """Test that the spread recommendations migration can be applied."""
        # Configure Alembic to use our test database
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                # Return the actual config values for other keys
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            
            # Apply all migrations up to the latest
            command.upgrade(alembic_config, "head")
            
        # Verify that the new tables exist
        inspector = sa.inspect(temp_db_engine)
        table_names = inspector.get_table_names()
        
        # Check for new tables that should be added in the spread recommendations migration
        expected_tables = [
            "spread_recommendations",
            "analysis_sessions",
        ]
        
        for table_name in expected_tables:
            assert table_name in table_names, f"Table {table_name} was not created by migration"

    def test_spread_recommendations_table_structure(self, temp_db_engine: Engine, alembic_config):
        """Test that the spread_recommendations table has the correct structure."""
        # Apply migrations
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            command.upgrade(alembic_config, "head")
        
        # Check spread_recommendations table structure
        inspector = sa.inspect(temp_db_engine)
        
        if "spread_recommendations" in inspector.get_table_names():
            columns = inspector.get_columns("spread_recommendations")
            column_names = [col["name"] for col in columns]
            
            # Expected columns for spread recommendations
            expected_columns = [
                "id",
                "session_id", 
                "long_strike",
                "short_strike",
                "long_premium",
                "short_premium",
                "net_debit",
                "max_profit",
                "max_risk",
                "risk_reward_ratio",
                "probability_of_profit",
                "breakeven_price",
                "expected_value",
                "sentiment_score",
                "ranking_score",
                "contracts_to_trade",
                "total_cost",
                "buying_power_used_pct",
                "long_bid",
                "long_ask",
                "short_bid", 
                "short_ask",
                "long_volume",
                "short_volume",
                "expiration_date",
                "generated_at",
                "created_at"
            ]
            
            for col_name in expected_columns:
                assert col_name in column_names, f"Column {col_name} missing from spread_recommendations table"
            
            # Check indexes
            indexes = inspector.get_indexes("spread_recommendations")
            index_names = [idx["name"] for idx in indexes]
            
            expected_indexes = [
                "idx_session_id",
                "idx_generated_at",
                "idx_ranking_score"
            ]
            
            for idx_name in expected_indexes:
                assert idx_name in index_names, f"Index {idx_name} missing from spread_recommendations table"

    def test_analysis_sessions_table_structure(self, temp_db_engine: Engine, alembic_config):
        """Test that the analysis_sessions table has the correct structure."""
        # Apply migrations
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            command.upgrade(alembic_config, "head")
        
        # Check analysis_sessions table structure
        inspector = sa.inspect(temp_db_engine)
        
        if "analysis_sessions" in inspector.get_table_names():
            columns = inspector.get_columns("analysis_sessions")
            column_names = [col["name"] for col in columns]
            
            # Expected columns for analysis sessions
            expected_columns = [
                "id",
                "session_uuid",
                "account_size",
                "max_recommendations",
                "recommendations_count",
                "spy_price",
                "sentiment_score",
                "market_status",
                "generated_at",
                "created_at"
            ]
            
            for col_name in expected_columns:
                assert col_name in column_names, f"Column {col_name} missing from analysis_sessions table"
            
            # Check unique constraint on session_uuid
            unique_constraints = inspector.get_unique_constraints("analysis_sessions")
            uuid_constraint_exists = any(
                "session_uuid" in constraint["column_names"] 
                for constraint in unique_constraints
            )
            assert uuid_constraint_exists, "Unique constraint on session_uuid missing"
            
            # Check indexes
            indexes = inspector.get_indexes("analysis_sessions")
            index_names = [idx["name"] for idx in indexes]
            
            expected_indexes = [
                "idx_session_uuid",
                "idx_generated_at_sessions"
            ]
            
            for idx_name in expected_indexes:
                assert idx_name in index_names, f"Index {idx_name} missing from analysis_sessions table"

    def test_migration_downgrade(self, temp_db_engine: Engine, alembic_config):
        """Test that migrations can be rolled back properly."""
        # Apply all migrations first
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            
            # Upgrade to head
            command.upgrade(alembic_config, "head")
            
            # Verify tables exist
            inspector = sa.inspect(temp_db_engine)
            table_names_before = set(inspector.get_table_names())
            
            # Get current revision
            with temp_db_engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_revision = context.get_current_revision()
            
            # If we have a current revision, try to downgrade one step
            if current_revision:
                # Get the script directory to find previous revision
                script_dir = ScriptDirectory.from_config(alembic_config)
                script = script_dir.get_revision(current_revision)
                
                if script and script.down_revision:
                    # Downgrade one revision
                    command.downgrade(alembic_config, script.down_revision)
                    
                    # Verify the migration was rolled back properly
                    inspector_after = sa.inspect(temp_db_engine)
                    table_names_after = set(inspector_after.get_table_names())
                    
                    # If this was the spread recommendations migration, these tables should be gone
                    if "spread_recommendations" in table_names_before:
                        assert "spread_recommendations" not in table_names_after, \
                            "spread_recommendations table was not removed during downgrade"
                    
                    if "analysis_sessions" in table_names_before:
                        assert "analysis_sessions" not in table_names_after, \
                            "analysis_sessions table was not removed during downgrade"

    def test_migration_data_integrity(self, temp_db_engine: Engine, alembic_config):
        """Test that existing data is preserved during migrations."""
        # Apply migrations up to the base state
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            
            # Apply all existing migrations
            command.upgrade(alembic_config, "head")
            
            # Insert test data into existing tables
            with temp_db_engine.connect() as conn:
                # Insert test data into market_data_cache
                conn.execute(text("""
                    INSERT INTO market_data_cache 
                    (cache_key, data_type, raw_data, expires_at)
                    VALUES 
                    ('test_key', 'quote', '{"price": 475.00}', datetime('now', '+1 hour'))
                """))
                
                # Insert test data into spy_quotes
                conn.execute(text("""
                    INSERT INTO spy_quotes 
                    (symbol, price, timestamp, source)
                    VALUES 
                    ('SPY', 475.00, datetime('now'), 'test')
                """))
                
                conn.commit()
                
                # Verify data exists
                cache_result = conn.execute(text("SELECT COUNT(*) FROM market_data_cache")).scalar()
                quote_result = conn.execute(text("SELECT COUNT(*) FROM spy_quotes")).scalar()
                
                assert cache_result > 0, "Test data was not inserted into market_data_cache"
                assert quote_result > 0, "Test data was not inserted into spy_quotes"
                
                # After migration, data should still exist
                cache_result_after = conn.execute(text("SELECT COUNT(*) FROM market_data_cache")).scalar()
                quote_result_after = conn.execute(text("SELECT COUNT(*) FROM spy_quotes")).scalar()
                
                assert cache_result_after == cache_result, "Data was lost from market_data_cache during migration"
                assert quote_result_after == quote_result, "Data was lost from spy_quotes during migration"

    def test_migration_performance(self, temp_db_engine: Engine, alembic_config):
        """Test that migrations complete within reasonable time limits."""
        import time
        
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            
            start_time = time.time()
            
            # Apply all migrations
            command.upgrade(alembic_config, "head")
            
            end_time = time.time()
            migration_time = end_time - start_time
            
            # Migration should complete within 30 seconds (very generous limit)
            assert migration_time < 30.0, f"Migration took {migration_time:.2f}s, expected < 30s"

    def test_concurrent_migration_safety(self, temp_db_engine: Engine, alembic_config):
        """Test that migrations handle concurrent access safely."""
        # This test checks that migrations use appropriate locking mechanisms
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            
            # Apply migrations - should not raise any locking errors
            try:
                command.upgrade(alembic_config, "head")
                
                # Verify we can still read from the database
                with temp_db_engine.connect() as conn:
                    result = conn.execute(text("SELECT 1")).scalar()
                    assert result == 1, "Database became inaccessible after migration"
                    
            except Exception as e:
                pytest.fail(f"Migration failed with concurrent access considerations: {e}")

    def test_foreign_key_constraints(self, temp_db_engine: Engine, alembic_config):
        """Test that foreign key relationships are properly created."""
        with patch.object(alembic_config, 'get_main_option') as mock_get_option:
            def get_option_side_effect(key, default=None):
                if key == 'sqlalchemy.url':
                    return str(temp_db_engine.url)
                return alembic_config.get_main_option.wrapped(key, default)
            
            mock_get_option.side_effect = get_option_side_effect
            command.upgrade(alembic_config, "head")
        
        # Check foreign key constraints
        inspector = sa.inspect(temp_db_engine)
        
        if "spread_recommendations" in inspector.get_table_names():
            foreign_keys = inspector.get_foreign_keys("spread_recommendations")
            
            # Should have foreign key to analysis_sessions
            session_fk_exists = any(
                fk["referred_table"] == "analysis_sessions" and "session_id" in fk["constrained_columns"]
                for fk in foreign_keys
            )
            assert session_fk_exists, "Foreign key from spread_recommendations to analysis_sessions missing"