import asyncio
from abc import ABC, abstractmethod
import random
from typing import Any, Dict, Optional, TYPE_CHECKING

from custom_types import Suit
from event import GameStateChangedEvent
from order import Order

if TYPE_CHECKING:
    from event import EventBus
    from player import Player


class Strategy(ABC):
    def __init__(self, name: str):
        self.name = name

        self._running = False

    @abstractmethod
    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"]):
        """
        The main asynchronous method for the strategy's logic.
        Runs within an asyncio task.
        """
        pass

    def stop(self):
        """Signal the strategy to stop its execution loop."""
        self._running = False

    # Optional: Method to update strategy's internal state from game state events
    def update_state(self, game_state: Dict[str, Any]):
        """Update the strategy's internal representation of the game state."""
        # This is where the strategy can process GameStateChangedEvent data
        # and update its understanding of the game.
        pass

    # Optional: Method for strategy to decide an action based on its logic
    # This might be called internally within the start loop or by the player object
    @abstractmethod
    async def decide_order(self) -> Optional["Order"]:
        """
        Decide on an action (e.g., an order) based on the current state.
        Returns an Order object, or None if no order.
        """
        pass

# Note: Circular dependency Player <-> Strategy.
# Use forward references ('Player') or type checking imports if needed.
# For simplicity, I'm using string forward references here.

"""
Strategy implementations
"""
class RandomStrategy(Strategy):
    def __init__(self, name: str):
        super().__init__(name)

        # Strategy attributes
        self._player: Optional["Player"] = None
        self._event_bus: Optional["EventBus"] = None
        self._order_queue: Optional[asyncio.Queue["Order"]] = None

        self.interval = random.uniform(0.5, 1.5) # interval in seconds between deciding orders

    # The main trading loop
    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"]):
        """
        Randomly places bid/ask orders depending on the player's inventory and spread.
        """
        self._player = player
        self._event_bus = event_bus
        self._order_queue = order_queue

        self._running = True

        # Guard clauses
        if not self._player or not self._event_bus or not self._order_queue or not self._player.event_queue:
            raise ValueError("Player, player event queue, event bus, and order queue must be instantiated.")

        # Subscribe to the game state changed event
        await self._event_bus.subscribe(GameStateChangedEvent, self._player.event_queue)

        while self._running:
            try:
                await asyncio.sleep(self.interval) # Wait for interval seconds
                order = await self.decide_order()
                if order:
                    await self._order_queue.put(order)
            except asyncio.CancelledError:
                print(f"Strategy for {self._player.name} (Generic) cancelled.")
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s Generic strategy: {e}")

    async def decide_order(self) -> Optional["Order"]:
        # Guard clauses
        if not self._player or not self._event_bus or not self._order_queue or not self._player.event_queue:
            raise ValueError("Player, player event queue, event bus, and order queue must be instantiated.")
        
        # Randomly decide on a suit
        random_suit = random.choice(list(Suit))

        # Randomly decide on a price
        random_price = int(random.uniform(1, 100))

        # Randomly decide on a side
        random_side = random.choice(["bid", "ask"])

        random_order = Order(random_suit, random_side, random_price, self._player)
        return random_order