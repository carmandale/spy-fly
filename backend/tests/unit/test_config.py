import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_from_env():
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "sqlite:///./custom.db",
            "ENVIRONMENT": "testing",
            "DEBUG": "false",
            "CORS_ORIGINS": '["http://localhost:5000","http://localhost:3001"]',
        },
    ):
        settings = Settings()
        assert settings.database_url == "sqlite:///./custom.db"
        assert settings.environment == "testing"
        assert settings.debug is False
        assert settings.cors_origins == [
            "http://localhost:5000",
            "http://localhost:3001",
        ]


def test_settings_defaults():
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.database_url == "sqlite:///./spy_fly.db"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.cors_origins == ["http://localhost:3003"]


def test_settings_cors_origins_string():
    with patch.dict(os.environ, {"CORS_ORIGINS": '["http://localhost:3000"]'}):
        settings = Settings()
        assert settings.cors_origins == ["http://localhost:3000"]


def test_settings_project_name():
    settings = Settings()
    assert settings.project_name == "SPY-FLY"
    assert settings.version == "0.1.0"


# New tests for Polygon.io configuration validation
def test_polygon_api_key_validation():
    """Test that polygon_api_key is properly configured"""
    with patch.dict(os.environ, {"POLYGON_API_KEY": "test_api_key_12345"}):
        settings = Settings()
        assert settings.polygon_api_key == "test_api_key_12345"


def test_polygon_api_key_empty_default():
    """Test that polygon_api_key defaults to empty string"""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.polygon_api_key == ""


def test_polygon_use_sandbox_validation():
    """Test polygon_use_sandbox boolean validation"""
    with patch.dict(os.environ, {"POLYGON_USE_SANDBOX": "true"}):
        settings = Settings()
        assert settings.polygon_use_sandbox is True

    with patch.dict(os.environ, {"POLYGON_USE_SANDBOX": "false"}):
        settings = Settings()
        assert settings.polygon_use_sandbox is False


def test_polygon_rate_limit_validation():
    """Test polygon_rate_limit validation"""
    with patch.dict(os.environ, {"POLYGON_RATE_LIMIT": "10"}):
        settings = Settings()
        assert settings.polygon_rate_limit == 10

    # Test negative value fails
    with patch.dict(os.environ, {"POLYGON_RATE_LIMIT": "-1"}):
        with pytest.raises(ValidationError):
            Settings()


def test_polygon_cache_ttl_validation():
    """Test polygon cache TTL values"""
    with patch.dict(
        os.environ,
        {
            "POLYGON_CACHE_TTL_QUOTE": "30",
            "POLYGON_CACHE_TTL_OPTIONS": "600",
            "POLYGON_CACHE_TTL_HISTORICAL": "7200",
        },
    ):
        settings = Settings()
        assert settings.polygon_cache_ttl_quote == 30
        assert settings.polygon_cache_ttl_options == 600
        assert settings.polygon_cache_ttl_historical == 7200

    # Test negative TTL fails
    with patch.dict(os.environ, {"POLYGON_CACHE_TTL_QUOTE": "-1"}):
        with pytest.raises(ValidationError):
            Settings()


def test_sentiment_thresholds_validation():
    """Test sentiment threshold validation"""
    with patch.dict(
        os.environ,
        {
            "VIX_LOW_THRESHOLD": "15.5",
            "VIX_HIGH_THRESHOLD": "25.0",
            "FUTURES_BULLISH_THRESHOLD": "0.002",
            "SENTIMENT_MINIMUM_SCORE": "65",
        },
    ):
        settings = Settings()
        assert settings.vix_low_threshold == 15.5
        assert settings.vix_high_threshold == 25.0
        assert settings.futures_bullish_threshold == 0.002
        assert settings.sentiment_minimum_score == 65


def test_environment_validation():
    """Test environment value validation"""
    valid_environments = ["development", "testing", "production"]

    for env in valid_environments:
        with patch.dict(os.environ, {"ENVIRONMENT": env}):
            settings = Settings()
            assert settings.environment == env


def test_api_port_validation():
    """Test API port validation"""
    with patch.dict(os.environ, {"API_PORT": "8003"}):
        settings = Settings()
        assert settings.api_port == 8003

    # Test invalid port fails
    with patch.dict(os.environ, {"API_PORT": "70000"}):
        with pytest.raises(ValidationError):
            Settings()


