from typing import Dict

from custom_types import Suit


class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Initialize empty inventory