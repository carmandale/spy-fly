"""
Spread Generator for creating bull-call-spread combinations.

This module generates and filters all possible bull-call-spread combinations
from a given options chain using vectorized operations for performance.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class SpreadCombination:
	"""Data structure representing a bull-call-spread combination."""
	
	# Strike prices
	long_strike: float
	short_strike: float
	spread_width: float
	
	# Pricing
	long_bid: float
	long_ask: float
	long_mid: float
	short_bid: float
	short_ask: float  
	short_mid: float
	net_debit: float
	
	# Risk metrics
	max_risk: float
	max_profit: float
	risk_reward_ratio: float
	breakeven: float
	
	# Liquidity metrics
	long_volume: int
	short_volume: int
	long_liquidity_score: float
	short_liquidity_score: float
	combined_liquidity_score: float
	
	def to_dict(self) -> Dict[str, Any]:
		"""Convert to dictionary for serialization."""
		return {
			'long_strike': self.long_strike,
			'short_strike': self.short_strike,
			'spread_width': self.spread_width,
			'long_bid': self.long_bid,
			'long_ask': self.long_ask,
			'long_mid': self.long_mid,
			'short_bid': self.short_bid,
			'short_ask': self.short_ask,
			'short_mid': self.short_mid,
			'net_debit': self.net_debit,
			'max_risk': self.max_risk,
			'max_profit': self.max_profit,
			'risk_reward_ratio': self.risk_reward_ratio,
			'breakeven': self.breakeven,
			'long_volume': self.long_volume,
			'short_volume': self.short_volume,
			'long_liquidity_score': self.long_liquidity_score,
			'short_liquidity_score': self.short_liquidity_score,
			'combined_liquidity_score': self.combined_liquidity_score
		}


class SpreadGenerator:
	"""
	Generate and analyze bull-call-spread combinations.
	
	This class creates all possible bull-call-spread combinations from
	an options chain and provides filtering and analysis capabilities.
	"""
	
	def __init__(self):
		"""Initialize the spread generator."""
		pass
		
	def generate_spreads(
		self,
		options_df: pd.DataFrame,
		skip_invalid: bool = True
	) -> List[SpreadCombination]:
		"""
		Generate all possible bull-call-spread combinations.
		
		Args:
			options_df: DataFrame with option data (must include strike, bid, ask, etc.)
			skip_invalid: Skip spreads with invalid pricing data
			
		Returns:
			List of SpreadCombination objects
		"""
		spreads = []
		
		# Iterate through all combinations where long strike < short strike
		for i in range(len(options_df)):
			long_option = options_df.iloc[i]
			
			# Skip if invalid data and skip_invalid is True
			if skip_invalid and (long_option['bid'] <= 0 or long_option['ask'] <= 0):
				continue
				
			for j in range(i + 1, len(options_df)):
				short_option = options_df.iloc[j]
				
				# Skip if invalid data
				if skip_invalid and (short_option['bid'] <= 0 or short_option['ask'] <= 0):
					continue
					
				# Create spread combination
				spread = self._create_spread_combination(long_option, short_option)
				
				# Only add valid spreads (positive net debit, positive max profit)
				if spread.net_debit > 0 and spread.max_profit > 0:
					spreads.append(spread)
					
		return spreads
	
	def generate_spreads_vectorized(
		self,
		options_df: pd.DataFrame
	) -> List[SpreadCombination]:
		"""
		Generate spreads using vectorized operations for better performance.
		
		Args:
			options_df: DataFrame with option data
			
		Returns:
			List of SpreadCombination objects
		"""
		n = len(options_df)
		if n < 2:
			return []
			
		# Create index arrays for all combinations
		long_idx, short_idx = np.meshgrid(range(n), range(n), indexing='ij')
		
		# Filter for long strike < short strike
		mask = long_idx < short_idx
		long_indices = long_idx[mask]
		short_indices = short_idx[mask]
		
		# Vectorized data extraction
		long_strikes = options_df['strike'].values[long_indices]
		short_strikes = options_df['strike'].values[short_indices]
		
		long_bids = options_df['bid'].values[long_indices]
		long_asks = options_df['ask'].values[long_indices]
		long_mids = options_df['mid'].values[long_indices]
		
		short_bids = options_df['bid'].values[short_indices]
		short_asks = options_df['ask'].values[short_indices]
		short_mids = options_df['mid'].values[short_indices]
		
		# Vectorized calculations
		spread_widths = short_strikes - long_strikes
		net_debits = long_mids - short_mids
		max_risks = net_debits
		max_profits = spread_widths - net_debits
		risk_reward_ratios = np.divide(
			max_profits,
			max_risks,
			out=np.zeros_like(max_profits),
			where=max_risks > 0
		)
		breakevens = long_strikes + net_debits
		
		# Liquidity data
		long_volumes = options_df['volume'].values[long_indices]
		short_volumes = options_df['volume'].values[short_indices]
		long_liquidity_scores = options_df['liquidity_score'].values[long_indices]
		short_liquidity_scores = options_df['liquidity_score'].values[short_indices]
		combined_liquidity_scores = (long_liquidity_scores + short_liquidity_scores) / 2
		
		# Filter valid spreads
		valid_mask = (net_debits > 0) & (max_profits > 0)
		
		# Create SpreadCombination objects
		spreads = []
		valid_indices = np.where(valid_mask)[0]
		
		for idx in valid_indices:
			spread = SpreadCombination(
				long_strike=float(long_strikes[idx]),
				short_strike=float(short_strikes[idx]),
				spread_width=float(spread_widths[idx]),
				long_bid=float(long_bids[idx]),
				long_ask=float(long_asks[idx]),
				long_mid=float(long_mids[idx]),
				short_bid=float(short_bids[idx]),
				short_ask=float(short_asks[idx]),
				short_mid=float(short_mids[idx]),
				net_debit=float(net_debits[idx]),
				max_risk=float(max_risks[idx]),
				max_profit=float(max_profits[idx]),
				risk_reward_ratio=float(risk_reward_ratios[idx]),
				breakeven=float(breakevens[idx]),
				long_volume=int(long_volumes[idx]),
				short_volume=int(short_volumes[idx]),
				long_liquidity_score=float(long_liquidity_scores[idx]),
				short_liquidity_score=float(short_liquidity_scores[idx]),
				combined_liquidity_score=float(combined_liquidity_scores[idx])
			)
			spreads.append(spread)
			
		return spreads
	
	def filter_by_risk_reward(
		self,
		spreads: List[SpreadCombination],
		min_ratio: float = 1.0
	) -> List[SpreadCombination]:
		"""
		Filter spreads by minimum risk/reward ratio.
		
		Args:
			spreads: List of spread combinations
			min_ratio: Minimum acceptable risk/reward ratio
			
		Returns:
			Filtered list of spreads
		"""
		return [s for s in spreads if s.risk_reward_ratio >= min_ratio]
	
	def filter_by_width(
		self,
		spreads: List[SpreadCombination],
		min_width: float = 1.0,
		max_width: float = 50.0
	) -> List[SpreadCombination]:
		"""
		Filter spreads by strike width.
		
		Args:
			spreads: List of spread combinations
			min_width: Minimum spread width
			max_width: Maximum spread width
			
		Returns:
			Filtered list of spreads
		"""
		return [s for s in spreads if min_width <= s.spread_width <= max_width]
	
	def filter_by_liquidity(
		self,
		spreads: List[SpreadCombination],
		options_df: pd.DataFrame,
		min_liquidity_score: float = 50.0,
		min_volume: Optional[int] = None
	) -> List[SpreadCombination]:
		"""
		Filter spreads by liquidity requirements.
		
		Args:
			spreads: List of spread combinations
			options_df: Original options DataFrame (for additional checks)
			min_liquidity_score: Minimum liquidity score for both legs
			min_volume: Minimum volume for both legs (optional)
			
		Returns:
			Filtered list of spreads
		"""
		filtered = []
		
		for spread in spreads:
			# Check liquidity scores
			if (spread.long_liquidity_score < min_liquidity_score or
				spread.short_liquidity_score < min_liquidity_score):
				continue
				
			# Check volume if specified
			if min_volume is not None:
				if spread.long_volume < min_volume or spread.short_volume < min_volume:
					continue
					
			filtered.append(spread)
			
		return filtered
	
	def calculate_position_size(
		self,
		spread: SpreadCombination,
		account_size: float,
		max_risk_pct: float = 0.05
	) -> Dict[str, Any]:
		"""
		Calculate appropriate position size based on account and risk limits.
		
		Args:
			spread: Spread combination
			account_size: Total account size
			max_risk_pct: Maximum percentage of account to risk
			
		Returns:
			Dictionary with position sizing details
		"""
		max_dollar_risk = account_size * max_risk_pct
		cost_per_contract = spread.net_debit * 100  # Options are per 100 shares
		
		# Calculate maximum contracts based on risk limit
		max_contracts = int(max_dollar_risk / cost_per_contract)
		contracts = max(1, max_contracts)  # At least 1 contract
		
		total_cost = contracts * cost_per_contract
		actual_risk_pct = total_cost / account_size
		
		return {
			'contracts': contracts,
			'total_cost': total_cost,
			'risk_pct': actual_risk_pct,
			'max_loss': total_cost,
			'max_gain': contracts * spread.max_profit * 100
		}
	
	def sort_spreads(
		self,
		spreads: List[SpreadCombination],
		sort_by: str = 'risk_reward_ratio',
		descending: bool = True
	) -> List[SpreadCombination]:
		"""
		Sort spreads by specified attribute.
		
		Args:
			spreads: List of spread combinations
			sort_by: Attribute name to sort by
			descending: Sort in descending order
			
		Returns:
			Sorted list of spreads
		"""
		return sorted(
			spreads,
			key=lambda s: getattr(s, sort_by),
			reverse=descending
		)
	
	def generate_filtered_spreads(
		self,
		options_df: pd.DataFrame,
		config: Optional[Dict[str, Any]] = None
	) -> List[SpreadCombination]:
		"""
		Generate spreads with all filters applied.
		
		Args:
			options_df: DataFrame with option data
			config: Configuration dictionary with filter parameters
			
		Returns:
			Filtered and sorted list of spreads
		"""
		# Default configuration
		default_config = {
			'min_risk_reward_ratio': 1.0,
			'min_spread_width': 1.0,
			'max_spread_width': 50.0,
			'min_liquidity_score': 50.0,
			'sort_by': 'risk_reward_ratio',
			'use_vectorized': True
		}
		
		if config:
			default_config.update(config)
			
		# Generate spreads
		if default_config['use_vectorized'] and len(options_df) > 10:
			spreads = self.generate_spreads_vectorized(options_df)
		else:
			spreads = self.generate_spreads(options_df)
			
		# Apply filters
		spreads = self.filter_by_risk_reward(
			spreads,
			min_ratio=default_config['min_risk_reward_ratio']
		)
		
		spreads = self.filter_by_width(
			spreads,
			min_width=default_config['min_spread_width'],
			max_width=default_config['max_spread_width']
		)
		
		spreads = self.filter_by_liquidity(
			spreads,
			options_df,
			min_liquidity_score=default_config['min_liquidity_score']
		)
		
		# Sort by preferred metric
		spreads = self.sort_spreads(
			spreads,
			sort_by=default_config['sort_by'],
			descending=True
		)
		
		return spreads
	
	def _create_spread_combination(
		self,
		long_option: pd.Series,
		short_option: pd.Series
	) -> SpreadCombination:
		"""Create a SpreadCombination from two option rows."""
		spread_width = short_option['strike'] - long_option['strike']
		net_debit = long_option['mid'] - short_option['mid']
		max_risk = net_debit
		max_profit = spread_width - net_debit
		
		# Calculate risk/reward ratio safely
		if max_risk > 0:
			risk_reward_ratio = max_profit / max_risk
		else:
			risk_reward_ratio = 0.0
			
		breakeven = long_option['strike'] + net_debit
		
		# Combined liquidity score (average of both legs)
		combined_liquidity = (
			long_option.get('liquidity_score', 50) + 
			short_option.get('liquidity_score', 50)
		) / 2
		
		return SpreadCombination(
			long_strike=float(long_option['strike']),
			short_strike=float(short_option['strike']),
			spread_width=float(spread_width),
			long_bid=float(long_option['bid']),
			long_ask=float(long_option['ask']),
			long_mid=float(long_option['mid']),
			short_bid=float(short_option['bid']),
			short_ask=float(short_option['ask']),
			short_mid=float(short_option['mid']),
			net_debit=float(net_debit),
			max_risk=float(max_risk),
			max_profit=float(max_profit),
			risk_reward_ratio=float(risk_reward_ratio),
			breakeven=float(breakeven),
			long_volume=int(long_option.get('volume', 0)),
			short_volume=int(short_option.get('volume', 0)),
			long_liquidity_score=float(long_option.get('liquidity_score', 50)),
			short_liquidity_score=float(short_option.get('liquidity_score', 50)),
			combined_liquidity_score=float(combined_liquidity)
		)