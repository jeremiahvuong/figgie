"""
Trading strategies for the Figgie algorithmic trading game.

This module contains various algorithmic trading strategies that can be used
by players in the Figgie game simulation.
"""

import random
from typing import Dict, Optional

from base_strategy import TradingStrategy
from game_types import Suit
from main import GameState, Order, Player


class RandomStrategy(TradingStrategy):
    """Randomly places bids and asks"""
    
    def __init__(self, action_probability: float = 0.3):
        self.action_probability = action_probability
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        if random.random() > self.action_probability:
            return None
            
        # Randomly choose a suit and action
        suit = random.choice(list(Suit))
        side = random.choice(["bid", "ask"])
        
        if side == "ask" and player.inventory[suit] == 0:
            return None  # Can't sell what we don't have
            
        # Generate a reasonable price based on current market
        current_bid = game_state.orderbook[suit.name]["bid"]["price"]
        current_ask = game_state.orderbook[suit.name]["ask"]["price"]
        
        if side == "bid":
            # Bid slightly higher than current bid
            if current_bid == -999:
                price = random.randint(1, 15)
            else:
                price = min(current_bid + random.randint(1, 3), player.dollars)
        else:  # ask
            # Ask slightly lower than current ask
            if current_ask == 999:
                price = random.randint(5, 20)
            else:
                price = max(current_ask - random.randint(1, 3), 1)
        
        return Order(suit, side, price, player)
    
    def get_strategy_name(self) -> str:
        return "Random"
    
    def get_thinking_time(self) -> float:
        """Random strategy acts quickly with minimal thinking"""
        return random.uniform(0.2, 1.5)


