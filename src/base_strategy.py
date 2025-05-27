"""
Base classes for trading strategies in the Figgie game.

This module contains the abstract base class that all trading strategies
must inherit from.
"""

import random
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from main import GameState, Order, Player


class TradingStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    @abstractmethod
    def decide_action(self, game_state: 'GameState', player: 'Player') -> Optional['Order']:
        """
        Given the current game state, decide what action to take.
        Returns an Order if the strategy wants to place one, None otherwise.
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Return the name of this strategy"""
        pass
    
    def get_thinking_time(self) -> float:
        """
        Return the thinking time for this strategy in seconds.
        Different strategies can have different thinking patterns.
        """
        # Default thinking time: 0.5 to 3 seconds
        return random.uniform(0.5, 3.0) 