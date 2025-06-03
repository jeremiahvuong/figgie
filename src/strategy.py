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
    """Randomly places bid/ask orders depending on the orderbook."""
    def __init__(self):
        super().__init__(name="Random")

        self._player: Optional["Player"] = None
        self._event_bus: Optional["EventBus"] = None
        self._order_queue: Optional[asyncio.Queue["Order"]] = None

        self.interval = random.uniform(0.1, 0.5) # interval in seconds between deciding orders

    async def start(self, player: "Player", event_bus: "EventBus", order_queue: asyncio.Queue["Order"], order_book: Dict[str, OrderBook]):
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
                order = await self._create_random_order()
                if order: await self._order_queue.put(order)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s strategy: {e}")

    async def _create_random_order(self) -> Optional["Order"]:
        assert self._player is not None # internal function, strategy should be associated with a player
        
        random_suit = random.choice(list(Suit))
        random_side: Literal["bid", "ask"] = random.choice(["bid", "ask"])

        # If the player has no inventory of the suit, don't place an ask order
        if random_side == "ask" and self._player.inventory[random_suit] < 1: return None

        # Get current market data
        order_book_entry = self._order_book[random_suit.name]
        current_bid = order_book_entry["bid"]["price"]
        current_ask = order_book_entry["ask"]["price"]
        last_traded = order_book_entry["last_traded_price"]
        
        # Handle default/empty orderbook values
        if current_bid == -999: current_bid = None
        if current_ask == 999: current_ask = None
        
        # Determine base price for order generation
        base_price = None
        if last_traded > 0:
            base_price = last_traded
        elif current_bid is not None and current_ask is not None:
            base_price = (current_bid + current_ask) / 2
        elif current_bid is not None:
            base_price = current_bid
        elif current_ask is not None:
            base_price = current_ask
        else:
            base_price = random.randint(5, 15)  # Default range if no market data
        
        # Generate competitive random price based on side
        if random_side == "bid":
            # For bids: must bid HIGHER than current bid (unless we're the current bidder)
            if current_bid is not None and order_book_entry["bid"]["player"] != self._player:
                # Must bid higher than current bid
                min_bid = current_bid + 1
                # Reasonable upper bound - don't bid too aggressively
                max_bid = min(50, current_bid + random.randint(1, 5))
                if min_bid > 50:  # Price too high, skip this order
                    return None
                random_price = random.uniform(min_bid, max_bid)
            elif current_bid is not None and order_book_entry["bid"]["player"] == self._player:
                # We're editing our own bid - can set any reasonable price
                random_price = max(1, base_price + random.uniform(-3, 3))
            else:
                # No current bid, set initial bid around base price
                random_price = max(1, base_price + random.uniform(-2, 2))
                
        else:  # ask
            # For asks: must ask LOWER than current ask (unless we're the current asker)
            if current_ask is not None and order_book_entry["ask"]["player"] != self._player:
                # Must ask lower than current ask
                max_ask = current_ask - 1
                # Reasonable lower bound - don't undersell too much
                min_ask = max(1, current_ask - random.randint(1, 5))
                if max_ask < 1:  # Price too low, skip this order
                    return None
                random_price = random.uniform(min_ask, max_ask)
            elif current_ask is not None and order_book_entry["ask"]["player"] == self._player:
                # We're editing our own ask - can set any reasonable price
                random_price = max(1, base_price + random.uniform(-3, 3))
            else:
                # No current ask, set initial ask around base price
                random_price = max(1, base_price + random.uniform(-2, 2))
        
        # Ensure price is reasonable (between 1 and 50 for this game)
        random_price = max(1, min(50, int(random_price)))
        
        # Additional check: make sure we're not violating the bidding rules
        if random_side == "bid" and current_bid is not None:
            if (order_book_entry["bid"]["player"] != self._player and 
                random_price <= current_bid):
                return None
        elif random_side == "ask" and current_ask is not None:
            if (order_book_entry["ask"]["player"] != self._player and 
                random_price >= current_ask):
                return None
            
        # Check if we're just replacing our own order with the same price
        current_order_player = order_book_entry[random_side]["player"]
        if (current_order_player == self._player and 
            order_book_entry[random_side]["price"] == random_price):
            return None
        
        random_order = Order(suit=random_suit, side=random_side, price=random_price, player=self._player)
        return random_order