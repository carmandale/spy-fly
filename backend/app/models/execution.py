"""
Data models for trade execution and order ticket generation.

These models define the structure for order tickets, broker formats,
and execution workflow data used in the trade execution system.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BrokerFormat(str, Enum):
    """Supported broker formats for order ticket generation."""
    
    INTERACTIVE_BROKERS = "interactive_brokers"
    TD_AMERITRADE = "td_ameritrade"
    ETRADE = "etrade"
    SCHWAB = "schwab"
    GENERIC = "generic"
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name for UI."""
        display_names = {
            self.INTERACTIVE_BROKERS: "Interactive Brokers",
            self.TD_AMERITRADE: "TD Ameritrade",
            self.ETRADE: "E*TRADE",
            self.SCHWAB: "Charles Schwab",
            self.GENERIC: "Generic Format"
        }
        return display_names[self]


class OrderType(str, Enum):
    """Order types supported for spread execution."""
    
    LIMIT = "limit"
    MARKET = "market"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    """Time in force options for orders."""
    
    DAY = "day"        # Good for day
    GTC = "gtc"        # Good till canceled
    IOC = "ioc"        # Immediate or cancel
    FOK = "fok"        # Fill or kill


class OrderTicket(BaseModel):
    """
    Order ticket model for spread execution.
    
    Contains all information needed to generate a broker-ready order
    ticket for bull call spread execution.
    """
    
    # Core identification
    recommendation_id: str = Field(..., description="ID of the recommendation this order is based on")
    symbol: str = Field(..., description="Underlying symbol (e.g., SPY)")
    
    # Spread configuration
    long_strike: Decimal = Field(..., description="Strike price of long call")
    short_strike: Decimal = Field(..., description="Strike price of short call")
    expiration_date: date = Field(..., description="Option expiration date")
    
    # Order quantities
    long_quantity: int = Field(..., gt=0, description="Number of long call contracts")
    short_quantity: int = Field(..., gt=0, description="Number of short call contracts")
    
    # Order execution details
    order_type: OrderType = Field(default=OrderType.LIMIT, description="Order type")
    time_in_force: TimeInForce = Field(default=TimeInForce.DAY, description="Time in force")
    
    # Pricing (optional for market orders)
    long_limit_price: Optional[Decimal] = Field(default=None, ge=0, description="Limit price for long call")
    short_limit_price: Optional[Decimal] = Field(default=None, ge=0, description="Limit price for short call")
    
    # Risk metrics
    net_debit: Decimal = Field(..., ge=0, description="Net debit for the spread")
    max_risk: Decimal = Field(..., ge=0, description="Maximum risk (should equal net debit)")
    max_profit: Decimal = Field(..., ge=0, description="Maximum profit potential")
    
    # Broker and formatting
    broker_format: BrokerFormat = Field(default=BrokerFormat.INTERACTIVE_BROKERS, description="Target broker format")
    
    # Account and risk management
    account_size: Decimal = Field(..., gt=0, description="Total account size")
    buying_power_used_pct: Decimal = Field(..., ge=0, le=0.05, description="Percentage of buying power used")
    total_cost: Decimal = Field(default=Decimal("0"), ge=0, description="Total cost of the position")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="Order ticket creation timestamp")
    
    @field_validator('expiration_date')
    @classmethod
    def validate_expiration_date(cls, v: date) -> date:
        """Validate that expiration date is not in the past."""
        if v < date.today():
            raise ValueError("expiration_date cannot be in the past")
        return v
    
    @model_validator(mode='after')
    def validate_spread_configuration(self) -> 'OrderTicket':
        """Validate the overall spread configuration."""
        # Bull call spread: long strike must be less than short strike
        if self.long_strike >= self.short_strike:
            raise ValueError("long_strike must be less than short_strike for bull call spreads")
        
        # Quantities must match for spreads
        if self.long_quantity != self.short_quantity:
            raise ValueError("long_quantity must equal short_quantity for spreads")
        
        # Max risk should not exceed net debit for spreads
        if self.max_risk > self.net_debit:
            raise ValueError("max_risk cannot exceed net_debit for spreads")
        
        # If limit prices are provided, validate net debit calculation
        if self.long_limit_price is not None and self.short_limit_price is not None:
            calculated_debit = self.long_limit_price - self.short_limit_price
            if abs(calculated_debit - self.net_debit) > Decimal('0.01'):
                raise ValueError("net_debit must equal long_limit_price minus short_limit_price")
        
        return self
    
    def __str__(self) -> str:
        """String representation for logging and debugging."""
        return (
            f"OrderTicket({self.recommendation_id}: {self.symbol} "
            f"{self.long_strike}/{self.short_strike} x{self.long_quantity} "
            f"for ${self.net_debit})"
        )


class ExecutionValidationResult(BaseModel):
    """Result of order validation checks."""
    
    is_valid: bool = Field(..., description="Whether the order passes all validations")
    errors: list[str] = Field(default_factory=list, description="List of validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of validation warnings")
    
    # Market condition checks
    market_open: bool = Field(..., description="Whether market is currently open")
    liquidity_sufficient: bool = Field(..., description="Whether options have sufficient liquidity")
    
    # Risk checks
    position_size_valid: bool = Field(..., description="Whether position size is within limits")
    risk_reward_valid: bool = Field(..., description="Whether risk/reward ratio is acceptable")
    
    # Pricing checks
    pricing_current: bool = Field(..., description="Whether pricing data is current")
    spread_valid: bool = Field(..., description="Whether spread configuration is valid")


class ExecutionRequest(BaseModel):
    """Request model for order execution preparation."""
    
    recommendation_id: str = Field(..., description="ID of recommendation to execute")
    broker_format: BrokerFormat = Field(default=BrokerFormat.INTERACTIVE_BROKERS, description="Target broker format")
    order_type: OrderType = Field(default=OrderType.LIMIT, description="Order type preference")
    time_in_force: TimeInForce = Field(default=TimeInForce.DAY, description="Time in force preference")
    
    # Optional overrides
    custom_quantity: Optional[int] = Field(default=None, gt=0, description="Override recommended quantity")
    custom_limit_adjustment: Optional[Decimal] = Field(default=None, description="Adjustment to limit prices")


class ExecutionResponse(BaseModel):
    """Response model for order execution preparation."""
    
    order_ticket: OrderTicket = Field(..., description="Generated order ticket")
    validation_result: ExecutionValidationResult = Field(..., description="Validation results")
    formatted_order: str = Field(..., description="Broker-formatted order text")
    execution_checklist: list[str] = Field(..., description="Step-by-step execution guidance")
    
    # Additional metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="Response generation timestamp")
    expires_at: datetime = Field(..., description="When this order preparation expires")


class BrokerFormatInfo(BaseModel):
    """Information about a supported broker format."""
    
    format_code: BrokerFormat = Field(..., description="Broker format enum value")
    display_name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="Description of format characteristics")
    order_fields: list[str] = Field(..., description="Fields included in order format")
    sample_order: str = Field(..., description="Sample formatted order text")