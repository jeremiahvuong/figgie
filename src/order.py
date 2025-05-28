from custom_types import Suit
from player import Player

class Order:
    def __init__(self, suit: Suit, side: str, price: int, player: Player) -> None:
        if side not in ["bid", "ask"]:
            raise ValueError("Side must be 'bid' or 'ask'")

        if suit not in Suit:
            raise ValueError("Invalid suit")

        self.suit = suit
        self.side = side
        self.price = price
        self.player = player