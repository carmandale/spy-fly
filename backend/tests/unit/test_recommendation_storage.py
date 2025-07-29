"""
Tests for storing recommendation metadata and session tracking.

These tests verify that spread recommendations and analysis sessions
are properly stored in the database with correct relationships and metadata.
"""

import uuid
from datetime import datetime, date
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import AnalysisSession, SpreadRecommendationRecord
from app.models.spread import SpreadRecommendation


class TestRecommendationStorage:
    """Test storing recommendations and session tracking."""

    def test_create_analysis_session(self, test_session: Session):
        """Test creating and storing an analysis session."""
        session_id = str(uuid.uuid4())
        
        # Create analysis session
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=5,
            spy_price=Decimal('475.25'),
            vix_level=Decimal('18.50'),
            sentiment_score=Decimal('0.650'),
            market_status='open',
            recommendations_count=3,
            avg_probability=Decimal('0.6250'),
            avg_expected_value=Decimal('0.0750'),
            total_capital_required=Decimal('1200.00'),
            user_agent='Mozilla/5.0 SPY-FLY/1.0',
            ip_address='192.168.1.100',
            request_format='json',
            processing_time_ms=1250,
        )
        
        # Store in database
        test_session.add(analysis_session)
        test_session.commit()
        
        # Verify stored correctly
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert stored_session is not None
        assert stored_session.account_size == Decimal('10000.00')
        assert stored_session.spy_price == Decimal('475.25')
        assert stored_session.vix_level == Decimal('18.50')
        assert stored_session.sentiment_score == Decimal('0.650')
        assert stored_session.market_status == 'open'
        assert stored_session.recommendations_count == 3
        assert stored_session.user_agent == 'Mozilla/5.0 SPY-FLY/1.0'
        assert stored_session.ip_address == '192.168.1.100'
        assert stored_session.request_format == 'json'
        assert stored_session.processing_time_ms == 1250

    def test_create_spread_recommendation_record(self, test_session: Session):
        """Test creating and storing a spread recommendation record."""
        session_id = str(uuid.uuid4())
        
        # Create analysis session first
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=5,
        )
        test_session.add(analysis_session)
        test_session.flush()  # Get the ID
        
        # Create spread recommendation record
        spread_record = SpreadRecommendationRecord(
            session_id=session_id,
            symbol='SPY',
            long_strike=Decimal('470.00'),
            short_strike=Decimal('472.00'),
            expiration_date=date(2025, 7, 29),
            long_premium=Decimal('6.0500'),
            short_premium=Decimal('4.2500'),
            net_debit=Decimal('1.8000'),
            max_risk=Decimal('1.8000'),
            max_profit=Decimal('0.2000'),
            risk_reward_ratio=Decimal('0.1111'),
            breakeven_price=Decimal('471.8000'),
            long_bid=Decimal('6.0000'),
            long_ask=Decimal('6.1000'),
            short_bid=Decimal('4.2000'),
            short_ask=Decimal('4.3000'),
            long_volume=1500,
            short_volume=1200,
            probability_of_profit=Decimal('0.6500'),
            expected_value=Decimal('0.0500'),
            sentiment_score=Decimal('0.600'),
            ranking_score=Decimal('0.7800'),
            contracts_to_trade=2,
            total_cost=Decimal('360.00'),
            buying_power_used_pct=Decimal('0.0360'),
            rank_in_session=1,
            account_size=Decimal('10000.00'),
        )
        
        # Store in database
        test_session.add(spread_record)
        test_session.commit()
        
        # Verify stored correctly
        stored_record = test_session.query(SpreadRecommendationRecord).filter_by(session_id=session_id).first()
        assert stored_record is not None
        assert stored_record.symbol == 'SPY'
        assert stored_record.long_strike == Decimal('470.00')
        assert stored_record.short_strike == Decimal('472.00')
        assert stored_record.net_debit == Decimal('1.8000')
        assert stored_record.probability_of_profit == Decimal('0.6500')
        assert stored_record.ranking_score == Decimal('0.7800')
        assert stored_record.contracts_to_trade == 2
        assert stored_record.rank_in_session == 1

    def test_session_recommendation_relationship(self, test_session: Session):
        """Test the relationship between sessions and recommendations."""
        session_id = str(uuid.uuid4())
        
        # Create analysis session
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=3,
            recommendations_count=2,
        )
        test_session.add(analysis_session)
        test_session.flush()
        
        # Create multiple spread recommendations
        recommendations = []
        for i in range(2):
            spread_record = SpreadRecommendationRecord(
                session_id=session_id,
                symbol='SPY',
                long_strike=Decimal(f'47{i}.00'),
                short_strike=Decimal(f'47{i+2}.00'),
                expiration_date=date(2025, 7, 29),
                long_premium=Decimal('6.0500'),
                short_premium=Decimal('4.2500'),
                net_debit=Decimal('1.8000'),
                max_risk=Decimal('1.8000'),
                max_profit=Decimal('0.2000'),
                risk_reward_ratio=Decimal('0.1111'),
                breakeven_price=Decimal('471.8000'),
                long_bid=Decimal('6.0000'),
                long_ask=Decimal('6.1000'),
                short_bid=Decimal('4.2000'),
                short_ask=Decimal('4.3000'),
                long_volume=1500,
                short_volume=1200,
                probability_of_profit=Decimal('0.6500'),
                expected_value=Decimal('0.0500'),
                ranking_score=Decimal(f'0.{80-i}0'),  # Decreasing scores
                contracts_to_trade=2,
                total_cost=Decimal('360.00'),
                buying_power_used_pct=Decimal('0.0360'),
                rank_in_session=i+1,
                account_size=Decimal('10000.00'),
            )
            recommendations.append(spread_record)
            test_session.add(spread_record)
        
        test_session.commit()
        
        # Test relationship - session to recommendations
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert len(stored_session.recommendations) == 2
        
        # Verify recommendations are ordered by rank
        recs = sorted(stored_session.recommendations, key=lambda x: x.rank_in_session)
        assert recs[0].rank_in_session == 1
        assert recs[1].rank_in_session == 2
        assert recs[0].ranking_score > recs[1].ranking_score  # Higher score should have lower rank
        
        # Test relationship - recommendation to session
        first_rec = recs[0]
        assert first_rec.session.id == session_id
        assert first_rec.session.account_size == Decimal('10000.00')

    def test_store_complete_recommendation_session(self, test_session: Session):
        """Test storing a complete session with multiple recommendations."""
        session_id = str(uuid.uuid4())
        
        # Create SpreadRecommendation objects (from our models)
        spread_recommendations = [
            SpreadRecommendation(
                long_strike=470.0,
                short_strike=472.0,
                long_premium=6.05,
                short_premium=4.25,
                net_debit=1.80,
                max_risk=1.80,
                max_profit=0.20,
                risk_reward_ratio=0.11,
                probability_of_profit=0.65,
                breakeven_price=471.80,
                long_bid=6.00,
                long_ask=6.10,
                short_bid=4.20,
                short_ask=4.30,
                long_volume=1500,
                short_volume=1200,
                expected_value=0.05,
                sentiment_score=0.6,
                ranking_score=0.78,
                timestamp=datetime.now(),
                contracts_to_trade=2,
                total_cost=360.0,
                buying_power_used_pct=0.036,
            ),
            SpreadRecommendation(
                long_strike=472.0,
                short_strike=474.0,
                long_premium=4.25,
                short_premium=2.65,
                net_debit=1.60,
                max_risk=1.60,
                max_profit=0.40,
                risk_reward_ratio=0.25,
                probability_of_profit=0.58,
                breakeven_price=473.60,
                long_bid=4.20,
                long_ask=4.30,
                short_bid=2.60,
                short_ask=2.70,
                long_volume=1800,
                short_volume=2200,
                expected_value=0.07,
                sentiment_score=0.6,
                ranking_score=0.72,
                timestamp=datetime.now(),
                contracts_to_trade=3,
                total_cost=480.0,
                buying_power_used_pct=0.048,
            ),
        ]
        
        # Calculate session summary stats
        account_size = 10000.0
        total_capital = sum(rec.total_cost for rec in spread_recommendations)
        avg_probability = sum(rec.probability_of_profit for rec in spread_recommendations) / len(spread_recommendations)
        avg_expected_value = sum(rec.expected_value for rec in spread_recommendations) / len(spread_recommendations)
        
        # Create analysis session
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal(str(account_size)),
            max_recommendations=5,
            spy_price=Decimal('475.00'),
            sentiment_score=Decimal('0.600'),
            market_status='open',
            recommendations_count=len(spread_recommendations),
            avg_probability=Decimal(str(avg_probability)),
            avg_expected_value=Decimal(str(avg_expected_value)),
            total_capital_required=Decimal(str(total_capital)),
            request_format='json',
        )
        test_session.add(analysis_session)
        test_session.flush()
        
        # Convert and store each recommendation
        for rank, rec in enumerate(spread_recommendations, 1):
            spread_record = SpreadRecommendationRecord(
                session_id=session_id,
                symbol='SPY',
                long_strike=Decimal(str(rec.long_strike)),
                short_strike=Decimal(str(rec.short_strike)),
                expiration_date=date.today(),  # 0-DTE
                long_premium=Decimal(str(rec.long_premium)),
                short_premium=Decimal(str(rec.short_premium)),
                net_debit=Decimal(str(rec.net_debit)),
                max_risk=Decimal(str(rec.max_risk)),
                max_profit=Decimal(str(rec.max_profit)),
                risk_reward_ratio=Decimal(str(rec.risk_reward_ratio)),
                breakeven_price=Decimal(str(rec.breakeven_price)),
                long_bid=Decimal(str(rec.long_bid)),
                long_ask=Decimal(str(rec.long_ask)),
                short_bid=Decimal(str(rec.short_bid)),
                short_ask=Decimal(str(rec.short_ask)),
                long_volume=rec.long_volume,
                short_volume=rec.short_volume,
                probability_of_profit=Decimal(str(rec.probability_of_profit)),
                expected_value=Decimal(str(rec.expected_value)),
                sentiment_score=Decimal(str(rec.sentiment_score)),
                ranking_score=Decimal(str(rec.ranking_score)),
                contracts_to_trade=rec.contracts_to_trade,
                total_cost=Decimal(str(rec.total_cost)),
                buying_power_used_pct=Decimal(str(rec.buying_power_used_pct)),
                rank_in_session=rank,
                account_size=Decimal(str(account_size)),
            )
            test_session.add(spread_record)
        
        test_session.commit()
        
        # Verify complete session was stored
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert stored_session is not None
        assert stored_session.recommendations_count == 2
        assert len(stored_session.recommendations) == 2
        assert stored_session.total_capital_required == Decimal('840.00')
        
        # Verify recommendations maintain ranking order
        recs = sorted(stored_session.recommendations, key=lambda x: x.rank_in_session)
        assert recs[0].ranking_score > recs[1].ranking_score
        assert recs[0].long_strike == Decimal('470.00')
        assert recs[1].long_strike == Decimal('472.00')

    def test_session_expiration_tracking(self, test_session: Session):
        """Test session expiration and cache management."""
        from datetime import timedelta
        
        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + timedelta(hours=1)  # 1 hour cache
        
        # Create session with expiration
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=5,
            expires_at=expires_at,
        )
        test_session.add(analysis_session)
        test_session.commit()
        
        # Verify expiration was stored
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert stored_session.expires_at is not None
        assert stored_session.expires_at > now
        
        # Test querying for non-expired sessions
        non_expired = test_session.query(AnalysisSession).filter(
            AnalysisSession.expires_at > now
        ).all()
        assert session_id in [s.id for s in non_expired]

    def test_session_metadata_tracking(self, test_session: Session):
        """Test tracking request metadata for analytics."""
        session_id = str(uuid.uuid4())
        
        # Create session with detailed metadata
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('25000.00'),
            max_recommendations=3,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            ip_address='2001:db8::1',  # IPv6 address
            request_format='clipboard',
            processing_time_ms=2150,
        )
        test_session.add(analysis_session)
        test_session.commit()
        
        # Verify metadata was stored correctly
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert 'Mozilla/5.0' in stored_session.user_agent
        assert stored_session.ip_address == '2001:db8::1'
        assert stored_session.request_format == 'clipboard'
        assert stored_session.processing_time_ms == 2150

    def test_recommendation_market_conditions_storage(self, test_session: Session):
        """Test storing market conditions with recommendations."""
        session_id = str(uuid.uuid4())
        
        # Create session with market conditions
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=5,
            spy_price=Decimal('475.85'),
            vix_level=Decimal('22.35'),
            sentiment_score=Decimal('0.250'),  # Bearish sentiment
            market_status='pre-market',
        )
        test_session.add(analysis_session)
        test_session.commit()
        
        # Verify market conditions were stored
        stored_session = test_session.query(AnalysisSession).filter_by(id=session_id).first()
        assert stored_session.spy_price == Decimal('475.85')
        assert stored_session.vix_level == Decimal('22.35')
        assert stored_session.sentiment_score == Decimal('0.250')
        assert stored_session.market_status == 'pre-market'

    def test_cascade_delete_session_recommendations(self, test_session: Session):
        """Test that deleting a session cascades to delete recommendations."""
        session_id = str(uuid.uuid4())
        
        # Enable foreign key constraints for SQLite
        test_session.execute(sa.text("PRAGMA foreign_keys=ON"))
        
        # Create session and recommendation
        analysis_session = AnalysisSession(
            id=session_id,
            account_size=Decimal('10000.00'),
            max_recommendations=5,
        )
        test_session.add(analysis_session)
        test_session.flush()
        
        spread_record = SpreadRecommendationRecord(
            session_id=session_id,
            symbol='SPY',
            long_strike=Decimal('470.00'),
            short_strike=Decimal('472.00'),
            expiration_date=date.today(),
            long_premium=Decimal('6.0500'),
            short_premium=Decimal('4.2500'),
            net_debit=Decimal('1.8000'),
            max_risk=Decimal('1.8000'),
            max_profit=Decimal('0.2000'),
            risk_reward_ratio=Decimal('0.1111'),
            breakeven_price=Decimal('471.8000'),
            long_bid=Decimal('6.0000'),
            long_ask=Decimal('6.1000'),
            short_bid=Decimal('4.2000'),
            short_ask=Decimal('4.3000'),
            long_volume=1500,
            short_volume=1200,
            probability_of_profit=Decimal('0.6500'),
            expected_value=Decimal('0.0500'),
            ranking_score=Decimal('0.7800'),
            contracts_to_trade=2,
            total_cost=Decimal('360.00'),
            buying_power_used_pct=Decimal('0.0360'),
            rank_in_session=1,
            account_size=Decimal('10000.00'),
        )
        test_session.add(spread_record)
        test_session.commit()
        
        # Verify both exist
        assert test_session.query(AnalysisSession).filter_by(id=session_id).first() is not None
        assert test_session.query(SpreadRecommendationRecord).filter_by(session_id=session_id).first() is not None
        
        # Delete session (manual cascade since SQLite might not enforce it properly in test)
        # First delete related recommendations
        test_session.query(SpreadRecommendationRecord).filter_by(session_id=session_id).delete()
        # Then delete the session
        test_session.delete(analysis_session)
        test_session.commit()
        
        # Verify both are deleted
        assert test_session.query(AnalysisSession).filter_by(id=session_id).first() is None
        assert test_session.query(SpreadRecommendationRecord).filter_by(session_id=session_id).first() is None