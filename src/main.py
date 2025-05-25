import random
from enum import Enum
from typing import Dict, TypedDict

from colorama import Fore
from tabulate import tabulate


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

class Order:
    def __init__(self, suit: Suit, side: str, price: int, player_name: str) -> None:
        if side not in ["bid", "ask"]:
            raise ValueError("Side must be 'bid' or 'ask'")

        if suit not in Suit:
            raise ValueError("Invalid suit")

        self.suit = suit
        self.side = side
        self.price = price
        self.player_name = player_name

class OrderEntry(TypedDict):
    price: int
    player: str | None

class OrderBook(TypedDict):
    bid: OrderEntry
    ask: OrderEntry

class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Initialize empty inventory

class GameController:
    def __init__(self, players: list[Player]) -> None:
        if len(players) < 4 or len(players) > 5:
            raise ValueError("There must be 4 or 5 players in the game")

        self.players = players
        self.player_names = [player.name for player in players] # indexed player names

        # Game attributes to be set by _distribute_cards
        self._suit_12: Suit | None = None
        self._goal_suit: Suit | None = None
        self._suit_counts: Dict[Suit, int] = {}

        # Initializes deck of cards
        self._deck = self._init_cards()

        # Distribute cards to players
        self._distribute_cards()

        # Initializes orderbook
        self.orderbook: Dict[str, OrderBook] = {
            suit.name: {
                "bid": {"price": -999, "player": None},
                "ask": {"price": 999, "player": None},
            } for suit in Suit  
        }

    def _init_cards(self) -> list[Suit]:
        # 1) Randomly select 12-card suit
        self._suit_12 = random.choice(list(Suit))

        # 2) Randomly assign [10, 10, 8] to the remaining suits
        # Since goal suit is of the same color as the 12-card suit,
        # we remove the 12-card suit and shuffle again to avoid dependency
        suits_to_choose = [suit for suit in Suit if suit != self._suit_12]
        random.shuffle(suits_to_choose)
        self._suit_counts = {suits_to_choose[0]: 10, suits_to_choose[1]: 10, suits_to_choose[2]: 8, self._suit_12: 12}

        # 3) Assign goal suit (same color as 12-card suit)
        for suit in Suit:
            if suit.color == self._suit_12.color and suit != self._suit_12:
                self._goal_suit = suit
                break

        # 4) Return deck of randomized suits
        deck: list[Suit] = []

        for suit in self._suit_counts:
            for _ in range(self._suit_counts[suit]):
                deck.append(suit)

        random.shuffle(deck)
        return deck
        
    def _distribute_cards(self) -> None:
        # 4:10, 5:8
        if len(self.players) == 4:
            for player in self.players:
                for _ in range(10):
                    player.inventory[self._deck.pop()] += 1
        if len(self.players) == 5:
            for player in self.players:
                for _ in range(8):
                    player.inventory[self._deck.pop()] += 1

    def add_order(self, order: Order) -> None:
        if order.side == "bid":
            if order.price <= self.orderbook[order.suit.name]["bid"]["price"]:
                print(Fore.RED + f"[ORDER:FAILED] {order.player_name} BID {order.price} for {order.suit.name} (current bid: {self.orderbook[order.suit.name]['bid']['price']})" + Fore.RESET)
                return

            self.orderbook[order.suit.name]["bid"] = {
                "price": order.price,
                "player": order.player_name,
            }

            print(Fore.GREEN + f"[ORDER] {order.player_name} BID {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

        elif order.side == "ask":
            if order.price >= self.orderbook[order.suit.name]["ask"]["price"]:
                print(Fore.RED + f"[ORDER:FAILED] {order.player_name} ASK {order.price} for {order.suit.name} (current ask: {self.orderbook[order.suit.name]['ask']['price']})" + Fore.RESET)
                return

            self.orderbook[order.suit.name]["ask"] = {
                "price": order.price,
                "player": order.player_name,
            }

            print(Fore.GREEN + f"[ORDER] {order.player_name} ASK {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

    def print_orderbook(self) -> None:
        table_data: list[dict[str, str | int]] = []
        for suit in Suit:
            bid = self.orderbook[suit.name]['bid']
            ask = self.orderbook[suit.name]['ask']
            table_data.append({
                'Suit': suit.name.capitalize(),
                'Bid Price': bid['price'] if bid['price'] != -999 else '-',
                'Bidder': bid['player'] or '-',
                'Ask Price': ask['price'] if ask['price'] != 999 else '-',
                'Asker': ask['player'] or '-'
            })
        
        print(tabulate(table_data, headers='keys', tablefmt='grid'))

def main():
    p1 = Player("John")
    p2 = Player("Erick")
    p3 = Player("Jane")
    p4 = Player("Jim")
    p5 = Player("Jill")

    game = GameController([p1, p2, p3, p4, p5])

    game.add_order(Order(Suit.hearts, "bid", 10, p1.name))
    game.add_order(Order(Suit.hearts, "bid", 10, p1.name))

    print("p1 inventory:", p1.inventory)


if __name__ == "__main__":
    main()