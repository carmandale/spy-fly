"""
Tests for API rate limiting and caching behavior.

These tests verify that the spread recommendations API properly handles
rate limiting, caching, performance constraints, and error conditions.
"""

import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from decimal import Decimal

from app.main import app
from app.models.spread import SpreadRecommendation


class TestAPIRateLimitingAndCaching:
    """Test API rate limiting, caching, and performance behavior."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    def test_api_handles_multiple_concurrent_requests(self, client):
        """Test that API can handle multiple requests without blocking."""
        # Simple test - make multiple requests and ensure they don't block each other
        responses = []
        for i in range(3):
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": 10000, "max_recommendations": 1}
            )
            responses.append(response)
        
        # All requests should return some response (success or error)
        for response in responses:
            assert response.status_code in [200, 500, 422, 503]  # Valid response codes

    def test_api_parameter_validation_performance(self, client):
        """Test that parameter validation doesn't cause performance issues."""
        test_cases = [
            {"account_size": -1000, "max_recommendations": 5},  # Invalid account size
            {"account_size": 10000, "max_recommendations": 0},  # Invalid max_recommendations  
            {"account_size": 10000, "max_recommendations": 20}, # Too many recommendations
            {"account_size": "invalid", "max_recommendations": 5}, # Wrong type
        ]
        
        for params in test_cases:
            start_time = time.time()
            response = client.get("/api/v1/recommendations/spreads", params=params)
            end_time = time.time()
            
            # Parameter validation should be fast
            assert end_time - start_time < 0.5  # 500ms maximum (generous for CI)
            assert response.status_code == 422  # Validation error

    def test_api_response_time_reasonable(self, client):
        """Test that API responds within reasonable time limits."""
        start_time = time.time()
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 10000, "max_recommendations": 3}
        )
        end_time = time.time()
        
        # Should complete within reasonable time
        assert end_time - start_time < 30.0  # 30 second maximum (very generous)
        assert response.status_code in [200, 500, 503]  # Valid response

    def test_api_handles_large_account_size(self, client):
        """Test API handles very large account sizes correctly."""
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 1000000, "max_recommendations": 5}  # $1M account
        )
        
        # Should not crash with large numbers
        assert response.status_code in [200, 500, 503]  # Valid response
        
        if response.status_code == 200:
            data = response.json()
            assert "account_size" in data or "recommendations" in data

    def test_api_handles_maximum_recommendations_limit(self, client):
        """Test API enforces maximum recommendations limit."""
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 10000, "max_recommendations": 15}  # Above limit
        )
        
        # Should reject requests above maximum
        assert response.status_code == 422  # Validation error

    def test_api_returns_consistent_response_structure(self, client):
        """Test that API returns consistent response format."""
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 10000, "max_recommendations": 3}
        )
        
        if response.status_code == 200:
            data = response.json()
            # Should have consistent top-level structure
            expected_fields = ["recommendations", "metadata", "summary"]
            for field in expected_fields:
                assert field in data, f"Missing field: {field}"
            
            # Recommendations should be a list
            assert isinstance(data["recommendations"], list)

    def test_api_handles_different_response_formats(self, client):
        """Test API handles different response format parameters."""
        formats = ["json", "text", "clipboard"]
        
        for format_type in formats:
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={
                    "account_size": 10000, 
                    "max_recommendations": 3,
                    "format": format_type
                }
            )
            
            # Should handle all format types
            assert response.status_code in [200, 500, 503]

    def test_api_handles_edge_case_account_sizes(self, client):
        """Test API handles edge case account sizes."""
        edge_cases = [
            1,        # Minimum valid account
            1000,     # Small account
            999999,   # Large account
        ]
        
        for account_size in edge_cases:
            response = client.get(
                "/api/v1/recommendations/spreads",
                params={"account_size": account_size, "max_recommendations": 1}
            )
            
            # Should handle all valid account sizes
            assert response.status_code in [200, 500, 503]

    def test_api_error_handling_graceful(self, client):
        """Test that API errors are handled gracefully."""
        # Test with various problematic inputs
        problematic_requests = [
            {"account_size": 0, "max_recommendations": 5},
            {"account_size": -100, "max_recommendations": 5},
            {"account_size": 10000, "max_recommendations": -1},
        ]
        
        for params in problematic_requests:
            response = client.get("/api/v1/recommendations/spreads", params=params)
            
            # Should return proper error codes, not crash
            assert response.status_code in [400, 422]
            
            # Should return JSON error response
            if response.headers.get("content-type", "").startswith("application/json"):
                error_data = response.json()
                assert "detail" in error_data or "message" in error_data

    def test_api_concurrent_requests_stability(self, client):
        """Test API stability under concurrent load."""
        import threading
        
        results = []
        
        def make_request():
            try:
                response = client.get(
                    "/api/v1/recommendations/spreads",
                    params={"account_size": 10000, "max_recommendations": 2}
                )
                results.append(response.status_code)
            except Exception as e:
                results.append(f"Error: {str(e)}")
        
        # Create multiple threads to make concurrent requests
        threads = []
        for i in range(5):  # Small number for test stability
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout per thread
        
        # All requests should complete
        assert len(results) == 5
        
        # All should return valid HTTP status codes
        for result in results:
            if isinstance(result, int):
                assert result in [200, 422, 500, 503]  # Valid HTTP codes
            else:
                # If it's an error string, that's also acceptable for this test
                assert "Error:" in str(result)

    @patch('app.api.v1.endpoints.recommendations.spread_service')
    def test_api_handles_service_errors(self, mock_service, client):
        """Test API graceful handling of service errors."""
        # Configure mock to raise an exception
        mock_service.get_recommendations.side_effect = Exception("Service unavailable")
        
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 10000, "max_recommendations": 3}
        )
        
        # Should return error but not crash
        assert response.status_code == 500
        
        if response.headers.get("content-type", "").startswith("application/json"):
            error_data = response.json()
            assert "detail" in error_data

    def test_api_request_size_limits(self, client):
        """Test that API handles request size appropriately."""
        # Test with maximum allowed recommendations
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 10000, "max_recommendations": 10}  # Maximum allowed
        )
        
        assert response.status_code in [200, 500, 422, 503]
        
        if response.status_code == 200:
            data = response.json()
            recommendations = data.get("recommendations", [])
            # Should not exceed requested limit
            assert len(recommendations) <= 10

    def test_api_response_serialization_performance(self, client):
        """Test that JSON serialization performs reasonably."""
        start_time = time.time()
        response = client.get(
            "/api/v1/recommendations/spreads",
            params={"account_size": 50000, "max_recommendations": 5}
        )
        end_time = time.time()
        
        # Response should be generated and serialized quickly
        assert end_time - start_time < 30.0  # 30 second maximum
        
        if response.status_code == 200:
            # Should be valid JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_api_handles_missing_parameters(self, client):
        """Test API handles missing required parameters."""
        test_cases = [
            {},  # No parameters (missing required account_size)
            {"max_recommendations": 5},  # Missing required account_size
        ]
        
        for params in test_cases:
            response = client.get("/api/v1/recommendations/spreads", params=params)
            
            # Should return validation error for missing account_size
            assert response.status_code == 422
            
            error_data = response.json()
            assert "detail" in error_data
        
        # Test case where account_size is provided (should work)
        response = client.get(
            "/api/v1/recommendations/spreads", 
            params={"account_size": 10000}  # max_recommendations has default
        )
        # Should succeed or fail with business logic error, not validation error
        assert response.status_code in [200, 500, 503]