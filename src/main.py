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
        
class Player:
    def __init__(self, name: str) -> None:
        self.name = name
        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit} # Initialize empty inventory

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

class OrderEntry(TypedDict):
    price: int
    player: Player | None

class OrderBook(TypedDict):
    bid: OrderEntry
    ask: OrderEntry
    last_traded_price: int

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

        # Initialize 100 dollars to each player
        for player in self.players:
            player.dollars = 100

        # Initializes orderbook
        self.orderbook: Dict[str, OrderBook] = {
            suit.name: {
                "bid": {"price": -999, "player": None},
                "ask": {"price": 999, "player": None},
                "last_traded_price": 0,
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
            # You can only bid if the price is lower than the current bid
            # if you were the last bidder you can set any price (editing)
            if order.price <= self.orderbook[order.suit.name]["bid"]["price"] and self.orderbook[order.suit.name]["bid"]["player"] is not order.player:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} BID {order.price} for {order.suit.name} (current bid: {self.orderbook[order.suit.name]['bid']['price']})" + Fore.RESET)
                return

            # If there exists an ask for the same suit and price, trade
            if self.orderbook[order.suit.name]["ask"]["price"] == order.price and self.orderbook[order.suit.name]["ask"]["player"] is not order.player:
                asker = self.orderbook[order.suit.name]["ask"]["player"]
                if not asker:
                    raise ValueError("Asker is None")
                
                self.trade(asker, order.player, order.suit, order.price)
                
                # Remove ask from orderbook
                self.orderbook[order.suit.name]["ask"]["player"] = None
                self.orderbook[order.suit.name]["ask"]["price"] = 999
                return # Don't add bid to orderbook

            self.orderbook[order.suit.name]["bid"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} BID {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

        elif order.side == "ask":
            # You can only ask if the price is higher than the current ask
            # if you were the last asker you can set any price (editing)
            if order.price >= self.orderbook[order.suit.name]["ask"]["price"] and self.orderbook[order.suit.name]["ask"]["player"] is not order.player:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} ASK {order.price} for {order.suit.name} (current ask: {self.orderbook[order.suit.name]['ask']['price']})" + Fore.RESET)
                return
            
            # If there exists a bid for the same suit and price, trade
            if self.orderbook[order.suit.name]["bid"]["price"] == order.price and self.orderbook[order.suit.name]["bid"]["player"] is not order.player:
                bidder = self.orderbook[order.suit.name]["bid"]["player"]
                if not bidder:
                    raise ValueError("Bidder is None")
                
                self.trade(bidder, order.player, order.suit, order.price)

                # Remove bid from orderbook
                self.orderbook[order.suit.name]["bid"]["player"] = None
                self.orderbook[order.suit.name]["bid"]["price"] = -999
                return # Don't add ask to orderbook

            self.orderbook[order.suit.name]["ask"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} ASK {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

    def trade(self, receiver: Player, giver: Player, suit: Suit, price: int) -> None:
        if receiver.dollars < price:
            print(Fore.RED + f"[TRADE:FAILED] {receiver.name} does not have enough dollars to trade" + Fore.RESET)
            return
        
        if giver.inventory[suit] < 1:
            print(Fore.RED + f"[TRADE:FAILED] {giver.name} does not have enough {suit.name} to trade" + Fore.RESET)
            return

        receiver.dollars -= price
        receiver.inventory[suit] += 1

        giver.dollars += price
        giver.inventory[suit] -= 1

        self.orderbook[suit.name]["last_traded_price"] = price

        print(Fore.GREEN + f"[TRADE] {receiver.name} received {suit.name} for {price} dollars from {giver.name}" + Fore.RESET)

    def print_orderbook(self) -> None:
        table_data: list[dict[str, str | int]] = []
        for suit in Suit:
            bid = self.orderbook[suit.name]["bid"]
            ask = self.orderbook[suit.name]["ask"]

            bid_display = "-"
            if bid['price'] != -999 and bid['player']:
                bid_display = f"{Fore.GREEN}{bid['price']}{Fore.RESET} ({bid['player'].name})"
            
            ask_display = "-"
            if ask['price'] != 999 and ask['player']:
                ask_display = f"{Fore.RED}{ask['price']}{Fore.RESET} ({ask['player'].name})"

            table_data.append({
                'Suit': f"{suit.value} {suit.name.capitalize()}",
                'Bid': bid_display,
                'Ask': ask_display,
                'Last Trade': f'{Fore.CYAN}{self.orderbook[suit.name]["last_traded_price"]}{Fore.RESET}' if self.orderbook[suit.name]["last_traded_price"] != 0 else '-'
            })

        # Print orderbook table
        print("\n")
        print(tabulate(table_data, headers='keys', tablefmt='grid'))
        # Print player points
        print(Fore.LIGHTMAGENTA_EX + tabulate([[f"{player.name}: {player.dollars}" for player in self.players]], tablefmt='grid') + Fore.RESET)
        print("\n")

def main():
    p1 = Player("John")
    p2 = Player("Erick")
    p3 = Player("Jane")
    p4 = Player("Jim")
    p5 = Player("Jill")

    game = GameController([p1, p2, p3, p4, p5])

    game.add_order(Order(Suit.hearts, "bid", 10, p1))
    game.add_order(Order(Suit.hearts, "ask", 10, p2))

    game.print_orderbook()
    
    


if __name__ == "__main__":
    main()