import asyncio
import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Literal, Optional

from custom_types import OrderBook, Suit
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
    async def start(self, player: "Player", event_bus: "EventBus", order_book: Dict[str, OrderBook]) -> None:
        """The main asynchronous method for the strategy's logic; runs within an asyncio task, invoked by player.start()"""
        pass

"""
Strategy implementations
"""
class Noisy(Strategy):
    """Randomly places bid/ask orders between $1-15 inclusive."""
    def __init__(self, lower_interval: float = 1, upper_interval: float = 5):
        super().__init__(name="Noisy")
        self.interval = random.uniform(lower_interval, upper_interval) # interval in seconds between deciding orders

    async def start(self, player: "Player", event_bus: "EventBus", order_book: Dict[str, OrderBook]):
        self._player = player
        self._order_queue = player.order_queue
        self._event_bus = event_bus
        self._order_book = order_book
        self._running = True

        while self._running:
            try:
                await asyncio.sleep(self.interval) # Wait for interval seconds
                order = await self._create_random_order()
                # Note: if order is None, Noisy will have to wait another interval to send an order
                if order: await self._order_queue.put(order)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s strategy: {e}")

    async def _create_random_order(self) -> Optional["Order"]:
        assert self._player is not None # internal function, strategy should be associated with a player

        random_suit = random.choice(list(Suit))
        random_side: Literal["bid", "ask"] = random.choice(["bid", "ask"])

        order_book_entry = self._order_book[random_suit.name]
        current_bid = order_book_entry["bid"]["price"]
        current_ask = order_book_entry["ask"]["price"]

        if random_side == "bid":
            min_price, max_price = 1, min(15, self._player.dollars)
            # Don't buy if we're have > 3 cards of the suit
            if self._player.inventory[random_suit] >= 3: return None

            if current_bid != -999 and order_book_entry["bid"]["player"] != self._player:
                min_price = current_bid + 1 # Can't buy for less than the current bid
                if min_price > max_price: return None # No valid price possible

        elif random_side == "ask":
            min_price, max_price = 1, 15
            # Can't sell if we have none of the suit
            if self._player.inventory[random_suit] < 1: return None

            if current_ask != 999 and order_book_entry["ask"]["player"] != self._player:
                max_price = current_ask - 1 # Can't sell for more than the current ask
                if max_price < min_price: return None # No valid price possible
        
        # Generate random price in valid range
        random_price = random.randint(min_price, max_price)

        random_order = Order(suit=random_suit, side=random_side, price=random_price, player=self._player)
        return random_order
