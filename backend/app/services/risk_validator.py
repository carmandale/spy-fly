"""
Risk Validator for spread recommendations.

This module enforces strict risk management constraints to ensure
trades adhere to predefined safety parameters:
- Maximum 5% buying power per trade
- Minimum 1:1 risk/reward ratio
- Proper position sizing with fractional contract handling
"""

from dataclasses import dataclass
from typing import Any, Optional
import math

from app.models.spread import SpreadRecommendation


@dataclass
class RiskValidationResult:
    """Result of a risk validation check."""
    
    is_valid: bool
    message: str
    actual_value: Optional[float] = None
    limit_value: Optional[float] = None
    
    # Specific fields for different validation types
    actual_percentage: Optional[float] = None
    max_allowed_percentage: Optional[float] = None
    actual_ratio: Optional[float] = None
    min_required_ratio: Optional[float] = None


class RiskValidator:
    """
    Validates spread recommendations against risk management constraints.
    
    This class enforces hard limits on position sizing and risk/reward
    ratios to protect trading capital and ensure disciplined trading.
    """
    
    def __init__(
        self,
        max_buying_power_pct: float = 0.05,
        min_risk_reward_ratio: float = 1.0
    ):
        """
        Initialize the risk validator with configurable limits.
        
        Args:
            max_buying_power_pct: Maximum percentage of account for single trade (default 5%)
            min_risk_reward_ratio: Minimum acceptable risk/reward ratio (default 1:1)
        """
        self.max_buying_power_pct = max_buying_power_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio
    
    def validate_buying_power(
        self,
        recommendation: SpreadRecommendation,
        account_size: float
    ) -> RiskValidationResult:
        """
        Validate that the recommendation doesn't exceed buying power limits.
        
        Args:
            recommendation: The spread recommendation to validate
            account_size: Total account size
            
        Returns:
            RiskValidationResult with validation details
            
        Raises:
            ValueError: If account size is not positive
        """
        if account_size <= 0:
            raise ValueError(f"Account size must be positive, got {account_size}")
        
        # Calculate actual buying power usage
        actual_percentage = recommendation.buying_power_used_pct
        
        # Check against limit
        is_valid = actual_percentage <= self.max_buying_power_pct
        
        if is_valid:
            message = "Buying power usage within limits"
        else:
            message = (
                f"Buying power usage {actual_percentage:.1%} exceeds maximum "
                f"{self.max_buying_power_pct:.1%}"
            )
        
        return RiskValidationResult(
            is_valid=is_valid,
            message=message,
            actual_percentage=actual_percentage,
            max_allowed_percentage=self.max_buying_power_pct
        )
    
    def validate_risk_reward_ratio(
        self,
        recommendation: SpreadRecommendation
    ) -> RiskValidationResult:
        """
        Validate that the risk/reward ratio meets minimum requirements.
        
        Args:
            recommendation: The spread recommendation to validate
            
        Returns:
            RiskValidationResult with validation details
        """
        # Handle edge case of zero net debit
        if recommendation.net_debit <= 0:
            return RiskValidationResult(
                is_valid=False,
                message="Invalid spread: net debit must be positive",
                actual_ratio=0.0,
                min_required_ratio=self.min_risk_reward_ratio
            )
        
        actual_ratio = recommendation.risk_reward_ratio
        is_valid = actual_ratio >= self.min_risk_reward_ratio
        
        if is_valid:
            message = "Risk/reward ratio meets requirements"
        else:
            message = (
                f"Risk/reward ratio {actual_ratio:.2f}:1 is below minimum "
                f"{self.min_risk_reward_ratio:.1f}:1"
            )
        
        return RiskValidationResult(
            is_valid=is_valid,
            message=message,
            actual_ratio=actual_ratio,
            min_required_ratio=self.min_risk_reward_ratio
        )
    
    def calculate_position_size(
        self,
        account_size: float,
        net_debit: float,
        max_buying_power_pct: Optional[float] = None
    ) -> dict[str, Any]:
        """
        Calculate the appropriate position size given constraints.
        
        Args:
            account_size: Total account size
            net_debit: Net debit per contract
            max_buying_power_pct: Override for max buying power percentage
            
        Returns:
            Dictionary with position sizing details:
            - contracts: Number of contracts to trade
            - total_cost: Total cost of the position
            - buying_power_pct: Actual buying power percentage used
            - warning: Optional warning if constraints are violated
            
        Raises:
            ValueError: If inputs are invalid
        """
        if account_size <= 0:
            raise ValueError(f"Account size must be positive, got {account_size}")
        if net_debit <= 0:
            raise ValueError(f"Net debit must be positive, got {net_debit}")
        
        if max_buying_power_pct is None:
            max_buying_power_pct = self.max_buying_power_pct
        
        if max_buying_power_pct <= 0:
            raise ValueError(f"Buying power percentage must be positive, got {max_buying_power_pct}")
        
        # Calculate maximum position value
        max_position_value = account_size * max_buying_power_pct
        
        # Calculate contracts (options are traded in lots of 100)
        max_contracts = max_position_value / (net_debit * 100)
        
        # Round down to whole contracts
        contracts = int(max_contracts)
        
        # Ensure minimum 1 contract
        if contracts < 1:
            contracts = 1
            warning = "Position size exceeds buying power limit"
        else:
            warning = None
        
        # Calculate actual values
        total_cost = contracts * net_debit * 100
        buying_power_pct = total_cost / account_size
        
        return {
            'contracts': contracts,
            'total_cost': total_cost,
            'buying_power_pct': buying_power_pct,
            'warning': warning
        }
    
    def validate_spread(
        self,
        recommendation: SpreadRecommendation,
        account_size: float
    ) -> dict[str, Any]:
        """
        Perform comprehensive validation of a spread recommendation.
        
        Args:
            recommendation: The spread recommendation to validate
            account_size: Total account size
            
        Returns:
            Dictionary with validation results:
            - is_valid: Overall validation result
            - buying_power_check: Buying power validation result
            - risk_reward_check: Risk/reward validation result
            - errors: List of validation errors
        """
        errors = []
        
        # Validate buying power
        bp_result = self.validate_buying_power(recommendation, account_size)
        if not bp_result.is_valid:
            errors.append(bp_result.message)
        
        # Validate risk/reward ratio
        rr_result = self.validate_risk_reward_ratio(recommendation)
        if not rr_result.is_valid:
            errors.append(rr_result.message)
        
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'buying_power_check': bp_result,
            'risk_reward_check': rr_result,
            'errors': errors
        }
    
    def validate_spreads_batch(
        self,
        recommendations: list[SpreadRecommendation],
        account_size: float
    ) -> dict[str, Any]:
        """
        Validate multiple spread recommendations in batch.
        
        Args:
            recommendations: List of spread recommendations
            account_size: Total account size
            
        Returns:
            Dictionary with batch validation results:
            - valid_spreads: List of spreads that passed validation
            - invalid_spreads: List of spreads that failed validation
            - validation_details: Detailed results for each spread
        """
        valid_spreads = []
        invalid_spreads = []
        validation_details = []
        
        for i, spread in enumerate(recommendations):
            result = self.validate_spread(spread, account_size)
            validation_details.append(result)
            
            if result['is_valid']:
                valid_spreads.append(spread)
            else:
                invalid_spreads.append(spread)
                # Simplify error messages for batch result
                if result['errors']:
                    validation_details[i]['errors'] = [
                        self._simplify_error_message(error) 
                        for error in result['errors']
                    ]
        
        return {
            'valid_spreads': valid_spreads,
            'invalid_spreads': invalid_spreads,
            'validation_details': validation_details
        }
    
    def _simplify_error_message(self, error: str) -> str:
        """Simplify error message for batch results."""
        if "exceeds maximum" in error:
            return "Buying power exceeds maximum"
        elif "below minimum" in error:
            return "Risk/reward ratio below minimum"
        else:
            return error
    
    def update_configuration(
        self,
        max_buying_power_pct: Optional[float] = None,
        min_risk_reward_ratio: Optional[float] = None
    ) -> None:
        """
        Update risk validator configuration.
        
        Args:
            max_buying_power_pct: New maximum buying power percentage
            min_risk_reward_ratio: New minimum risk/reward ratio
        """
        if max_buying_power_pct is not None:
            self.max_buying_power_pct = max_buying_power_pct
        
        if min_risk_reward_ratio is not None:
            self.min_risk_reward_ratio = min_risk_reward_ratio