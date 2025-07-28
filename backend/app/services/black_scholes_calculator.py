"""
Black-Scholes Calculator for options probability calculations.

This module implements the Black-Scholes model for calculating probability of profit
for call options, specifically optimized for SPY 0-DTE trading strategies.
"""

import math

from scipy.stats import norm


class BlackScholesCalculator:
    """
    Black-Scholes calculator for options probability analysis.

    Implements the Black-Scholes-Merton model for European call options
    with focus on probability of profit calculations for trading decisions.
    """

    def probability_of_profit(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate probability of profit for a call option.

        Args:
                spot_price: Current price of the underlying asset
                strike_price: Strike price of the option
                time_to_expiry: Time to expiry in years (e.g., 1/365 for 1 day)
                volatility: Implied volatility as decimal (e.g., 0.20 for 20%)
                risk_free_rate: Risk-free interest rate as decimal (default: 0.05)

        Returns:
                Probability of profit as decimal between 0 and 1

        Raises:
                ValueError: If any input parameter is invalid
        """
        self._validate_inputs(spot_price, strike_price, time_to_expiry, volatility)

        # Calculate d1 and d2 parameters
        d1, d2 = self._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        # Probability of profit = N(d2) for call options
        # This represents the probability that S_T > K at expiry
        probability = self._cumulative_normal(d2)

        return probability

    def _calculate_d1_d2(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float,
    ) -> tuple[float, float]:
        """
        Calculate d1 and d2 parameters for Black-Scholes formula.

        Args:
                spot_price: Current price of underlying
                strike_price: Strike price
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility
                risk_free_rate: Risk-free rate

        Returns:
                Tuple of (d1, d2) values
        """
        # d1 = [ln(S/K) + (r + σ²/2)T] / (σ√T)
        ln_s_over_k = math.log(spot_price / strike_price)
        vol_squared = volatility * volatility
        vol_sqrt_t = volatility * math.sqrt(time_to_expiry)

        d1 = (
            ln_s_over_k + (risk_free_rate + vol_squared / 2) * time_to_expiry
        ) / vol_sqrt_t

        # d2 = d1 - σ√T
        d2 = d1 - vol_sqrt_t

        return d1, d2

    def _cumulative_normal(self, z: float) -> float:
        """
        Calculate cumulative standard normal distribution N(z).

        Uses scipy.stats.norm for high accuracy.

        Args:
                z: Standard normal variable

        Returns:
                Probability that standard normal variable ≤ z
        """
        return norm.cdf(z)

    def _validate_inputs(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
    ) -> None:
        """
        Validate input parameters for Black-Scholes calculation.

        Args:
                spot_price: Current price of underlying
                strike_price: Strike price
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility

        Raises:
                ValueError: If any parameter violates mathematical constraints
        """
        if spot_price <= 0:
            raise ValueError(f"Spot price must be positive, got {spot_price}")

        if strike_price <= 0:
            raise ValueError(f"Strike price must be positive, got {strike_price}")

        if time_to_expiry <= 0:
            raise ValueError(f"Time to expiry must be positive, got {time_to_expiry}")

        if volatility <= 0:
            raise ValueError(f"Volatility must be positive, got {volatility}")

    def option_price(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate theoretical call option price using Black-Scholes formula.

        This method is provided for completeness but the main focus is on
        probability calculations for trading decisions.

        Args:
                spot_price: Current price of the underlying asset
                strike_price: Strike price of the option
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility as decimal
                risk_free_rate: Risk-free interest rate as decimal

        Returns:
                Theoretical call option price
        """
        self._validate_inputs(spot_price, strike_price, time_to_expiry, volatility)

        d1, d2 = self._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        # Call price = S*N(d1) - K*e^(-rT)*N(d2)
        discount_factor = math.exp(-risk_free_rate * time_to_expiry)

        call_price = spot_price * self._cumulative_normal(
            d1
        ) - strike_price * discount_factor * self._cumulative_normal(d2)

        return max(call_price, 0.0)  # Option price cannot be negative

    def delta(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate delta (price sensitivity to underlying price changes).

        Args:
                spot_price: Current price of the underlying asset
                strike_price: Strike price of the option
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility as decimal
                risk_free_rate: Risk-free interest rate as decimal

        Returns:
                Delta value (between 0 and 1 for call options)
        """
        self._validate_inputs(spot_price, strike_price, time_to_expiry, volatility)

        d1, _ = self._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        return self._cumulative_normal(d1)

    def gamma(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate gamma (rate of change of delta).

        Args:
                spot_price: Current price of the underlying asset
                strike_price: Strike price of the option
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility as decimal
                risk_free_rate: Risk-free interest rate as decimal

        Returns:
                Gamma value
        """
        self._validate_inputs(spot_price, strike_price, time_to_expiry, volatility)

        d1, _ = self._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        # γ = φ(d1) / (S * σ * √T)
        phi_d1 = norm.pdf(d1)  # Standard normal PDF
        gamma_value = phi_d1 / (spot_price * volatility * math.sqrt(time_to_expiry))

        return gamma_value

    def theta(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry: float,
        volatility: float,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate theta (time decay).

        Args:
                spot_price: Current price of the underlying asset
                strike_price: Strike price of the option
                time_to_expiry: Time to expiry in years
                volatility: Implied volatility as decimal
                risk_free_rate: Risk-free interest rate as decimal

        Returns:
                Theta value (typically negative for long options)
        """
        self._validate_inputs(spot_price, strike_price, time_to_expiry, volatility)

        d1, d2 = self._calculate_d1_d2(
            spot_price, strike_price, time_to_expiry, volatility, risk_free_rate
        )

        sqrt_t = math.sqrt(time_to_expiry)
        phi_d1 = norm.pdf(d1)
        n_d2 = self._cumulative_normal(d2)

        # θ = -(S*φ(d1)*σ)/(2√T) - r*K*e^(-rT)*N(d2)
        theta_value = (
            -(spot_price * phi_d1 * volatility) / (2 * sqrt_t)
            - risk_free_rate
            * strike_price
            * math.exp(-risk_free_rate * time_to_expiry)
            * n_d2
        )

        return theta_value / 365  # Convert to per-day theta