class ConservativeStrategy(TradingStrategy):
    """Conservative strategy that focuses on accumulating the goal suit when known"""
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # If we know the goal suit, focus on it
        if game_state.goal_suit:
            return self._trade_goal_suit(game_state, player)
        
        # Otherwise, try to infer the goal suit and trade conservatively
        return self._conservative_trade(game_state, player)
    
    def _trade_goal_suit(self, game_state: GameState, player: Player) -> Optional[Order]:
        goal_suit = game_state.goal_suit
        if not goal_suit:
            return None
            
        current_bid = game_state.orderbook[goal_suit.name]["bid"]["price"]
        current_ask = game_state.orderbook[goal_suit.name]["ask"]["price"]
        
        # Try to buy goal suit if price is reasonable
        if current_ask != 999 and current_ask <= 15 and player.dollars >= current_ask:
            return Order(goal_suit, "bid", current_ask, player)
        
        # Place a conservative bid for goal suit
        if current_bid == -999 or current_bid < 10:
            bid_price = min(10, player.dollars)
            return Order(goal_suit, "bid", bid_price, player)
        
        return None
    
    def _conservative_trade(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Look for suits we have many of to sell
        for suit, count in player.inventory.items():
            if count >= 3:  # Sell if we have 3+ of a suit
                current_ask = game_state.orderbook[suit.name]["ask"]["price"]
                if current_ask == 999:
                    return Order(suit, "ask", 12, player)
                elif current_ask > 8:
                    return Order(suit, "ask", current_ask - 1, player)
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Conservative"
    
    def get_thinking_time(self) -> float:
        """Conservative strategy takes time to carefully consider moves"""
        return random.uniform(1.5, 4.0)


class AggressiveStrategy(TradingStrategy):
    """Aggressive strategy that tries to corner markets and make quick profits"""
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Look for arbitrage opportunities
        arbitrage_order = self._find_arbitrage(game_state, player)
        if arbitrage_order:
            return arbitrage_order
        
        # Try to corner a market
        corner_order = self._corner_market(game_state, player)
        if corner_order:
            return corner_order
        
        return None
    
    def _find_arbitrage(self, game_state: GameState, player: Player) -> Optional[Order]:
        for suit in Suit:
            current_bid = game_state.orderbook[suit.name]["bid"]["price"]
            current_ask = game_state.orderbook[suit.name]["ask"]["price"]
            
            # If spread is very tight, try to take it
            if current_ask != 999 and current_bid != -999 and current_ask - current_bid <= 2:
                if player.dollars >= current_ask:
                    return Order(suit, "bid", current_ask, player)
        
        return None
    
    def _corner_market(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Try to buy up suits we already have a lot of
        for suit, count in player.inventory.items():
            if count >= 2:  # If we already have 2+, try to get more
                current_ask = game_state.orderbook[suit.name]["ask"]["price"]
                if current_ask != 999 and current_ask <= 18 and player.dollars >= current_ask:
                    return Order(suit, "bid", current_ask, player)
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Aggressive"
    
    def get_thinking_time(self) -> float:
        """Aggressive strategy acts quickly to seize opportunities"""
        return random.uniform(0.3, 1.0)


class ValueStrategy(TradingStrategy):
    """Value-based strategy that estimates fair value and trades around it"""
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Calculate expected values for each suit
        suit_values = self._calculate_suit_values(game_state)
        
        for suit in Suit:
            fair_value = suit_values[suit]
            current_bid = game_state.orderbook[suit.name]["bid"]["price"]
            current_ask = game_state.orderbook[suit.name]["ask"]["price"]
            
            # Buy if ask is below fair value
            if current_ask != 999 and current_ask < fair_value * 0.8 and player.dollars >= current_ask:
                return Order(suit, "bid", current_ask, player)
            
            # Sell if we have the suit and bid is above fair value
            if (player.inventory[suit] > 0 and current_bid != -999 and 
                current_bid > fair_value * 1.2):
                return Order(suit, "ask", current_bid, player)
            
            # Place value-based orders
            if current_bid == -999 or current_bid < fair_value * 0.9:
                bid_price = min(int(fair_value * 0.9), player.dollars)
                if bid_price > 0:
                    return Order(suit, "bid", bid_price, player)
        
        return None
    
    def _calculate_suit_values(self, game_state: GameState) -> Dict[Suit, float]:
        """Calculate expected value for each suit based on probability of being goal suit"""
        values = {}
        
        for suit in Suit:
            # Base value from potential goal suit probability
            if game_state.goal_suit:
                # We know the goal suit
                if suit == game_state.goal_suit:
                    values[suit] = 10.0  # $10 per card
                else:
                    values[suit] = 2.0   # Low value for non-goal suits
            else:
                # Estimate probability based on suit counts and color
                if game_state.suit_12 and suit.color == game_state.suit_12.color and suit != game_state.suit_12:
                    values[suit] = 8.0  # Likely goal suit
                else:
                    values[suit] = 4.0  # Could be goal suit
        
        return values
    
    def get_strategy_name(self) -> str:
        return "Value"
    
    def get_thinking_time(self) -> float:
        """Value strategy takes time to calculate fair values"""
        return random.uniform(1.0, 3.5)


class MarketMakerStrategy(TradingStrategy):
    """Market maker strategy that provides liquidity by maintaining bid-ask spreads"""
    
    def __init__(self, target_spread: int = 3, max_position: int = 4):
        self.target_spread = target_spread
        self.max_position = max_position
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Find suits where we can provide liquidity
        for suit in Suit:
            current_bid = game_state.orderbook[suit.name]["bid"]["price"]
            current_ask = game_state.orderbook[suit.name]["ask"]["price"]
            
            # Calculate mid price
            if current_bid != -999 and current_ask != 999:
                mid_price = (current_bid + current_ask) / 2
            elif current_bid != -999:
                mid_price = current_bid + 2
            elif current_ask != 999:
                mid_price = current_ask - 2
            else:
                mid_price = 10  # Default mid price
            
            # Check if we should provide liquidity
            position = player.inventory[suit]
            
            # If we have too many, try to sell
            if position >= self.max_position:
                if current_ask == 999 or current_ask > mid_price + 1:
                    return Order(suit, "ask", int(mid_price + 1), player)
            
            # If we have room to buy and spread is wide, provide bid
            elif position < self.max_position and player.dollars >= mid_price:
                if current_bid == -999 or current_bid < mid_price - 1:
                    return Order(suit, "bid", int(mid_price - 1), player)
        
        return None
    
    def get_strategy_name(self) -> str:
        return "MarketMaker"


class MomentumStrategy(TradingStrategy):
    """Momentum strategy that follows price trends"""
    
    def __init__(self, momentum_threshold: int = 3):
        self.momentum_threshold = momentum_threshold
        self.price_history: Dict[str, list[int]] = {suit.name: [] for suit in Suit}
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Update price history
        for suit in Suit:
            last_price = game_state.orderbook[suit.name]["last_traded_price"]
            if last_price > 0:
                self.price_history[suit.name].append(last_price)
                # Keep only recent history
                if len(self.price_history[suit.name]) > 5:
                    self.price_history[suit.name].pop(0)
        
        # Look for momentum opportunities
        for suit in Suit:
            history = self.price_history[suit.name]
            if len(history) >= 2:
                # Check for upward momentum
                if history[-1] > history[-2] + self.momentum_threshold:
                    current_ask = game_state.orderbook[suit.name]["ask"]["price"]
                    if current_ask != 999 and player.dollars >= current_ask:
                        return Order(suit, "bid", current_ask, player)
                
                # Check for downward momentum (sell if we have the suit)
                elif (history[-1] < history[-2] - self.momentum_threshold and 
                      player.inventory[suit] > 0):
                    current_bid = game_state.orderbook[suit.name]["bid"]["price"]
                    if current_bid != -999:
                        return Order(suit, "ask", current_bid, player)
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Momentum"


class InformationStrategy(TradingStrategy):
    """Strategy that tries to infer the goal suit from trading patterns"""
    
    def __init__(self):
        self.suit_probabilities: Dict[Suit, float] = {suit: 0.25 for suit in Suit}
        self.observation_count = 0
    
    def decide_action(self, game_state: GameState, player: Player) -> Optional[Order]:
        # Update probabilities based on observations
        self._update_probabilities(game_state)
        
        # Trade based on inferred probabilities
        return self._trade_on_information(game_state, player)
    
    def _update_probabilities(self, game_state: GameState) -> None:
        """Update suit probabilities based on market activity"""
        self.observation_count += 1
        
        # If we know the goal suit, set probabilities accordingly
        if game_state.goal_suit:
            for suit in Suit:
                if suit == game_state.goal_suit:
                    self.suit_probabilities[suit] = 1.0
                else:
                    self.suit_probabilities[suit] = 0.0
            return
        
        # Update based on trading activity and suit counts
        for suit in Suit:
            last_price = game_state.orderbook[suit.name]["last_traded_price"]
            
            # Higher prices suggest higher value (possibly goal suit)
            if last_price > 12:
                self.suit_probabilities[suit] *= 1.1
            elif last_price > 0 and last_price < 5:
                self.suit_probabilities[suit] *= 0.9
            
            # Use color information if we know the 12-card suit
            if game_state.suit_12:
                if suit.color == game_state.suit_12.color and suit != game_state.suit_12:
                    self.suit_probabilities[suit] *= 1.2
                else:
                    self.suit_probabilities[suit] *= 0.8
        
        # Normalize probabilities
        total = sum(self.suit_probabilities.values())
        if total > 0:
            for suit in Suit:
                self.suit_probabilities[suit] /= total
    
    def _trade_on_information(self, game_state: GameState, player: Player) -> Optional[Order]:
        """Trade based on inferred goal suit probabilities"""
        # Find the suit with highest probability
        best_suit = max(self.suit_probabilities.keys(), 
                       key=lambda s: self.suit_probabilities[s])
        
        if self.suit_probabilities[best_suit] > 0.4:  # High confidence
            current_ask = game_state.orderbook[best_suit.name]["ask"]["price"]
            current_bid = game_state.orderbook[best_suit.name]["bid"]["price"]
            
            # Try to buy the likely goal suit
            if current_ask != 999 and current_ask <= 15 and player.dollars >= current_ask:
                return Order(best_suit, "bid", current_ask, player)
            
            # Place a reasonable bid
            if current_bid == -999 or current_bid < 8:
                bid_price = min(8, player.dollars)
                return Order(best_suit, "bid", bid_price, player)
        
        # Sell suits with low probability if we have them
        for suit, prob in self.suit_probabilities.items():
            if prob < 0.15 and player.inventory[suit] > 0:
                current_bid = game_state.orderbook[suit.name]["bid"]["price"]
                if current_bid != -999 and current_bid >= 5:
                    return Order(suit, "ask", current_bid, player)
        
        return None
    
    def get_strategy_name(self) -> str:
        return "Information" 