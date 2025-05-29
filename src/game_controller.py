import random
from typing import Dict

from colorama import Fore
from tabulate import tabulate
from custom_types import OrderBook, Suit
from event import EventBus, TradeExecutedEvent
from order import Order
from player import Player


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

        # Initialize 100 dollars to each player (temp)
        for player in self.players:
            player.dollars = 100

        # Ante pot
        self._pot = 0
        ANTE = 40
        for player in self.players:
            player.dollars -= ANTE
            self._pot += ANTE
        
        # Initializes orderbook
        self.orderbook: Dict[str, OrderBook] = {
            suit.name: {
                "bid": {"price": -999, "player": None},
                "ask": {"price": 999, "player": None},
                "last_traded_price": 0,
            } for suit in Suit  
        }

        # Async Components
        self.event_bus = EventBus()

        # Print Game Start
        print("\n")
        print(Fore.LIGHTCYAN_EX + f"Pot: {self._pot}" + Fore.RESET)
        print(Fore.LIGHTCYAN_EX + f"Ante: {ANTE}" + Fore.RESET)

        # Print players
        print("Players:", ", ".join(self.player_names))
        # Print card counts
        print(tabulate([[f"{suit.value}: {self._suit_counts[suit]}" for suit in Suit]], tablefmt='grid'))
        print("\n")


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

    async def add_order(self, order: Order) -> None:
        """
        Adds an order to the orderbook.
        If a bid/ask is the same, a trade is executed, as such if we want to take a bid/ask we simply need to put up a bid/ask of the same price.
        """
        if order.side == "bid":
            # You can only bid if the price is lower than the current bid
            # if you were the last bidder you can set any price (editing)
            if order.price <= self.orderbook[order.suit.name]["bid"]["price"] and self.orderbook[order.suit.name]["bid"]["player"] is not order.player:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} BID {order.price} for {order.suit.name} (current bid: {self.orderbook[order.suit.name]['bid']['price']})" + Fore.RESET)
                return

            # If there exists an ask for the same or higher price, trade
            if self.orderbook[order.suit.name]["ask"]["price"] <= order.price and self.orderbook[order.suit.name]["ask"]["player"] is not order.player:
                asker = self.orderbook[order.suit.name]["ask"]["player"]
                if not asker:
                    raise ValueError("Asker is None")
                
                await self._trade(asker, order.player, order.suit, order.price)
                return # Don't add bid to orderbook

            self.orderbook[order.suit.name]["bid"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} BID {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

        elif order.side == "ask":
            if order.player.inventory[order.suit] < 1:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} does not have {order.suit.name} to sell" + Fore.RESET)
                return

            # You can only ask if the price is higher than the current ask
            # if you were the last asker you can set any price (editing)
            if order.price >= self.orderbook[order.suit.name]["ask"]["price"] and self.orderbook[order.suit.name]["ask"]["player"] is not order.player:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} ASK {order.price} for {order.suit.name} (current ask: {self.orderbook[order.suit.name]['ask']['price']})" + Fore.RESET)
                return

            # If there exists a bid for the same or lower price, trade
            if self.orderbook[order.suit.name]["bid"]["price"] >= order.price and self.orderbook[order.suit.name]["bid"]["player"] is not order.player:
                bidder = self.orderbook[order.suit.name]["bid"]["player"]
                if not bidder:
                    raise ValueError("Bidder is None")

                await self._trade(bidder, order.player, order.suit, order.price)
                return # Don't add ask to orderbook

            self.orderbook[order.suit.name]["ask"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} ASK {order.price} for {order.suit.name}" + Fore.RESET)
            self.print_orderbook()

    async def _trade(self, receiver: Player, giver: Player, suit: Suit, price: int) -> None:
        if receiver.dollars < price:
            print(Fore.RED + f"[TRADE:FAILED] {receiver.name} does not have enough dollars to trade" + Fore.RESET)
            return
        
        if giver.inventory[suit] < 1:
            print(Fore.RED + f"[TRADE:FAILED] {giver.name} does not have {suit.name} to trade" + Fore.RESET)
            return

        receiver.dollars -= price
        receiver.inventory[suit] += 1

        giver.dollars += price
        giver.inventory[suit] -= 1

        self._reset_suit_orderbook(suit)
        self.orderbook[suit.name]["last_traded_price"] = price

        print(Fore.GREEN + f"[TRADE] {receiver.name} received {suit.name} for {price} dollars from {giver.name}" + Fore.RESET)
        self.print_orderbook()

        # Publish trade executed event
        await self.event_bus.publish(TradeExecutedEvent(giver=giver, receiver=receiver, suit=suit, price=price))

    def _reset_suit_orderbook(self, suit: Suit) -> None:
        self.orderbook[suit.name]["bid"]["player"] = None
        self.orderbook[suit.name]["bid"]["price"] = -999
        self.orderbook[suit.name]["ask"]["player"] = None
        self.orderbook[suit.name]["ask"]["price"] = 999

    def end_round(self) -> None:
        winner: Player | None = None
        max_cards = 0

        if self._goal_suit is None:
            raise ValueError("Goal suit is not set") # Should never happen.

        for player in self.players:
            if player.inventory[self._goal_suit] > max_cards:
                winner = player
                max_cards = player.inventory[self._goal_suit]
        
        if winner:
            winner.dollars += self._pot
            print(Fore.GREEN + f"\n{winner.name} wins the round with {max_cards} {self._goal_suit.name} cards! (+{self._pot} dollars)" + Fore.RESET)
            self._pot = 0
        else:
            raise ValueError("No winner found") # Should never happen.

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

        print("\n")
        # Print orderbook table
        print(tabulate(table_data, headers='keys', tablefmt='grid'))
        # Print player points
        print(Fore.LIGHTMAGENTA_EX + tabulate([[f"{player.name}: {player.dollars}" for player in self.players]], tablefmt='grid') + Fore.RESET)
        print("\n")