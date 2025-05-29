from typing import TYPE_CHECKING, Dict, Optional
from custom_types import Suit

if TYPE_CHECKING:
    import asyncio


class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Initialize empty inventory

        self.event_queue: Optional[asyncio.Queue[asyncio.Event]] = None