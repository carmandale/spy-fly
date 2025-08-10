"""
Trade to Position Data Mapper.

This module handles the transformation of data between Trade/TradeSpread models
and Position models, including field mapping, data validation, and business
logic for calculating position parameters from trade data.
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional
from decimal import Decimal

from app.models.trading import Trade, TradeSpread
from app.core.exceptions import ServiceError

logger = logging.getLogger(__name__)


class TradeToPositionMappingError(ServiceError):
    """Exception raised for trade-to-position mapping errors."""
    pass


class TradeToPositionMapper:
    """
    Mapper class for transforming Trade/TradeSpread data to Position format.
    
    This class handles:
    - Field mapping between different data models
    - Data validation and type conversion
    - Business logic for calculating position parameters
    - Default value assignment for missing fields
    """
    
    def map_trade_to_position(
        self,
        trade: Trade,
        current_spy_price: float,
        current_vix: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Map a Trade (with TradeSpread) to Position data.
        
        Args:
            trade: The trade record to map
            current_spy_price: Current SPY price for entry conditions
            current_vix: Current VIX level (optional)
            
        Returns:
            Dictionary containing position data ready for Position model creation
            
        Raises:
            TradeToPositionMappingError: If mapping fails due to invalid data
        """
        try:
            if not trade.spread:
                raise TradeToPositionMappingError("Trade must have spread data to create position")
            
            spread = trade.spread
            
            # Basic position identification
            position_data = {
                "symbol": "SPY",  # Assuming SPY for now - could be made configurable
                "position_type": self._map_spread_type(spread.spread_type),
                "status": "open",  # New positions start as open
                "contracts": trade.contracts or 1,
                "entry_date": trade.trade_date,
                "expiration_date": spread.expiration_date,
            }
            
            # Spread configuration
            position_data.update({
                "long_strike": float(spread.long_strike),
                "short_strike": float(spread.short_strike),
            })
            
            # Entry pricing - map from spread data
            position_data.update({
                "entry_long_premium": float(spread.long_premium),
                "entry_short_premium": float(spread.short_premium),
                "entry_net_debit": float(spread.net_debit),
                "entry_total_cost": self._calculate_entry_total_cost(spread, trade.contracts or 1),
            })
            
            # Risk metrics - use spread calculations
            position_data.update({
                "max_profit": float(spread.max_profit),
                "max_loss": float(spread.max_loss),
                "breakeven_price": float(spread.breakeven),
            })
            
            # Entry market conditions
            position_data.update({
                "entry_spy_price": current_spy_price,
                "entry_vix": current_vix,
                "entry_sentiment_score": self._get_sentiment_score_from_trade(trade),
            })
            
            # Position management - use defaults or trade-specific values
            position_data.update({
                "profit_target_percent": self._calculate_profit_target_percent(spread),
                "stop_loss_percent": self._calculate_stop_loss_percent(spread),
            })
            
            # Metadata
            position_data.update({
                "notes": self._generate_position_notes(trade),
            })
            
            # Validate the mapped data
            self._validate_position_data(position_data)
            
            logger.debug(f"Successfully mapped trade {trade.id} to position data")
            return position_data
            
        except Exception as e:
            logger.error(f"Failed to map trade {trade.id} to position: {str(e)}")
            raise TradeToPositionMappingError(f"Mapping failed: {str(e)}") from e
    
    def _map_spread_type(self, trade_spread_type: str) -> str:
        """Map trade spread type to position type."""
        mapping = {
            "bull_call_spread": "bull_call_spread",
            "bear_put_spread": "bear_put_spread",
            "bull_call": "bull_call_spread",  # Handle variations
            "bear_put": "bear_put_spread",
        }
        
        return mapping.get(trade_spread_type.lower(), "bull_call_spread")
    
    def _calculate_entry_total_cost(self, spread: TradeSpread, contracts: int) -> float:
        """Calculate total entry cost for the position."""
        try:
            # Net debit per contract * number of contracts * 100 (option multiplier)
            net_debit = float(spread.net_debit)
            total_cost = net_debit * contracts * 100
            
            # Ensure positive cost (debit spreads should have positive cost)
            return abs(total_cost)
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to calculate entry total cost: {str(e)}")
            return 0.0
    
    def _get_sentiment_score_from_trade(self, trade: Trade) -> Optional[float]:
        """Extract sentiment score from trade if available."""
        try:
            if trade.sentiment_score and hasattr(trade.sentiment_score, 'total_score'):
                # Convert sentiment score to decimal (0-1 range)
                return float(trade.sentiment_score.total_score) / 100.0
            return None
        except (AttributeError, ValueError, TypeError):
            return None
    
    def _calculate_profit_target_percent(self, spread: TradeSpread) -> float:
        """Calculate profit target percentage based on spread characteristics."""
        try:
            # Default profit target of 50% of max profit
            default_target = 50.0
            
            # Adjust based on risk/reward ratio
            if spread.risk_reward_ratio:
                risk_reward = float(spread.risk_reward_ratio)
                
                # Higher risk/reward ratios can have higher profit targets
                if risk_reward >= 2.0:
                    return 60.0  # 60% target for high reward spreads
                elif risk_reward >= 1.5:
                    return 55.0  # 55% target for good reward spreads
                elif risk_reward < 1.0:
                    return 40.0  # Lower target for poor risk/reward
            
            return default_target
            
        except (ValueError, TypeError):
            return 50.0  # Default fallback
    
    def _calculate_stop_loss_percent(self, spread: TradeSpread) -> float:
        """Calculate stop loss percentage based on spread characteristics."""
        try:
            # Default stop loss of 20% of max loss
            default_stop = 20.0
            
            # Adjust based on risk/reward ratio
            if spread.risk_reward_ratio:
                risk_reward = float(spread.risk_reward_ratio)
                
                # Lower risk/reward ratios should have tighter stops
                if risk_reward < 1.0:
                    return 15.0  # Tighter stop for poor risk/reward
                elif risk_reward >= 2.0:
                    return 25.0  # Wider stop for high reward spreads
            
            return default_stop
            
        except (ValueError, TypeError):
            return 20.0  # Default fallback
    
    def _generate_position_notes(self, trade: Trade) -> Optional[str]:
        """Generate position notes from trade information."""
        notes_parts = []
        
        # Add trade ID reference
        notes_parts.append(f"Created from trade #{trade.id}")
        
        # Add entry signal reason if available
        if trade.entry_signal_reason:
            notes_parts.append(f"Entry reason: {trade.entry_signal_reason}")
        
        # Add trade notes if available
        if trade.notes:
            notes_parts.append(f"Trade notes: {trade.notes}")
        
        # Add probability of profit if available
        if trade.probability_of_profit:
            notes_parts.append(f"Entry PoP: {trade.probability_of_profit}%")
        
        return " | ".join(notes_parts) if notes_parts else None
    
    def _validate_position_data(self, position_data: Dict[str, Any]) -> None:
        """Validate position data before creation."""
        required_fields = [
            "symbol", "position_type", "status", "contracts", "entry_date",
            "expiration_date", "long_strike", "short_strike", "entry_long_premium",
            "entry_short_premium", "entry_net_debit", "entry_total_cost",
            "max_profit", "max_loss", "breakeven_price", "entry_spy_price"
        ]
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in position_data]
        if missing_fields:
            raise TradeToPositionMappingError(f"Missing required fields: {missing_fields}")
        
        # Validate data types and ranges
        validations = [
            ("contracts", lambda x: isinstance(x, int) and x > 0, "Contracts must be positive integer"),
            ("entry_total_cost", lambda x: isinstance(x, (int, float)) and x >= 0, "Entry cost must be non-negative"),
            ("long_strike", lambda x: isinstance(x, (int, float)) and x > 0, "Long strike must be positive"),
            ("short_strike", lambda x: isinstance(x, (int, float)) and x > 0, "Short strike must be positive"),
            ("max_profit", lambda x: isinstance(x, (int, float)) and x >= 0, "Max profit must be non-negative"),
            ("max_loss", lambda x: isinstance(x, (int, float)) and x >= 0, "Max loss must be non-negative"),
            ("entry_spy_price", lambda x: isinstance(x, (int, float)) and x > 0, "SPY price must be positive"),
        ]
        
        for field, validator, error_msg in validations:
            if field in position_data and not validator(position_data[field]):
                raise TradeToPositionMappingError(f"Invalid {field}: {error_msg}")
        
        # Validate date relationships
        if position_data["entry_date"] >= position_data["expiration_date"]:
            raise TradeToPositionMappingError("Entry date must be before expiration date")
        
        # Validate strike relationship for bull call spreads
        if (position_data["position_type"] == "bull_call_spread" and 
            position_data["long_strike"] >= position_data["short_strike"]):
            raise TradeToPositionMappingError("Bull call spread: long strike must be less than short strike")
        
        # Validate strike relationship for bear put spreads
        if (position_data["position_type"] == "bear_put_spread" and 
            position_data["long_strike"] <= position_data["short_strike"]):
            raise TradeToPositionMappingError("Bear put spread: long strike must be greater than short strike")
        
        logger.debug("Position data validation passed")
    
    def map_trade_update_to_position(
        self,
        trade: Trade,
        existing_position_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map trade updates to position updates.
        
        Args:
            trade: The updated trade record
            existing_position_data: Current position data
            
        Returns:
            Dictionary containing position updates
        """
        updates = {}
        
        # Update position management parameters if trade has new values
        if trade.spread:
            spread = trade.spread
            
            # Recalculate profit target and stop loss if spread data changed
            new_profit_target = self._calculate_profit_target_percent(spread)
            new_stop_loss = self._calculate_stop_loss_percent(spread)
            
            if new_profit_target != existing_position_data.get("profit_target_percent"):
                updates["profit_target_percent"] = new_profit_target
            
            if new_stop_loss != existing_position_data.get("stop_loss_percent"):
                updates["stop_loss_percent"] = new_stop_loss
        
        # Update notes if trade notes changed
        new_notes = self._generate_position_notes(trade)
        if new_notes != existing_position_data.get("notes"):
            updates["notes"] = new_notes
        
        return updates
