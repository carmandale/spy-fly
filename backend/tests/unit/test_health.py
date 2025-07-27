from datetime import datetime
from unittest.mock import patch

import pytest


def test_health_endpoint_status_code(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_response_structure(client):
    response = client.get("/api/v1/health")
    data = response.json()
    
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "environment" in data


def test_health_endpoint_response_values(client):
    response = client.get("/api/v1/health")
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"


def test_health_endpoint_timestamp_format(client):
    response = client.get("/api/v1/health")
    data = response.json()
    
    # Verify timestamp is valid ISO format
    try:
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
    except ValueError:
        pytest.fail("Timestamp is not in valid ISO format")


def test_health_endpoint_with_mocked_time(client):
    mock_time = "2025-07-26T12:00:00Z"
    with patch("app.api.v1.endpoints.health.datetime") as mock_datetime:
        mock_datetime.utcnow.return_value.isoformat.return_value = "2025-07-26T12:00:00"
        
        response = client.get("/api/v1/health")
        data = response.json()
        
        assert data["timestamp"] == mock_time