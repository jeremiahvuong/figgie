import asyncio
from typing import TYPE_CHECKING, Dict

from custom_types import OrderBook, Suit

if TYPE_CHECKING:
    from event import Event, EventBus
    from order import Order
    from strategy import Strategy

class Player:
    def __init__(self, strategy: 'Strategy', alias: str = "") -> None:
        self.strategy: Strategy = strategy

        self.name = f"{strategy.name} ({alias})" if alias else strategy.name

        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Init empty inventory

        self.event_queue: asyncio.Queue[Event] = asyncio.Queue()
        self.order_queue: asyncio.Queue[Order] = asyncio.Queue()

    async def start_strategy(self, event_bus: "EventBus", order_book: Dict[str, OrderBook]) -> None:
        """Runs the player's strategy."""
        await self.strategy.start(player=self, event_bus=event_bus, order_queue=self.order_queue, order_book=order_book)