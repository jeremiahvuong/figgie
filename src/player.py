from typing import TYPE_CHECKING, Any, Dict, Optional
from custom_types import Suit

if TYPE_CHECKING:
    import asyncio
    from event import Event
    from order import Order
    from strategy import Strategy


class Player:
    def __init__(self, strategy: 'Strategy') -> None:
        self.strategy: Strategy = strategy
        self.name = strategy.name

        # Player attributes
        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Initialize empty inventory

        # Player queues
        self.event_queue: Optional[asyncio.Queue[Event]] = None
        self.order_queue: Optional[asyncio.Queue[Order]] = None

    # Methods for strategy to interact with (place orders, check state)
    # These will now interact with the async queues
    async def decide_action(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # This method will be called by the player's async task
        # It should use self.strategy to determine the action
        return None # temp
    
    # Method for the simulation to pass the game state to the player's strategy
    def update_strategy_state(self, game_state: Dict[str, Any]) -> None:
        if self.strategy and hasattr(self.strategy, 'update_state'):
            self.strategy.update_state(game_state)