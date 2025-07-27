import os
import pytest
from unittest.mock import patch

from app.config import Settings


def test_settings_from_env():
    with patch.dict(os.environ, {
        "DATABASE_URL": "sqlite:///./custom.db",
        "ENVIRONMENT": "testing",
        "DEBUG": "false",
        "CORS_ORIGINS": '["http://localhost:5000","http://localhost:3001"]'
    }):
        settings = Settings()
        assert settings.database_url == "sqlite:///./custom.db"
        assert settings.environment == "testing"
        assert settings.debug is False
        assert settings.cors_origins == ["http://localhost:5000", "http://localhost:3001"]


def test_settings_defaults():
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        assert settings.database_url == "sqlite:///./spy_fly.db"
        assert settings.environment == "development"
        assert settings.debug is True
        assert settings.cors_origins == ["http://localhost:3000"]


def test_settings_cors_origins_string():
    with patch.dict(os.environ, {
        "CORS_ORIGINS": "http://localhost:3000"
    }):
        settings = Settings()
        assert settings.cors_origins == ["http://localhost:3000"]


def test_settings_project_name():
    settings = Settings()
    assert settings.project_name == "SPY-FLY"
    assert settings.version == "0.1.0"