def test_cors_origins_json_validation():
    """Test CORS origins JSON parsing edge cases"""
    # Test valid JSON array
    with patch.dict(
        os.environ,
        {"CORS_ORIGINS": '["http://localhost:3000", "http://localhost:3003"]'},
    ):
        settings = Settings()
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:3003",
        ]


def test_all_default_values():
    """Test that all configuration has proper defaults"""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()

        # Core settings
        assert settings.project_name == "SPY-FLY"
        assert settings.version == "0.1.0"
        assert settings.database_url == "sqlite:///./spy_fly.db"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.cors_origins == ["http://localhost:3003"]
        assert settings.api_port == 8003

        # Polygon settings
        assert settings.polygon_api_key == ""
        assert settings.polygon_use_sandbox is False
        assert settings.polygon_rate_limit == 5
        assert settings.polygon_cache_ttl_quote == 60
        assert settings.polygon_cache_ttl_options == 300
        assert settings.polygon_cache_ttl_historical == 3600

        # Sentiment settings
        assert settings.sentiment_cache_ttl == 300
        assert settings.vix_low_threshold == 16.0
        assert settings.vix_high_threshold == 20.0
        assert settings.futures_bullish_threshold == 0.001
        assert settings.rsi_oversold == 30
        assert settings.rsi_overbought == 70
        assert settings.bollinger_inner_range == 0.4
        assert settings.sentiment_minimum_score == 60


def test_startup_configuration_validation_success():
    """Test successful startup configuration validation"""
    with patch.dict(
        os.environ,
        {
            "POLYGON_API_KEY": "test_api_key_12345",
            "DATABASE_URL": "sqlite:///./test.db",
            "API_PORT": "8003",
        },
    ):
        settings = Settings()
        is_valid, errors = settings.validate_startup_configuration()
        assert is_valid is True
        assert len(errors) == 0


def test_startup_configuration_validation_failures():
    """Test startup configuration validation with failures"""
    with patch.dict(
        os.environ,
        {
            "POLYGON_API_KEY": "",  # Empty API key
            "DATABASE_URL": "",  # Empty database URL
            "API_PORT": "70000",  # Invalid port
            "VIX_LOW_THRESHOLD": "20.0",
            "VIX_HIGH_THRESHOLD": "15.0",  # Invalid: high < low
            "RSI_OVERSOLD": "70",
            "RSI_OVERBOUGHT": "30",  # Invalid: overbought < oversold
        },
        clear=True,
    ):
        with pytest.raises(ValidationError):
            Settings()


def test_startup_configuration_missing_api_key():
    """Test startup validation with missing API key"""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        is_valid, errors = settings.validate_startup_configuration()
        assert is_valid is False
        assert any("POLYGON_API_KEY is not configured" in error for error in errors)


def test_startup_configuration_short_api_key():
    """Test startup validation with short API key"""
    with patch.dict(os.environ, {"POLYGON_API_KEY": "short"}):
        settings = Settings()
        is_valid, errors = settings.validate_startup_configuration()
        assert is_valid is False
        assert any("appears to be invalid (too short)" in error for error in errors)


def test_get_masked_api_key():
    """Test API key masking for security"""
    # Test with no API key
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.get_masked_api_key() == "NOT_SET"

    # Test with short API key
    with patch.dict(os.environ, {"POLYGON_API_KEY": "short"}):
        settings = Settings()
        assert settings.get_masked_api_key() == "***"

    # Test with normal API key
    with patch.dict(os.environ, {"POLYGON_API_KEY": "test_api_key_12345"}):
        settings = Settings()
        masked = settings.get_masked_api_key()
        assert masked == "test...2345"
        assert "api_key" not in masked


def test_validate_api_key_for_production():
    """Test production API key validation"""
    # Test development environment (should pass without API key)
    with patch.dict(os.environ, {"ENVIRONMENT": "development", "POLYGON_API_KEY": ""}):
        settings = Settings()
        assert settings.validate_api_key_for_production() is True

    # Test production environment without API key (should fail)
    with patch.dict(os.environ, {"ENVIRONMENT": "production", "POLYGON_API_KEY": ""}):
        settings = Settings()
        assert settings.validate_api_key_for_production() is False

    # Test production environment with API key (should pass)
    with patch.dict(
        os.environ,
        {"ENVIRONMENT": "production", "POLYGON_API_KEY": "test_api_key_12345"},
    ):
        settings = Settings()
        assert settings.validate_api_key_for_production() is True
