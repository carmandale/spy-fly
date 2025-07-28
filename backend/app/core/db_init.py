"""Database initialization module for SPY-FLY."""

import logging
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.trading import (
    Configuration,
)

logger = logging.getLogger(__name__)


def init_db(database_url: str = None) -> None:
    """
    Initialize the database with all tables and seed data.

    Args:
        database_url: Optional database URL. If not provided, uses settings.
    """
    if database_url is None:
        from app.config import settings

        database_url = settings.database_url

    # Ensure the database directory exists if using SQLite
    if database_url.startswith("sqlite://"):
        db_path = database_url.replace("sqlite:///", "")
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Create engine
    engine = create_engine(
        database_url,
        connect_args=(
            {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        ),
    )

    # Create all tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)

    # Verify tables were created
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Created {len(tables)} tables: {', '.join(tables)}")

    # Create session for seed data
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    try:
        # Add seed data if configuration table is empty
        if session.query(Configuration).count() == 0:
            logger.info("Adding seed configuration data...")
            seed_configurations = [
                Configuration(
                    category="risk",
                    key="max_buying_power_percent",
                    value="5.0",
                    value_type="float",
                    description="Maximum percentage of buying power per trade",
                ),
                Configuration(
                    category="risk",
                    key="stop_loss_percent",
                    value="20.0",
                    value_type="float",
                    description="Stop loss percentage of max risk",
                ),
                Configuration(
                    category="risk",
                    key="min_risk_reward_ratio",
                    value="1.0",
                    value_type="float",
                    description="Minimum risk/reward ratio for trades",
                ),
                Configuration(
                    category="sentiment",
                    key="minimum_score",
                    value="60",
                    value_type="integer",
                    description="Minimum sentiment score to proceed",
                ),
                Configuration(
                    category="alerts",
                    key="email_enabled",
                    value="false",
                    value_type="boolean",
                    description="Enable email notifications",
                ),
                Configuration(
                    category="alerts",
                    key="profit_target_alert",
                    value="50.0",
                    value_type="float",
                    description="Alert when profit reaches this percentage",
                ),
                Configuration(
                    category="system",
                    key="paper_trading_mode",
                    value="true",
                    value_type="boolean",
                    description="Enable paper trading mode",
                ),
            ]

            session.add_all(seed_configurations)
            session.commit()
            logger.info(f"Added {len(seed_configurations)} configuration entries")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()

    logger.info("Database initialization completed successfully")


def verify_db_schema() -> bool:
    """
    Verify that all required tables exist in the database.

    Returns:
        bool: True if all tables exist, False otherwise
    """
    from app.config import settings

    engine = create_engine(
        settings.database_url,
        connect_args=(
            {"check_same_thread": False}
            if settings.database_url.startswith("sqlite")
            else {}
        ),
    )

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    # Required tables
    required_tables = {
        # Market data tables
        "market_data_cache",
        "spy_quotes",
        "option_contracts",
        "historical_prices",
        "api_requests_log",
        # Trading tables
        "trades",
        "sentiment_scores",
        "trade_spreads",
        "configuration",
        "daily_summaries",
    }

    missing_tables = required_tables - existing_tables

    if missing_tables:
        logger.warning(f"Missing tables: {', '.join(missing_tables)}")
        return False

    engine.dispose()
    return True


def reset_db() -> None:
    """
    Drop all tables and recreate them. USE WITH CAUTION!
    """
    from app.config import settings

    engine = create_engine(
        settings.database_url,
        connect_args=(
            {"check_same_thread": False}
            if settings.database_url.startswith("sqlite")
            else {}
        ),
    )

    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)

    logger.info("Recreating database tables...")
    Base.metadata.create_all(bind=engine)

    engine.dispose()

    # Re-initialize with seed data
    init_db()
