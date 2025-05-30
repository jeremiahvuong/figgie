import asyncio
from typing import TYPE_CHECKING, Any, Dict, Set, Type

from custom_types import Suit

if TYPE_CHECKING:
    from order import Order
    from player import Player

"""
Events to be used in the event bus
"""
class Event:
    """Base class for all events."""
    pass

class OrderPlacedEvent(Event):
    """Event for when any player places an order."""
    def __init__(self, player: "Player", order: "Order"):
        self.player = player
        self.order = order

class TradeExecutedEvent(Event):
    """Event for when a trade is executed."""
    def __init__(self, receiver: "Player", giver: "Player", suit: Suit, price: int):
        self.receiver = receiver
        self.giver = giver
        self.suit = suit
        self.price = price

class GameStateChangedEvent(Event):
    """Event for when the game state changes."""
    def __init__(self, game_state_snapshot: Dict[str, Any]):
        self.game_state_snapshot = game_state_snapshot


class EventBus:
    """
    A passive message broker that facilitates communication between components without direct coupling.
    Can be used by both event-driven and non-event-driven architectures.
    """
    def __init__(self):
        self._subscribers: Dict[Type[Event], Set[asyncio.Queue[Event]]] = {}
        """
        A dictionary that maps event types to a set of the subscribed players' queues.

        ex: {OrderPlacedEvent: {player1_event_queue, player2_event_queue},
            TradeExecutedEvent: {player2_event_queue, player3_event_queue},
            ...}
        """

    async def subscribe(self, event_type: Type[Event], queue: asyncio.Queue[Event]) -> None:
        """Subscribe a queue to a specific event type."""
        if event_type not in self._subscribers:
            # Create a new set if the event type is not in the dictionary
            self._subscribers[event_type] = set()
        self._subscribers[event_type].add(queue)

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of that event type."""
        event_type = type(event)

        if event_type not in self._subscribers:
            return # No subscribers

        for queue in self._subscribers[event_type]:
            # Use create_task to avoid blocking publish if a queue is full.
            asyncio.create_task(queue.put(event))