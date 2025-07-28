"""
Spread Selection Service for SPY 0-DTE Bull-Call-Spread strategies.

This service coordinates the spread selection algorithm, integrating Black-Scholes
calculations, risk management, and market data to generate trade recommendations.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from app.models.spread import SpreadRecommendation
from app.services.black_scholes_calculator import BlackScholesCalculator
from app.services.market_service import MarketDataService
from app.services.options_chain_processor import OptionsChainProcessor
from app.services.risk_validator import RiskValidator
from app.services.sentiment_calculator import SentimentCalculator
from app.services.spread_generator import SpreadGenerator


@dataclass
class SpreadConfiguration:
    """Configuration for spread selection parameters."""

    # Risk management constraints
    max_buying_power_pct: float = 0.05  # 5% maximum buying power per trade
    min_risk_reward_ratio: float = 1.0  # Minimum 1:1 risk/reward

    # Spread criteria
    min_probability_of_profit: float = 0.30  # Minimum 30% probability
    max_bid_ask_spread_pct: float = 0.05  # Maximum 5% bid-ask spread
    min_volume: int = 10  # Minimum volume per leg

    # Time constraints
    min_time_to_expiry_hours: float = 0.5  # Minimum 0.5 hours to expiry
    max_time_to_expiry_hours: float = 8.0  # Maximum 8 hours to expiry

    # Ranking weights
    probability_weight: float = 0.4  # Weight for probability in ranking
    risk_reward_weight: float = 0.3  # Weight for risk/reward in ranking
    sentiment_weight: float = 0.3  # Weight for sentiment in ranking


class SpreadSelectionService:
    """
    Core service for SPY 0-DTE bull-call-spread selection and analysis.

    This service integrates multiple components to provide comprehensive
    spread analysis and recommendations with risk management constraints.
    """

    def __init__(
        self,
        black_scholes_calculator: BlackScholesCalculator,
        market_service: MarketDataService,
        sentiment_calculator: SentimentCalculator,
        config: SpreadConfiguration | None = None,
        options_processor: OptionsChainProcessor | None = None,
        spread_generator: SpreadGenerator | None = None,
        risk_validator: RiskValidator | None = None,
    ):
        """
        Initialize the spread selection service with dependencies.

        Args:
                black_scholes_calculator: Black-Scholes calculation service
                market_service: Market data service for prices and option chains
                sentiment_calculator: Sentiment analysis service
                config: Configuration parameters (uses defaults if None)
                options_processor: Options chain processor (creates default if None)
                spread_generator: Spread generator (creates default if None)
                risk_validator: Risk validator (creates default if None)
        """
        self.black_scholes = black_scholes_calculator
        self.market_service = market_service
        self.sentiment_calculator = sentiment_calculator
        self.config = config or SpreadConfiguration()

        # Initialize enhanced processors
        self.options_processor = options_processor or OptionsChainProcessor()
        self.spread_generator = spread_generator or SpreadGenerator()
        self.risk_validator = risk_validator or RiskValidator(
            max_buying_power_pct=self.config.max_buying_power_pct,
            min_risk_reward_ratio=self.config.min_risk_reward_ratio,
        )

        # Internal state
        self._current_sentiment_score: float | None = None
        self._current_vix: float | None = None
        self._current_spy_price: float | None = None

    async def get_recommendations(
        self, account_size: float, max_recommendations: int = 5
    ) -> list[SpreadRecommendation]:
        """
        Generate spread recommendations for current market conditions.

        Args:
                account_size: Total account size for position sizing
                max_recommendations: Maximum number of recommendations to return

        Returns:
                List of spread recommendations sorted by ranking score

        Raises:
                ValueError: If account size is invalid or market data unavailable
        """
        if account_size <= 0:
            raise ValueError(f"Account size must be positive, got {account_size}")

        # Step 1: Gather current market data
        await self._update_market_context()

        # Step 2: Validate market conditions for trading
        if not self._is_market_suitable_for_trading():
            return []

        # Step 3: Get option chain data
        option_chain_response = await self._get_current_option_chain()

        # Step 4: Process options with enhanced processor
        options_df = self.options_processor.prepare_for_spread_generation(
            option_chain_response,
            spot_price=self._current_spy_price,
            config={
                "filter_zero_dte": True,
                "validate_data": True,
                "min_volume": self.config.min_volume,
                "max_bid_ask_spread_pct": self.config.max_bid_ask_spread_pct,
                "min_otm_points": -5,  # Allow slightly ITM
                "max_otm_points": 20,  # Up to 20 points OTM
            },
        )

        if options_df.empty:
            return []  # No valid options to process

        # Step 5: Generate spreads with enhanced generator
        spread_combinations = self.spread_generator.generate_filtered_spreads(
            options_df,
            config={
                "min_risk_reward_ratio": self.config.min_risk_reward_ratio,
                "min_spread_width": 1.0,
                "max_spread_width": 20.0,
                "min_liquidity_score": 50.0,
                "use_vectorized": True,  # Use fast vectorized operations
            },
        )

        if not spread_combinations:
            return []  # No valid spreads found

        # Step 6: Calculate probability and position sizing for each spread
        recommendations = await self._analyze_spread_combinations(
            spread_combinations, options_df, account_size
        )

        # Step 7: Filter by probability requirements
        valid_recommendations = [
            rec
            for rec in recommendations
            if rec.probability_of_profit >= self.config.min_probability_of_profit
        ]

        # Step 8: Rank and return top recommendations
        ranked_recommendations = self._rank_recommendations(valid_recommendations)
        return ranked_recommendations[:max_recommendations]

    async def _update_market_context(self) -> None:
        """Update current market context (SPY price, VIX, sentiment)."""
        # Get current SPY price
        spy_data = await self.market_service.get_spy_quote()
        self._current_spy_price = spy_data.price

        # For VIX, we'll need to add a method to get VIX data
        # For now, use a default volatility or extend MarketDataService
        self._current_vix = 20.0  # Default VIX level - to be implemented

        # Calculate current sentiment score
        self._current_sentiment_score = (
            await self.sentiment_calculator.calculate_sentiment()
        )

    def _is_market_suitable_for_trading(self) -> bool:
        """
        Check if current market conditions are suitable for spread trading.

        Returns:
                True if conditions are suitable, False otherwise
        """
        # Check that we have required data
        if not all(
            [self._current_spy_price, self._current_vix, self._current_sentiment_score]
        ):
            return False

        # Check if market is open (basic check - can be enhanced)
        now = datetime.now()
        if now.weekday() >= 5:  # Weekend
            return False

        # Check if VIX is within reasonable bounds for trading
        if self._current_vix > 50.0:  # Extremely high volatility
            return False

        return True

    async def _get_current_option_chain(self) -> Any:
        """
        Get current SPY option chain for 0-DTE options.

        Returns:
                Dictionary containing option chain data
        """
        # Get today's date for 0-DTE options
        today = date.today()

        # Get option chain from market service
        option_chain_response = await self.market_service.get_spy_options(
            expiration=today, option_type="call"  # Only get calls for bull-call-spreads
        )

        return option_chain_response

    def _generate_spread_combinations(
        self, option_chain: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Generate all possible bull-call-spread combinations from option chain.

        Args:
                option_chain: Option chain data from market service

        Returns:
                List of spread combination dictionaries
        """
        spreads = []
        calls = option_chain.get("calls", [])

        # Generate bull-call spreads (long lower strike, short higher strike)
        for i, long_option in enumerate(calls):
            for short_option in calls[i + 1 :]:  # Only higher strikes
                spread = {
                    "long_option": long_option,
                    "short_option": short_option,
                    "long_strike": long_option["strike"],
                    "short_strike": short_option["strike"],
                    "spread_width": short_option["strike"] - long_option["strike"],
                }
                spreads.append(spread)

        return spreads

    def _filter_spreads_by_criteria(
        self, spread_candidates: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Filter spread candidates by basic criteria.

        Args:
                spread_candidates: List of spread combinations

        Returns:
                List of spreads that meet basic criteria
        """
        valid_spreads = []

        for spread in spread_candidates:
            long_option = spread["long_option"]
            short_option = spread["short_option"]

            # Check bid-ask spread requirements
            long_spread_pct = self._calculate_bid_ask_spread_pct(long_option)
            short_spread_pct = self._calculate_bid_ask_spread_pct(short_option)

            if (
                long_spread_pct > self.config.max_bid_ask_spread_pct
                or short_spread_pct > self.config.max_bid_ask_spread_pct
            ):
                continue

            # Check volume requirements
            if (
                long_option.get("volume", 0) < self.config.min_volume
                or short_option.get("volume", 0) < self.config.min_volume
            ):
                continue

            # Check time to expiry (if available)
            # This would be implemented based on option chain data structure

            valid_spreads.append(spread)

        return valid_spreads

    def _calculate_bid_ask_spread_pct(self, option: dict[str, Any]) -> float:
        """Calculate bid-ask spread as percentage of mid price."""
        bid = option.get("bid", 0)
        ask = option.get("ask", 0)

        if bid <= 0 or ask <= 0:
            return float("inf")  # Invalid pricing

        mid = (bid + ask) / 2
        spread_pct = (ask - bid) / mid if mid > 0 else float("inf")

        return spread_pct

    async def _analyze_spreads(
        self, valid_spreads: list[dict[str, Any]], account_size: float
    ) -> list[SpreadRecommendation]:
        """
        Analyze valid spreads with risk metrics and probability calculations.

        Args:
                valid_spreads: List of spreads that passed basic filtering
                account_size: Account size for position sizing

        Returns:
                List of analyzed spread recommendations
        """
        recommendations = []

        for spread in valid_spreads:
            try:
                recommendation = await self._analyze_single_spread(spread, account_size)
                if recommendation:
                    recommendations.append(recommendation)
            except Exception as e:
                # Log error and continue with next spread
                print(f"Error analyzing spread: {e}")
                continue

        return recommendations

    async def _analyze_single_spread(
        self, spread: dict[str, Any], account_size: float
    ) -> SpreadRecommendation | None:
        """
        Analyze a single spread and create recommendation if it meets criteria.

        Args:
                spread: Spread data dictionary
                account_size: Account size for position sizing

        Returns:
                SpreadRecommendation if spread meets criteria, None otherwise
        """
        long_option = spread["long_option"]
        short_option = spread["short_option"]

        # Calculate net debit and risk metrics
        long_premium = (long_option["bid"] + long_option["ask"]) / 2
        short_premium = (short_option["bid"] + short_option["ask"]) / 2
        net_debit = long_premium - short_premium

        if net_debit <= 0:
            return None  # Invalid spread (should be net debit)

        max_risk = net_debit
        max_profit = spread["spread_width"] - net_debit

        if max_profit <= 0:
            return None  # No profit potential

        risk_reward_ratio = max_profit / max_risk

        # Check minimum risk/reward ratio
        if risk_reward_ratio < self.config.min_risk_reward_ratio:
            return None

        # Calculate probability of profit using Black-Scholes
        breakeven = long_option["strike"] + net_debit
        time_to_expiry = 1.0 / 365  # 0-DTE approximation (can be refined)
        volatility = self._current_vix / 100 if self._current_vix else 0.20

        probability_of_profit = self.black_scholes.probability_of_profit(
            spot_price=self._current_spy_price,
            strike_price=breakeven,
            time_to_expiry=time_to_expiry,
            volatility=volatility,
        )

        # Check minimum probability requirement
        if probability_of_profit < self.config.min_probability_of_profit:
            return None

        # Calculate position sizing
        max_position_cost = account_size * self.config.max_buying_power_pct
        contracts_to_trade = max(1, int(max_position_cost / (net_debit * 100)))
        total_cost = contracts_to_trade * net_debit * 100
        buying_power_used_pct = total_cost / account_size

        # Calculate expected value and ranking score
        expected_value = (probability_of_profit * max_profit) - (
            (1 - probability_of_profit) * max_risk
        )
        ranking_score = self._calculate_ranking_score(
            probability_of_profit, risk_reward_ratio, expected_value
        )

        return SpreadRecommendation(
            long_strike=long_option["strike"],
            short_strike=short_option["strike"],
            long_premium=long_premium,
            short_premium=short_premium,
            net_debit=net_debit,
            max_risk=max_risk,
            max_profit=max_profit,
            risk_reward_ratio=risk_reward_ratio,
            probability_of_profit=probability_of_profit,
            breakeven_price=breakeven,
            long_bid=long_option["bid"],
            long_ask=long_option["ask"],
            short_bid=short_option["bid"],
            short_ask=short_option["ask"],
            long_volume=long_option.get("volume", 0),
            short_volume=short_option.get("volume", 0),
            expected_value=expected_value,
            sentiment_score=self._current_sentiment_score,
            ranking_score=ranking_score,
            timestamp=datetime.now(),
            contracts_to_trade=contracts_to_trade,
            total_cost=total_cost,
            buying_power_used_pct=buying_power_used_pct,
        )

    def _calculate_ranking_score(
        self,
        probability_of_profit: float,
        risk_reward_ratio: float,
        expected_value: float,
    ) -> float:
        """
        Calculate ranking score for spread recommendation.

        Args:
                probability_of_profit: Probability of profit (0-1)
                risk_reward_ratio: Risk/reward ratio
                expected_value: Expected value of the trade

        Returns:
                Ranking score (higher is better)
        """
        # Normalize risk_reward_ratio (cap at 5.0 for scoring purposes)
        normalized_rr = min(risk_reward_ratio, 5.0) / 5.0

        # Normalize sentiment score (-1 to 1 -> 0 to 1)
        normalized_sentiment = (
            (self._current_sentiment_score + 1) / 2
            if self._current_sentiment_score
            else 0.5
        )

        # Calculate weighted score
        score = (
            self.config.probability_weight * probability_of_profit
            + self.config.risk_reward_weight * normalized_rr
            + self.config.sentiment_weight * normalized_sentiment
        )

        return score

    def _rank_spreads(
        self, recommendations: list[SpreadRecommendation]
    ) -> list[SpreadRecommendation]:
        """
        Rank spread recommendations by their ranking score.

        Args:
                recommendations: List of spread recommendations

        Returns:
                List sorted by ranking score (highest first)
        """
        return sorted(recommendations, key=lambda x: x.ranking_score, reverse=True)

    async def _analyze_spread_combinations(
        self, spread_combinations: list, options_df: Any, account_size: float
    ) -> list[SpreadRecommendation]:
        """
        Analyze spread combinations and create recommendations.

        Args:
            spread_combinations: List of SpreadCombination objects
            options_df: Options DataFrame (for additional data if needed)
            account_size: Account size for position sizing

        Returns:
            List of SpreadRecommendation objects
        """
        recommendations = []

        for spread in spread_combinations:
            # Calculate position sizing
            position_info = self.spread_generator.calculate_position_size(
                spread,
                account_size=account_size,
                max_risk_pct=self.config.max_buying_power_pct,
            )

            # Calculate probability of profit using Black-Scholes
            time_to_expiry = 1.0 / 365  # 0-DTE approximation
            volatility = self._current_vix / 100 if self._current_vix else 0.20

            probability_of_profit = self.black_scholes.probability_of_profit(
                spot_price=self._current_spy_price,
                strike_price=spread.breakeven,
                time_to_expiry=time_to_expiry,
                volatility=volatility,
            )

            # Calculate expected value
            expected_value = (probability_of_profit * spread.max_profit) - (
                (1 - probability_of_profit) * spread.max_risk
            )

            # Calculate ranking score
            ranking_score = self._calculate_ranking_score(
                probability_of_profit, spread.risk_reward_ratio, expected_value
            )

            # Create recommendation
            recommendation = SpreadRecommendation(
                long_strike=spread.long_strike,
                short_strike=spread.short_strike,
                long_premium=spread.long_mid,
                short_premium=spread.short_mid,
                net_debit=spread.net_debit,
                max_risk=spread.max_risk,
                max_profit=spread.max_profit,
                risk_reward_ratio=spread.risk_reward_ratio,
                probability_of_profit=probability_of_profit,
                breakeven_price=spread.breakeven,
                long_bid=spread.long_bid,
                long_ask=spread.long_ask,
                short_bid=spread.short_bid,
                short_ask=spread.short_ask,
                long_volume=spread.long_volume,
                short_volume=spread.short_volume,
                expected_value=expected_value,
                sentiment_score=self._current_sentiment_score,
                ranking_score=ranking_score,
                timestamp=datetime.now(),
                contracts_to_trade=position_info["contracts"],
                total_cost=position_info["total_cost"],
                buying_power_used_pct=position_info["risk_pct"],
            )

            # Validate the recommendation against risk constraints
            validation_result = self.risk_validator.validate_spread(
                recommendation, account_size
            )

            # Only add if it passes all risk checks
            if validation_result["is_valid"]:
                recommendations.append(recommendation)

        return recommendations

    def _rank_recommendations(
        self, recommendations: list[SpreadRecommendation]
    ) -> list[SpreadRecommendation]:
        """
        Rank spread recommendations by their ranking score.

        Args:
            recommendations: List of spread recommendations

        Returns:
            List sorted by ranking score (highest first)
        """
        return sorted(recommendations, key=lambda x: x.ranking_score, reverse=True)

    def get_configuration(self) -> SpreadConfiguration:
        """Get current service configuration."""
        return self.config

    def update_configuration(self, config: SpreadConfiguration) -> None:
        """Update service configuration."""
        self.config = config
        # Update risk validator with new limits
        self.risk_validator.update_configuration(
            max_buying_power_pct=config.max_buying_power_pct,
            min_risk_reward_ratio=config.min_risk_reward_ratio,
        )
