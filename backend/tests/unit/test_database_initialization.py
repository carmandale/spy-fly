"""Tests for database initialization and connection."""

import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from app.core.database import Base, engine, SessionLocal, get_db
from app.config import settings


class TestDatabaseInitialization:
    """Test database initialization and connection."""
    
    def test_database_url_configuration(self):
        """Test that database URL is properly configured."""
        assert settings.database_url is not None
        assert settings.database_url.startswith("sqlite://")
        assert "spy_fly.db" in settings.database_url
    
    def test_create_database_file(self, tmp_path):
        """Test database file creation with proper permissions."""
        # Create a temporary database file path
        db_path = tmp_path / "test_spy_fly.db"
        db_url = f"sqlite:///{db_path}"
        
        # Create engine with temporary database
        test_engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False}
        )
        
        # Create all tables
        Base.metadata.create_all(bind=test_engine)
        
        # Verify database file exists
        assert db_path.exists()
        
        # Check file permissions (readable and writable)
        assert os.access(db_path, os.R_OK)
        assert os.access(db_path, os.W_OK)
        
        # Clean up
        test_engine.dispose()
    
    def test_database_connection(self):
        """Test that we can connect to the database."""
        # Create a test connection
        with engine.connect() as conn:
            # Execute a simple query
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    def test_session_creation(self):
        """Test that we can create database sessions."""
        # Create a session
        session = SessionLocal()
        
        try:
            # Verify session is connected
            session.execute(text("SELECT 1"))
            assert session.is_active
        finally:
            session.close()
    
    def test_get_db_dependency(self):
        """Test the get_db dependency function."""
        # Get a database session using the dependency
        db_gen = get_db()
        db = next(db_gen)
        
        try:
            # Verify we got a valid session
            assert db is not None
            db.execute(text("SELECT 1"))
        finally:
            # Clean up
            try:
                next(db_gen)
            except StopIteration:
                pass
    
    def test_sqlite_specific_settings(self):
        """Test SQLite-specific connection settings."""
        # For SQLite, we need to check that the engine was created with proper connect_args
        # This is a simplified test since we can't directly access connect_args from the engine
        # We'll just verify the engine works with multiple threads
        from threading import Thread
        
        def query_in_thread():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        
        # This would fail if check_same_thread wasn't False
        thread = Thread(target=query_in_thread)
        thread.start()
        thread.join()
    
    def test_database_initialization_module(self):
        """Test that database initialization module exists and works."""
        # Import the initialization module
        from app.core import db_init
        
        # Test initialization function
        assert hasattr(db_init, 'init_db')
        assert callable(db_init.init_db)
        
        # Test that it can be called without errors
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_init.db"
            db_url = f"sqlite:///{db_path}"
            db_init.init_db(db_url)
            
            # Verify database was created
            assert db_path.exists()
            
            # Verify tables were created
            test_engine = create_engine(db_url)
            inspector = inspect(test_engine)
            tables = inspector.get_table_names()
            
            # Check for trading-specific tables
            expected_tables = [
                'trades',
                'sentiment_scores',
                'trade_spreads',
                'configuration',
                'daily_summaries'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} not found in database"
            
            test_engine.dispose()
    
    def test_database_url_validation(self):
        """Test database URL validation in configuration."""
        # The configuration should validate the database URL
        is_valid, errors = settings.validate_startup_configuration()
        
        # Check that database URL validation is included
        if not settings.database_url:
            assert not is_valid
            assert any("DATABASE_URL" in error for error in errors)
    
    def test_concurrent_connections(self):
        """Test that multiple connections can be created simultaneously."""
        sessions = []
        
        try:
            # Create multiple sessions
            for _ in range(5):
                session = SessionLocal()
                sessions.append(session)
                
                # Execute a query in each session
                result = session.execute(text("SELECT 1"))
                assert result.scalar() == 1
        finally:
            # Clean up all sessions
            for session in sessions:
                session.close()
    
    def test_database_error_handling(self):
        """Test proper error handling for database operations."""
        # Create an invalid engine
        bad_engine = create_engine("sqlite:///nonexistent/path/db.db")
        
        # Attempt to connect should raise an error
        with pytest.raises(OperationalError):
            with bad_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        
        bad_engine.dispose()