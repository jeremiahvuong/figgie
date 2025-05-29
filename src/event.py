import asyncio
from typing import TYPE_CHECKING, Dict, List

from custom_types import Suit
from order import Order
from player import Player

if TYPE_CHECKING:
    pass

"""
Events to be used in the event bus
"""
class Event:
    """Base class for all events."""
    pass

class OrderPlacedEvent(Event):
    def __init__(self, player: Player, order: Order):
        self.player = player
        self.order = order

class TradeExecutedEvent(Event):
    def __init__(self, receiver: Player, giver: Player, suit: Suit, price: int):
        self.receiver = receiver
        self.giver = giver
        self.suit = suit
        self.price = price

"""
Event bus is used by the event_driven architecture.
The player makes a subsequent decision based on the subscribed event.
Some strategies fall under HFT.
"""
class EventBus:
    def __init__(self):
        """
        _subscribers is a dictionary that maps event types to list
        of the subscribed players' queues.

        ex: {OrderPlacedEvent: [player1_event_queue, player2_event_queue],
            TradeExecutedEvent: [player1_event_queue, player3_event_queue],
            ...}
        """
        self._subscribers: Dict[type, List[asyncio.Queue[Event]]] = {}

    async def subscribe(self, event_type: type, queue: asyncio.Queue[Event]) -> None:
        """Subscribe a queue to a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = [] # make a new list if it doesn't exist
        self._subscribers[event_type].append(queue)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of that event type."""
        event_type = type(event)
        if event_type in self._subscribers:
            for queue in self._subscribers[event_type]:
                # Use create_task to avoid blocking publish if a queue is full
                asyncio.create_task(queue.put(event))