import asyncio
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

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
        """The main asynchronous method for the strategy's logic; runs within an asyncio task."""
        pass

"""
Strategy implementations
"""
class RandomStrategy(Strategy):
    def __init__(self):
        super().__init__(name="Random")

        self._player: Optional["Player"] = None
        self._event_bus: Optional["EventBus"] = None
        self._order_queue: Optional[asyncio.Queue["Order"]] = None

        self.interval = random.uniform(0.1, 0.5) # interval in seconds between deciding orders

    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"]):
        """
        Randomly places bid/ask orders depending on the player's inventory and spread.
        """
        self._player = player
        self._event_bus = event_bus
        self._order_queue = order_queue

        self._running = True

        # Subscribe to the game state changed event
        await self._event_bus.subscribe(GameStateChangedEvent, self._player.event_queue)

        while self._running:
            try:
                await asyncio.sleep(self.interval) # Wait for interval seconds
                order = await self._get_random_order()
                if order:
                    await self._order_queue.put(order)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s Generic strategy: {e}")

    async def _get_random_order(self) -> Optional["Order"]:
        assert self._player is not None # internal function, strategy should be associated with a player
        random_suit = random.choice(list(Suit))
        random_price = int(random.uniform(1, 20))
        random_side = random.choice(["bid", "ask"])

        random_order = Order(suit=random_suit, side=random_side, price=random_price, player=self._player)
        return random_order