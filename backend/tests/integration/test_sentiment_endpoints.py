import pytest
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime

from app.models.sentiment import SentimentResult, SentimentBreakdown, TechnicalStatus, ComponentScore


class TestSentimentEndpoints:
    @pytest.mark.asyncio
    async def test_calculate_sentiment_success(self, client):
        # Mock sentiment result
        mock_result = {
            "score": 75,
            "decision": "PROCEED",
            "threshold": 60,
            "timestamp": "2025-07-26T09:45:00",
            "breakdown": {
                "vix": {"score": 20, "value": 14.5, "label": "Low volatility (bullish)"},
                "futures": {"score": 20, "value": 5680.0, "change_percent": 0.176, "label": "Positive overnight (bullish)"},
                "rsi": {"score": 10, "value": 55.2, "range": "30-70", "label": "Neutral (healthy)"},
                "ma50": {"score": 10, "value": 567.89, "position": "above", "label": "Above 50-MA (bullish)"},
                "bollinger": {"score": 10, "value": 0.65, "label": "Middle range (neutral)"},
                "news": {"score": 5, "value": 0, "label": "Neutral market sentiment"}
            },
            "technical_status": {
                "all_bullish": True,
                "details": {
                    "trend": "up",
                    "momentum": "positive",
                    "volatility": "low"
                }
            },
            "cached": False
        }
        
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock(return_value=mock_result)
            
            response = client.get("/api/v1/sentiment/calculate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["score"] == 75
            assert data["decision"] == "PROCEED"
            assert data["threshold"] == 60
            assert "breakdown" in data
            assert "technical_status" in data
    
    @pytest.mark.asyncio
    async def test_calculate_sentiment_with_force_refresh(self, client):
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock()
            
            response = client.get("/api/v1/sentiment/calculate?force_refresh=true")
            
            assert response.status_code == 200
            # Verify force_refresh was passed
            mock_calc.calculate_sentiment.assert_called_once_with(force_refresh=True)
    
    @pytest.mark.asyncio
    async def test_sentiment_skip_decision(self, client):
        mock_result = {
            "score": 45,
            "decision": "SKIP",
            "threshold": 60,
            "timestamp": "2025-07-26T09:45:00",
            "breakdown": {
                "vix": {"score": 0, "value": 25.0, "label": "High volatility (bearish)"},
                "futures": {"score": 0, "value": 5650.0, "change_percent": -0.353, "label": "Negative overnight (bearish)"},
                "rsi": {"score": 10, "value": 55.0, "range": "30-70", "label": "Neutral (healthy)"},
                "ma50": {"score": 10, "value": 567.89, "position": "above", "label": "Above 50-MA (bullish)"},
                "bollinger": {"score": 10, "value": 0.5, "label": "Middle range (neutral)"},
                "news": {"score": 15, "value": 0, "label": "Neutral market sentiment"}
            },
            "technical_status": {
                "all_bullish": False,
                "details": {
                    "trend": "up",
                    "momentum": "positive",
                    "volatility": "high"
                }
            },
            "cached": False
        }
        
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock(return_value=mock_result)
            
            response = client.get("/api/v1/sentiment/calculate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["score"] == 45
            assert data["decision"] == "SKIP"
            assert data["score"] < data["threshold"]
    
    @pytest.mark.asyncio
    async def test_sentiment_service_error(self, client):
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock(
                side_effect=Exception("Market data unavailable")
            )
            
            response = client.get("/api/v1/sentiment/calculate")
            
            assert response.status_code == 503
            data = response.json()
            assert "error" in data
            assert "SENTIMENT_ERROR" in data["error"]["code"]
    
    @pytest.mark.asyncio
    async def test_cache_headers(self, client):
        mock_result = {
            "score": 70,
            "decision": "PROCEED",
            "threshold": 60,
            "timestamp": "2025-07-26T09:45:00",
            "breakdown": {
                "vix": {"score": 20, "value": 14.5, "label": "Low volatility (bullish)"},
                "futures": {"score": 20, "value": 5680.0, "change_percent": 0.176, "label": "Positive overnight (bullish)"},
                "rsi": {"score": 10, "value": 55.0, "range": "30-70", "label": "Neutral (healthy)"},
                "ma50": {"score": 10, "value": 567.89, "position": "above", "label": "Above 50-MA (bullish)"},
                "bollinger": {"score": 10, "value": 0.5, "label": "Middle range (neutral)"},
                "news": {"score": 0, "value": 0, "label": "Neutral market sentiment"}
            },
            "technical_status": {
                "all_bullish": True,
                "details": {"trend": "up", "momentum": "positive", "volatility": "low"}
            },
            "cached": True,
            "cache_expires_at": "2025-07-26T09:50:00"
        }
        
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock(return_value=mock_result)
            
            response = client.get("/api/v1/sentiment/calculate")
            
            assert response.status_code == 200
            assert "Cache-Control" in response.headers
            assert response.headers.get("X-Cached") == "true"
    
    @pytest.mark.asyncio 
    async def test_sentiment_breakdown_structure(self, client):
        mock_result = {
            "score": 65,
            "decision": "PROCEED",
            "threshold": 60,
            "timestamp": "2025-07-26T09:45:00",
            "breakdown": {
                "vix": {"score": 10, "value": 18.0, "threshold": "16-20", "label": "Medium volatility (neutral)"},
                "futures": {"score": 10, "value": 5674.0, "change_percent": 0.071, "label": "Slightly positive (neutral)"},
                "rsi": {"score": 10, "value": 45.0, "range": "30-70", "label": "Neutral (healthy)"},
                "ma50": {"score": 10, "value": 567.89, "position": "above", "label": "Above 50-MA (bullish)"},
                "bollinger": {"score": 10, "value": 0.6, "label": "Middle range (neutral)"},
                "news": {"score": 15, "value": 0, "label": "Neutral market sentiment"}
            },
            "technical_status": {
                "all_bullish": True,
                "details": {
                    "trend": "up",
                    "momentum": "positive", 
                    "volatility": "medium"
                }
            },
            "cached": False
        }
        
        with patch("app.api.v1.endpoints.sentiment.sentiment_calculator") as mock_calc:
            mock_calc.calculate_sentiment = AsyncMock(return_value=mock_result)
            
            response = client.get("/api/v1/sentiment/calculate")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify breakdown structure
            breakdown = data["breakdown"]
            assert "vix" in breakdown
            assert "futures" in breakdown
            assert "rsi" in breakdown
            assert "ma50" in breakdown
            assert "bollinger" in breakdown
            assert "news" in breakdown
            
            # Verify each component has required fields
            for component in breakdown.values():
                assert "score" in component
                assert "value" in component
                assert "label" in component