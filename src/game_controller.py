import asyncio
import random
import time
from typing import Dict

from colorama import Fore
from tabulate import tabulate

from custom_types import OrderBook, Suit
from event import EventBus, OrderPlacedEvent, TradeExecutedEvent
from order import Order
from player import Player


class GameController:
    def __init__(self, players: list[Player], verbose_orderbook: bool = False) -> None:
        if len(players) < 4 or len(players) > 5:
            raise ValueError("There must be 4 or 5 players in the game")

        self.verbose_orderbook = verbose_orderbook

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
        self._player_order_queues: Dict[str, asyncio.Queue[Order]] = {} # Player name : Order queue
        self._player_tasks: Dict[str, asyncio.Task[None]] = {} # Player name : Task
        self._running = False # Simulation running state

        self._start_time = 0

        # Print Game Start
        print("\n")
        print(Fore.LIGHTCYAN_EX + f"Pot: {self._pot}" + Fore.RESET)
        print(Fore.LIGHTCYAN_EX + f"Ante: {ANTE}" + Fore.RESET)
        print(Fore.LIGHTCYAN_EX + f"Goal Suit: {self._goal_suit.name.capitalize() if self._goal_suit else 'Goal Suit Not Set!'}" + Fore.RESET)

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

        # 4) Add cards to deck
        deck: list[Suit] = []
        for suit in self._suit_counts:
            for _ in range(self._suit_counts[suit]):
                deck.append(suit)

        # 5) Shuffle deck and return
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
        If a bid/ask is the same or of better value than the current ask/bid, a trade is executed.
        Trades are executed at the lowest of the bid/ask price.
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
                if not asker: raise ValueError("Asker is None") # Should never happen

                trade_price = min(order.price, self.orderbook[order.suit.name]["ask"]["price"])

                await self._trade(receiver=order.player, giver=asker, suit=order.suit, price=trade_price)
                return # Don't add bid to orderbook

            self.orderbook[order.suit.name]["bid"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} BID {order.price} for {order.suit.name} @ {time.time() - self._start_time:.3f}s" + Fore.RESET)
            await self.event_bus.publish(OrderPlacedEvent(player=order.player, order=order))
            self.print_orderbook()

        elif order.side == "ask":
            if order.player.inventory[order.suit] < 1:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} does not have {order.suit.name} to sell" + Fore.RESET)
                return

            # You can only ask if lower than the current ask
            # if you were the last asker you can set any price (editing)
            if order.price >= self.orderbook[order.suit.name]["ask"]["price"] and self.orderbook[order.suit.name]["ask"]["player"] is not order.player:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} ASK {order.price} for {order.suit.name} (current ask: {self.orderbook[order.suit.name]['ask']['price']})" + Fore.RESET)
                return

            # If there exists a bid for the same or lower price, trade
            if self.orderbook[order.suit.name]["bid"]["price"] >= order.price and self.orderbook[order.suit.name]["bid"]["player"] is not order.player:
                bidder = self.orderbook[order.suit.name]["bid"]["player"]
                if not bidder: raise ValueError("Bidder is None") # Should never happen

                trade_price = min(order.price, self.orderbook[order.suit.name]["bid"]["price"])

                await self._trade(receiver=bidder, giver=order.player, suit=order.suit, price=trade_price)
                return # Don't add ask to orderbook

            self.orderbook[order.suit.name]["ask"] = {
                "price": order.price,
                "player": order.player,
            }

            print(Fore.YELLOW + f"[ORDER] {order.player.name} ASK {order.price} for {order.suit.name} @ {time.time() - self._start_time:.3f}s" + Fore.RESET)
            await self.event_bus.publish(OrderPlacedEvent(player=order.player, order=order))
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

        print(Fore.GREEN + f"[TRADE] {receiver.name} received {suit.name} for {price} dollars from {giver.name} @ {time.time() - self._start_time:.3f}s" + Fore.RESET)
        await self.event_bus.publish(TradeExecutedEvent(giver=giver, receiver=receiver, suit=suit, price=price))

        # Since the reciever loses money, if they have active bids that are greater 
        # than their amount of dollars after the trade, cancel those orders.
        for s in Suit:
            if s == suit: continue # already reset, skip the suit we're trading
            if self.orderbook[s.name]["bid"]["player"] == receiver:
                trade_price = self.orderbook[s.name]["bid"]["price"]
                if receiver.dollars < trade_price:
                    self.orderbook[s.name]["bid"]["player"] = None
                    self.orderbook[s.name]["bid"]["price"] = -999
                    print(Fore.MAGENTA + f"[TRADE:CANCELLED] {receiver.name} bid of {trade_price} for {s.name} cancelled because they don't have enough dollars to trade @ {time.time() - self._start_time:.3f}s" + Fore.RESET)

        self.print_orderbook()

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
            self.print_orderbook(always_print=True)
            # Print player inventory
            for player in self.players:
                print(Fore.LIGHTMAGENTA_EX + f"{player.name}: {player.inventory}" + Fore.RESET)

            # Reset pot
            self._pot = 0
        else:
            raise ValueError("No winner found") # Should never happen.
        
    async def start_round(self, round_duration: float = 60.0) -> None:
        """Runs a single game round for round_duration seconds."""
        self._running = True
        self._start_time = time.time()

        # Run players' strategies
        for player in self.players:
            self._player_order_queues[player.name] = player.order_queue # Store mapped {player names : order queues}
            player_task = asyncio.create_task(player.start_strategy(event_bus=self.event_bus, order_book=self.orderbook))
            self._player_tasks[player.name] = player_task # Store mapped {player names : tasks}

        # Process player orders
        order_processing_task = asyncio.create_task(self._process_player_orders())

        # Run game round for round_duration seconds
        try:
            await asyncio.sleep(round_duration)
        except asyncio.CancelledError:
            print("Game round cancelled")

        print("Game round ending...")
        self._running = False

        # Queue cancellations of tasks
        order_processing_task.cancel()
        for task in self._player_tasks.values(): task.cancel()

        # Wait for all tasks to complete successfully, then end round
        await asyncio.gather(order_processing_task, *self._player_tasks.values(), return_exceptions=True)
        self.end_round()

    async def _process_player_orders(self) -> None:
        """Asynchronous task that processes player orders upon receiving them from the event bus."""
        merged_order_queue: asyncio.Queue[Order] = asyncio.Queue()

        forwarding_tasks: list[asyncio.Task[None]] = []
        async def forward_orders(player_queue: asyncio.Queue[Order], merged_queue: asyncio.Queue[Order]) -> None:
            """Forward orders from player's order queue to the merged order queue."""
            while self._running:
                try:
                    order = await player_queue.get()
                    await merged_queue.put(order)
                except asyncio.CancelledError:
                    break

        for order_queue in self._player_order_queues.values():
            forwarding_tasks.append(asyncio.create_task(forward_orders(order_queue, merged_order_queue)))

        while self._running:
            try:
                order = await merged_order_queue.get()
                if order:
                    await self.add_order(order)
            except asyncio.TimeoutError:
                break
            except asyncio.CancelledError:
                break
        
        # Cancel all players' forwarding tasks
        for task in forwarding_tasks:
            task.cancel()

        # Wait for all forwarding tasks to complete
        await asyncio.gather(*forwarding_tasks, return_exceptions=True)

    def print_orderbook(self, always_print: bool = False) -> None:
        if not self.verbose_orderbook and not always_print:
            return

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