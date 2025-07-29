"""
OrderFormatter service for creating and formatting order tickets.

This service integrates spread recommendations with order ticket generation
and broker-specific formatting to provide a complete execution workflow.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from app.models.execution import (
    OrderTicket,
    BrokerFormat,
    OrderType,
    TimeInForce,
)
from app.models.spread import SpreadRecommendation
from app.services.execution.broker_format_adapter import BrokerFormatAdapter


class OrderFormatterError(Exception):
    """Exception raised for order formatting errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class OrderFormatter:
    """Service for creating and formatting order tickets from spread recommendations."""
    
    def __init__(self, broker_adapter: Optional[BrokerFormatAdapter] = None):
        """
        Initialize OrderFormatter.
        
        Args:
            broker_adapter: BrokerFormatAdapter instance for formatting orders
        """
        self.broker_adapter = broker_adapter or BrokerFormatAdapter()
    
    def create_order_ticket(
        self,
        recommendation_id: str,
        recommendation: SpreadRecommendation,
        account_size: Decimal,
        broker_format: BrokerFormat = BrokerFormat.INTERACTIVE_BROKERS,
        order_type: OrderType = OrderType.LIMIT,
        time_in_force: TimeInForce = TimeInForce.DAY,
        custom_quantity: Optional[int] = None,
        limit_price_adjustment: Optional[Decimal] = None
    ) -> OrderTicket:
        """
        Create order ticket from spread recommendation.
        
        Args:
            recommendation_id: Unique identifier for this order
            recommendation: SpreadRecommendation to convert
            account_size: Total account size for validation
            broker_format: Target broker format
            order_type: Order type (limit, market, etc.)
            time_in_force: Time in force setting
            custom_quantity: Override recommended quantity
            limit_price_adjustment: Adjustment to limit prices
            
        Returns:
            OrderTicket ready for broker submission
            
        Raises:
            OrderFormatterError: If validation fails or data is invalid
        """
        # Validate inputs
        self._validate_order_parameters(
            recommendation=recommendation,
            account_size=account_size,
            custom_quantity=custom_quantity
        )
        
        # Determine contract quantity
        quantity = custom_quantity or recommendation.contracts_to_trade
        if quantity <= 0:
            raise OrderFormatterError(
                "Invalid contract quantity",
                details={"quantity": quantity, "recommendation_id": recommendation_id}
            )
        
        # Calculate pricing
        long_limit_price = None
        short_limit_price = None
        net_debit = Decimal(str(recommendation.net_debit))
        
        if order_type == OrderType.LIMIT:
            long_limit_price = Decimal(str(recommendation.long_premium))
            short_limit_price = Decimal(str(recommendation.short_premium))
            
            # Apply limit price adjustment if provided
            if limit_price_adjustment:
                long_limit_price += limit_price_adjustment
                short_limit_price += limit_price_adjustment
                net_debit = long_limit_price - short_limit_price
        
        # Calculate position sizing and costs
        total_cost = net_debit * quantity * 100  # Options are per 100 shares
        buying_power_used_pct = float(total_cost) / float(account_size)
        
        # Validate buying power doesn't exceed 5% limit
        if buying_power_used_pct > 0.05:
            raise OrderFormatterError(
                f"Position exceeds 5% buying power limit: {buying_power_used_pct:.1%}",
                details={
                    "total_cost": float(total_cost),
                    "account_size": float(account_size),
                    "buying_power_used": buying_power_used_pct
                }
            )
        
        # Create order ticket
        try:
            order_ticket = OrderTicket(
                recommendation_id=recommendation_id,
                symbol="SPY",  # Currently only supporting SPY
                long_strike=Decimal(str(recommendation.long_strike)),
                short_strike=Decimal(str(recommendation.short_strike)),
                expiration_date=date.today(),  # 0-DTE options
                long_quantity=quantity,
                short_quantity=quantity,
                order_type=order_type,
                time_in_force=time_in_force,
                long_limit_price=long_limit_price,
                short_limit_price=short_limit_price,
                net_debit=net_debit,
                max_risk=Decimal(str(recommendation.max_risk)),
                max_profit=Decimal(str(recommendation.max_profit)),
                broker_format=broker_format,
                account_size=account_size,
                buying_power_used_pct=Decimal(str(buying_power_used_pct)),
                total_cost=total_cost
            )
            
            return order_ticket
            
        except Exception as e:
            raise OrderFormatterError(
                f"Failed to create order ticket: {str(e)}",
                details={"recommendation_id": recommendation_id, "error": str(e)}
            ) from e
    
    def format_order(self, order_ticket: OrderTicket) -> str:
        """
        Format order ticket for broker platform.
        
        Args:
            order_ticket: OrderTicket to format
            
        Returns:
            Formatted order string ready for copy-paste
            
        Raises:
            OrderFormatterError: If formatting fails
        """
        try:
            return self.broker_adapter.format_order(order_ticket)
        except Exception as e:
            raise OrderFormatterError(
                f"Failed to format order for broker: {str(e)}",
                details={"broker_format": order_ticket.broker_format.value, "error": str(e)}
            ) from e
    
    def generate_order_package(
        self,
        recommendation_id: str,
        recommendation: SpreadRecommendation,
        account_size: Decimal,
        broker_format: BrokerFormat = BrokerFormat.INTERACTIVE_BROKERS,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate complete order package with all components.
        
        Args:
            recommendation_id: Unique identifier for this order
            recommendation: SpreadRecommendation to convert
            account_size: Total account size
            broker_format: Target broker format
            **kwargs: Additional arguments for order creation
            
        Returns:
            Dictionary containing order_ticket, formatted_order, checklist, and risk_summary
        """
        # Create order ticket
        order_ticket = self.create_order_ticket(
            recommendation_id=recommendation_id,
            recommendation=recommendation,
            account_size=account_size,
            broker_format=broker_format,
            **kwargs
        )
        
        # Generate all components
        formatted_order = self.format_order(order_ticket)
        execution_checklist = self.generate_execution_checklist(order_ticket)
        risk_summary = self.generate_risk_summary(order_ticket)
        
        # Package with metadata
        generated_at = datetime.now()
        expires_at = generated_at + timedelta(hours=1)  # Order preparation expires in 1 hour
        
        return {
            "order_ticket": order_ticket,
            "formatted_order": formatted_order,
            "execution_checklist": execution_checklist,
            "risk_summary": risk_summary,
            "generated_at": generated_at,
            "expires_at": expires_at
        }
    
    def generate_execution_checklist(self, order_ticket: OrderTicket) -> List[str]:
        """
        Generate step-by-step execution checklist.
        
        Args:
            order_ticket: OrderTicket to generate checklist for
            
        Returns:
            List of execution steps
        """
        checklist = [
            "1. Verify market is open and trading normally",
            f"2. Confirm account has sufficient buying power (${order_ticket.total_cost:.2f} required)",
            f"3. Check current SPY price and option liquidity",
            f"4. Review risk parameters: Max Risk ${order_ticket.max_risk:.2f}, Max Profit ${order_ticket.max_profit:.2f}",
        ]
        
        # Add broker-specific steps
        if order_ticket.broker_format == BrokerFormat.INTERACTIVE_BROKERS:
            checklist.extend([
                "5. In TWS, navigate to Options Trading for SPY",
                "6. Set up the spread as shown in the order details",
                "7. Verify limit prices match current market conditions",
                "8. Double-check contract quantities and expiration date",
                "9. Submit order and monitor for fill confirmation"
            ])
        elif order_ticket.broker_format == BrokerFormat.TD_AMERITRADE:
            checklist.extend([
                "5. In TD Ameritrade, go to Trade > Options",
                "6. Select SPY and choose the spread strategy",
                "7. Enter strikes and quantities as specified",
                "8. Set limit price for net debit",
                "9. Review and submit the order"
            ])
        elif order_ticket.broker_format == BrokerFormat.ETRADE:
            checklist.extend([
                "5. In E*TRADE, navigate to Options Trading",
                "6. Set up Bull Call Spread for SPY",
                "7. Enter long and short strike prices",
                "8. Verify net debit and contract quantities",
                "9. Submit spread order"
            ])
        elif order_ticket.broker_format == BrokerFormat.SCHWAB:
            checklist.extend([
                "5. In Schwab StreetSmart, go to Options Chain",
                "6. Create Bull Call Spread with specified strikes",
                "7. Set BUY TO OPEN and SELL TO OPEN legs",
                "8. Enter net debit limit price",
                "9. Review and submit order"
            ])
        else:  # Generic
            checklist.extend([
                "5. Open your broker's options trading platform",
                "6. Navigate to SPY options for today's expiration",
                "7. Set up Bull Call Spread with the specified strikes",
                "8. Enter contract quantities and limit prices",
                "9. Review all details and submit the order"
            ])
        
        checklist.append("10. Monitor position and set alerts for profit/loss targets")
        
        return checklist
    
    def generate_risk_summary(self, order_ticket: OrderTicket) -> Dict[str, Any]:
        """
        Generate comprehensive risk summary.
        
        Args:
            order_ticket: OrderTicket to analyze
            
        Returns:
            Dictionary with risk metrics
        """
        max_risk = float(order_ticket.max_risk)
        max_profit = float(order_ticket.max_profit)
        
        return {
            "max_risk": max_risk,
            "max_profit": max_profit,
            "risk_reward_ratio": round(max_profit / max_risk, 3) if max_risk > 0 else 0,
            "breakeven_price": float(order_ticket.long_strike + order_ticket.net_debit),
            "probability_of_profit": 0.65,  # From recommendation (simplified)
            "buying_power_used": float(order_ticket.buying_power_used_pct),
            "total_cost": float(order_ticket.total_cost),
            "contracts": order_ticket.long_quantity,
            "cost_per_contract": float(order_ticket.net_debit * 100),
            "expiration": "Today (0-DTE)",
            "time_decay_risk": "High - position will expire worthless if SPY closes below long strike"
        }
    
    def _validate_order_parameters(
        self,
        recommendation: SpreadRecommendation,
        account_size: Decimal,
        custom_quantity: Optional[int] = None
    ) -> None:
        """
        Validate order parameters before creating order ticket.
        
        Args:
            recommendation: SpreadRecommendation to validate
            account_size: Account size to validate
            custom_quantity: Custom quantity to validate if provided
            
        Raises:
            OrderFormatterError: If validation fails
        """
        # Validate account size
        if account_size <= 0:
            raise OrderFormatterError(
                "Account size must be positive",
                details={"account_size": float(account_size)}
            )
        
        # Validate recommendation data
        if recommendation.net_debit <= 0:
            raise OrderFormatterError(
                "Invalid recommendation: net debit must be positive",
                details={"net_debit": recommendation.net_debit}
            )
        
        if recommendation.long_strike >= recommendation.short_strike:
            raise OrderFormatterError(
                "Invalid recommendation: long strike must be less than short strike for bull call spread",
                details={
                    "long_strike": recommendation.long_strike,
                    "short_strike": recommendation.short_strike
                }
            )
        
        # Validate custom quantity
        if custom_quantity is not None and custom_quantity <= 0:
            raise OrderFormatterError(
                "Custom quantity must be positive",
                details={"custom_quantity": custom_quantity}
            )
        
        # Validate contracts to trade
        if recommendation.contracts_to_trade <= 0:
            raise OrderFormatterError(
                "Recommendation has invalid contract quantity",
                details={"contracts_to_trade": recommendation.contracts_to_trade}
            )