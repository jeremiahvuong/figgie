"""
Core game types and enums for the Figgie trading game.

This module contains the basic types used throughout the game to avoid
circular import issues.
"""

from enum import Enum
from typing import TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from player import Player


class Suit(Enum):
    hearts = "♥"
    diamonds = "♦"
    clubs = "♣"
    spades = "♠"

    @property
    def color(self) -> str:
        # Diamonds and Hearts are red, Clubs and Spades are black
        if self in [Suit.hearts, Suit.diamonds]:
            return "red"
        else:
            return "black"

"""
Types to be used by the orderbook.
"""
class OrderEntry(TypedDict):
    price: int
    player: "Player | None"

class OrderBook(TypedDict):
    bid: OrderEntry
    ask: OrderEntry
    last_traded_price: int