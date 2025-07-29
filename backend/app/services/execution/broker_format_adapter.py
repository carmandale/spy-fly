"""
Broker Format Adapter service for formatting order tickets.

This service converts OrderTicket objects into broker-specific formatted
strings that can be copied and pasted into trading platforms.
"""

from typing import List

from app.models.execution import (
    OrderTicket,
    BrokerFormat,
    BrokerFormatInfo,
    OrderType,
    TimeInForce,
)


class BrokerFormatAdapter:
    """Service for formatting order tickets for different broker platforms."""

    def format_order(self, order_ticket: OrderTicket) -> str:
        """
        Format an order ticket for the specified broker.
        
        Args:
            order_ticket: The order ticket to format
            
        Returns:
            Formatted order string ready for broker platform
        """
        format_method = {
            BrokerFormat.INTERACTIVE_BROKERS: self._format_interactive_brokers,
            BrokerFormat.TD_AMERITRADE: self._format_td_ameritrade,
            BrokerFormat.ETRADE: self._format_etrade,
            BrokerFormat.SCHWAB: self._format_schwab,
            BrokerFormat.GENERIC: self._format_generic,
        }
        
        formatter = format_method.get(order_ticket.broker_format)
        if not formatter:
            raise ValueError(f"Unsupported broker format: {order_ticket.broker_format}")
        
        return formatter(order_ticket)

    def _format_interactive_brokers(self, order: OrderTicket) -> str:
        """Format order for Interactive Brokers TWS."""
        expiration = order.expiration_date.strftime("%Y%m%d")
        
        # IB format for options spreads
        long_symbol = f"{order.symbol}   {expiration}C{order.long_strike:08.0f}"
        short_symbol = f"{order.symbol}   {expiration}C{order.short_strike:08.0f}"
        
        order_type_str = "LMT" if order.order_type == OrderType.LIMIT else "MKT"
        tif_str = order.time_in_force.value.upper()
        
        lines = [
            "# Interactive Brokers Order Entry",
            f"Symbol: {order.symbol} Bull Call Spread",
            f"",
            f"Leg 1 - BUY {order.long_quantity} {long_symbol}",
            f"Order Type: {order_type_str}",
        ]
        
        if order.long_limit_price:
            lines.append(f"Limit Price: ${order.long_limit_price:.4f}")
        
        lines.extend([
            f"",
            f"Leg 2 - SELL {order.short_quantity} {short_symbol}",
            f"Order Type: {order_type_str}",
        ])
        
        if order.short_limit_price:
            lines.append(f"Limit Price: ${order.short_limit_price:.4f}")
        
        lines.extend([
            f"",
            f"Net Debit: ${order.net_debit:.4f}",
            f"Time in Force: {tif_str}",
            f"Max Risk: ${order.max_risk:.2f}",
            f"Max Profit: ${order.max_profit:.2f}",
        ])
        
        return "\n".join(lines)

    def _format_td_ameritrade(self, order: OrderTicket) -> str:
        """Format order for TD Ameritrade."""
        expiration = order.expiration_date.strftime("%m/%d/%Y")
        
        order_type_str = "LIMIT" if order.order_type == OrderType.LIMIT else "MARKET"
        
        lines = [
            "# TD Ameritrade Order Entry",
            f"Strategy: Bull Call Spread",
            f"Symbol: {order.symbol}",
            f"Expiration: {expiration}",
            f"",
            f"BUY {order.long_quantity} {order.symbol} ${order.long_strike} CALL",
        ]
        
        if order.long_limit_price:
            lines.append(f"  @ ${order.long_limit_price:.4f}")
        
        lines.append(f"SELL {order.short_quantity} {order.symbol} ${order.short_strike} CALL")
        
        if order.short_limit_price:
            lines.append(f"  @ ${order.short_limit_price:.4f}")
        
        lines.extend([
            f"",
            f"Order Type: {order_type_str}",
            f"Net Debit: ${order.net_debit:.4f}",
            f"Duration: {order.time_in_force.value.upper()}",
        ])
        
        return "\n".join(lines)

    def _format_etrade(self, order: OrderTicket) -> str:
        """Format order for E*TRADE."""
        expiration = order.expiration_date.strftime("%m/%d/%Y")
        
        lines = [
            "# E*TRADE Order Entry",
            f"Spread Type: Bull Call",
            f"Underlying: {order.symbol}",
            f"Expiration: {expiration}",
            f"Quantity: {order.long_quantity}",
            f"",
            f"BUY {order.long_quantity} ${order.long_strike} Call",
            f"SELL {order.short_quantity} ${order.short_strike} Call",
            f"",
        ]
        
        if order.order_type == OrderType.LIMIT:
            lines.append(f"Order Type: Limit")
            lines.append(f"Net Debit: ${order.net_debit:.4f}")
        else:
            lines.append(f"Order Type: Market")
        
        lines.append(f"Time in Force: {order.time_in_force.value.upper()}")
        
        return "\n".join(lines)

    def _format_schwab(self, order: OrderTicket) -> str:
        """Format order for Charles Schwab."""
        expiration = order.expiration_date.strftime("%m/%d/%Y")
        
        lines = [
            "# Charles Schwab Order Entry",
            f"Strategy: Bull Call Spread",
            f"Symbol: {order.symbol}",
            f"Exp Date: {expiration}",
            f"Contracts: {order.long_quantity}",
            f"",
            f"BUY TO OPEN {order.symbol} ${order.long_strike} Call",
            f"SELL TO OPEN {order.symbol} ${order.short_strike} Call",
            f"",
        ]
        
        if order.order_type == OrderType.LIMIT:
            lines.extend([
                f"Order Type: Limit",
                f"Net Debit: ${order.net_debit:.4f}",
            ])
        else:
            lines.append("Order Type: Market")
        
        lines.append(f"Time in Force: {order.time_in_force.value.upper()}")
        
        return "\n".join(lines)

    def _format_generic(self, order: OrderTicket) -> str:
        """Format order in generic, human-readable format."""
        expiration = order.expiration_date.strftime("%B %d, %Y")
        
        lines = [
            "# Bull Call Spread Order Details",
            f"",
            f"Symbol: {order.symbol}",
            f"Strategy: Bull Call Spread",
            f"Expiration: {expiration}",
            f"Quantity: {order.long_quantity} contracts",
            f"",
            f"Long Position:",
            f"  BUY {order.long_quantity} {order.symbol} ${order.long_strike} Call",
        ]
        
        if order.long_limit_price:
            lines.append(f"  Limit Price: ${order.long_limit_price:.4f}")
        
        lines.extend([
            f"",
            f"Short Position:",
            f"  SELL {order.short_quantity} {order.symbol} ${order.short_strike} Call",
        ])
        
        if order.short_limit_price:
            lines.append(f"  Limit Price: ${order.short_limit_price:.4f}")
        
        lines.extend([
            f"",
            f"Order Details:",
            f"  Order Type: {order.order_type.value.title()}",
            f"  Time in Force: {order.time_in_force.value.upper()}",
            f"  Net Debit: ${order.net_debit:.4f}",
            f"",
            f"Risk Analysis:",
            f"  Max Risk: ${order.max_risk:.2f}",
            f"  Max Profit: ${order.max_profit:.2f}",
            f"  Risk/Reward: {order.max_profit/order.max_risk:.2f}:1" if order.max_risk > 0 else "  Risk/Reward: N/A",
            f"  Breakeven: ${order.long_strike + order.net_debit:.2f}",
        ])
        
        return "\n".join(lines)

    def get_supported_formats(self) -> List[BrokerFormatInfo]:
        """Get list of all supported broker formats with details."""
        formats = []
        
        for broker_format in BrokerFormat:
            format_info = self.get_format_info(broker_format)
            formats.append(format_info)
        
        return formats

    def get_format_info(self, broker_format: BrokerFormat) -> BrokerFormatInfo:
        """Get detailed information about a specific broker format."""
        format_details = {
            BrokerFormat.INTERACTIVE_BROKERS: {
                "description": "Optimized for Interactive Brokers TWS platform with precise option symbols",
                "order_fields": [
                    "Option symbols with expiration codes",
                    "Limit prices for each leg",
                    "Net debit calculation",
                    "Time in force specifications"
                ],
                "sample": "BUY 2 SPY   20250729C00470000\nLIMIT $6.05\nSELL 2 SPY   20250729C00472000\nLIMIT $4.25"
            },
            BrokerFormat.TD_AMERITRADE: {
                "description": "Compatible with TD Ameritrade's options trading interface",
                "order_fields": [
                    "Strategy type identification", 
                    "Strike prices and expiration",
                    "Individual leg pricing",
                    "Duration settings"
                ],
                "sample": "BUY 2 SPY $470 CALL @ $6.05\nSELL 2 SPY $472 CALL @ $4.25\nNet Debit: $1.80"
            },
            BrokerFormat.ETRADE: {
                "description": "Formatted for E*TRADE's spread order entry system",
                "order_fields": [
                    "Spread type specification",
                    "Strike and expiration details", 
                    "Quantity and pricing",
                    "Order type selection"
                ],
                "sample": "Bull Call Spread\nSPY 07/29/2025\nLong: $470, Short: $472\nNet Debit: $1.80"
            },
            BrokerFormat.SCHWAB: {
                "description": "Optimized for Charles Schwab's trading platform",
                "order_fields": [
                    "Strategy identification",
                    "BTO/STO leg specifications",
                    "Contract quantities",
                    "Order execution details"
                ],
                "sample": "BUY TO OPEN SPY $470 Call\nSELL TO OPEN SPY $472 Call\nLimit Order: $1.80 Debit"
            },
            BrokerFormat.GENERIC: {
                "description": "Human-readable format with complete trade analysis",
                "order_fields": [
                    "Complete trade description",
                    "Risk and reward analysis",
                    "Breakeven calculations",
                    "Educational information"
                ],
                "sample": "Bull Call Spread: BUY SPY $470, SELL SPY $472\nMax Risk: $1.80, Max Profit: $0.20\nBreakeven: $471.80"
            }
        }
        
        details = format_details[broker_format]
        
        return BrokerFormatInfo(
            format_code=broker_format,
            display_name=broker_format.display_name,
            description=details["description"],
            order_fields=details["order_fields"],
            sample_order=details["sample"]
        )