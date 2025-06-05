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
    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"], order_book: Dict[str, OrderBook]):
        """The main asynchronous method for the strategy's logic; runs within an asyncio task, invoked by player.start()"""
        pass

"""
Strategy implementations
"""
class Noisy(Strategy):
    """Randomly places bid/ask orders between $1-15 inclusive."""
    def __init__(self, lower_interval: float = 1, upper_interval: float = 5):
        super().__init__(name="Noisy")

        self._player: Optional["Player"] = None
        self._event_bus: Optional["EventBus"] = None
        self._order_queue: Optional[asyncio.Queue["Order"]] = None

        self.interval = random.uniform(lower_interval, upper_interval) # interval in seconds between deciding orders

    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"], order_book: Dict[str, OrderBook]):
        self._player = player
        self._event_bus = event_bus
        self._order_queue = order_queue
        self._order_book = order_book

        self._running = True

        while self._running:
            try:
                await asyncio.sleep(self.interval) # Wait for interval seconds
                order = await self._create_random_order()
                # If order is None, we skip that iteration,
                # such that Noisy has to wait another interval to send an order;
                # unintentionally acts as a "random" method.
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
        
        # Represent empty orderbook values as None for easier comparison
        if current_bid == -999: current_bid = None
        if current_ask == 999: current_ask = None

        if random_side == "bid":
            min_price, max_price = 1, min(15, self._player.dollars)
            # Don't buy if we're have > 3 cards of the suit
            if self._player.inventory[random_suit] >= 3: return None

            # For bids: must be higher than current bid if not our own bid
            if current_bid is not None and order_book_entry["bid"]["player"] != self._player:
                min_price = current_bid + 1 # Can't buy for less than the current bid
                if min_price > max_price: return None # No valid price possible

        elif random_side == "ask":
            min_price, max_price = 1, 15
            # Can't sell if we have none of the suit
            if self._player.inventory[random_suit] < 1: return None

            # For asks: must be lower than current ask if not our own ask
            if current_ask is not None and order_book_entry["ask"]["player"] != self._player:
                max_price = current_ask - 1 # Can't sell for more than the current ask
                if max_price < min_price: return None # No valid price possible
        
        # Generate random price in valid range
        random_price = random.randint(min_price, max_price)

        random_order = Order(suit=random_suit, side=random_side, price=random_price, player=self._player)
        return random_order
