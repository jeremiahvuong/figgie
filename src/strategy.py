import asyncio
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Literal, Optional

from custom_types import OrderBook, Suit
from event import GameStateChangedEvent
from order import Order

if TYPE_CHECKING:
    from event import EventBus
    from player import Player


class Strategy(ABC):
    """Abstract base class for all strategies."""
    def __init__(self, name: str):
        self.name = name
        self._running = False

    @abstractmethod
    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"], order_book: Dict[str, OrderBook]):
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

    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"], order_book: Dict[str, OrderBook]):
        """
        Randomly places bid/ask orders depending on the player's inventory and spread.
        """
        self._player = player
        self._event_bus = event_bus
        self._order_queue = order_queue
        self._order_book = order_book

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
        random_side: Literal["bid", "ask"] = random.choice(["bid", "ask"])

        # If the player has no inventory of the suit, don't place an order
        if random_side == "ask" and self._player.inventory[random_suit] < 1:
            return None

        curr_price = self._order_book[random_suit.name][random_side]['price']

        if curr_price == -999 or curr_price == 999:
            curr_price = 0

        if random_side == "bid":
            random_price = curr_price + random.uniform(1, 3)
        elif random_side == "ask" and curr_price == 0:
            random_price = 1
        else:
            random_price = curr_price - random.uniform(1, 3)

        if random_price < 1:
            return None

        random_order = Order(suit=random_suit, side=random_side, price=int(random_price), player=self._player)
        return random_order