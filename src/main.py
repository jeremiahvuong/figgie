import random
import time
from typing import Dict, Optional, TypedDict

from colorama import Fore
from tabulate import tabulate

from game_types import Suit
        
class GameState:
    """Immutable snapshot of game state for strategy decision making"""
    def __init__(self, orderbook: Dict[str, 'OrderBook'], player_inventory: Dict[Suit, int], 
                 player_dollars: int, pot: int, suit_counts: Dict[Suit, int], 
                 goal_suit: Optional[Suit] = None, suit_12: Optional[Suit] = None):
        self.orderbook = orderbook.copy()
        self.player_inventory = player_inventory.copy()
        self.player_dollars = player_dollars
        self.pot = pot
        self.suit_counts = suit_counts.copy()
        self.goal_suit = goal_suit
        self.suit_12 = suit_12


# Import base strategy class
from base_strategy import TradingStrategy


class Player:
    def __init__(self, name: str, strategy: TradingStrategy) -> None:
        self.name = name
        self.dollars = 0
        self.inventory: Dict[Suit, int] = {suit: 0 for suit in Suit}
        self.strategy = strategy

    def decide_action(self, game_state: GameState) -> Optional['Order']:
        """Use the player's strategy to decide on an action"""
        return self.strategy.decide_action(game_state, self)

    def get_strategy_name(self) -> str:
        return self.strategy.get_strategy_name()


class Order:
    def __init__(self, suit: Suit, side: str, price: int, player: Player) -> None:
        if side not in ["bid", "ask"]:
            raise ValueError("Side must be 'bid' or 'ask'")

        if not isinstance(suit, Suit):
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

        # Print Game Start
        print("\n")
        print(Fore.LIGHTCYAN_EX + f"Pot: {self._pot}" + Fore.RESET)
        print(Fore.LIGHTCYAN_EX + f"Ante: {ANTE}" + Fore.RESET)

        # Print players and their strategies
        player_info = [f"{player.name} ({player.get_strategy_name()})" for player in self.players]
        print("Players:", ", ".join(player_info))
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

    def add_order(self, order: Order) -> None:
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
            if order.player.inventory[order.suit] < 1:
                print(Fore.RED + f"[ORDER:FAILED] {order.player.name} does not have {order.suit.name} to sell" + Fore.RESET)
                return

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
            print(Fore.RED + f"[TRADE:FAILED] {giver.name} does not have {suit.name} to trade" + Fore.RESET)
            return

        receiver.dollars -= price
        receiver.inventory[suit] += 1

        giver.dollars += price
        giver.inventory[suit] -= 1

        self.orderbook[suit.name]["last_traded_price"] = price

        print(Fore.GREEN + f"[TRADE] {receiver.name} received {suit.name} for {price} dollars from {giver.name}" + Fore.RESET)

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

        # Print orderbook table
        print("\n")
        print(tabulate(table_data, headers='keys', tablefmt='grid'))
        # Print player points
        print(Fore.LIGHTMAGENTA_EX + tabulate([[f"{player.name}: {player.dollars}" for player in self.players]], tablefmt='grid') + Fore.RESET)
        print("\n")

    def create_game_state(self, player: Player) -> GameState:
        """Create a GameState snapshot for a specific player"""
        return GameState(
            orderbook=self.orderbook,
            player_inventory=player.inventory,
            player_dollars=player.dollars,
            pot=self._pot,
            suit_counts=self._suit_counts,
            goal_suit=self._goal_suit,
            suit_12=self._suit_12
        )

    def run_trading_round(self, duration_minutes: float = 2.0, verbose: bool = True) -> None:
        """Run a time-based trading round where players trade for a specified duration"""
        start_time = time.time()
        duration_seconds = duration_minutes * 60
        action_count = 0
        
        if verbose:
            print(Fore.LIGHTBLUE_EX + f"=== Starting {duration_minutes}-Minute Trading Round ===" + Fore.RESET)
            print(f"Trading will end at: {time.strftime('%H:%M:%S', time.localtime(start_time + duration_seconds))}")
        
        while time.time() - start_time < duration_seconds:
            # Randomly select a player to act
            active_player = random.choice(self.players)
            
            # Simulate thinking time (strategy-specific delays)
            thinking_time = active_player.strategy.get_thinking_time()
            time.sleep(thinking_time)
            
            # Check if we still have time after thinking
            if time.time() - start_time >= duration_seconds:
                break
            
            # Get the game state for this player
            game_state = self.create_game_state(active_player)
            
            # Let the player's strategy decide on an action
            order = active_player.decide_action(game_state)
            
            if order:
                self.add_order(order)
                action_count += 1
                
                # Show time remaining periodically
                if verbose and action_count % 5 == 0:
                    elapsed = time.time() - start_time
                    remaining = duration_seconds - elapsed
                    print(f"Time remaining: {remaining:.1f}s | Actions taken: {action_count}")
        
        elapsed_time = time.time() - start_time
        if verbose:
            print(Fore.LIGHTBLUE_EX + f"=== Trading Round Complete ({elapsed_time:.1f}s, {action_count} actions) ===" + Fore.RESET)

    def run_simulation(self, num_rounds: int = 1, duration_minutes: float = 2.0, verbose: bool = True) -> None:
        """Run multiple rounds of time-based trading"""
        for round_num in range(num_rounds):
            if verbose:
                print(f"\n{Fore.LIGHTCYAN_EX}=== ROUND {round_num + 1} ==={Fore.RESET}")
            
            # Reset for new round if not the first round
            if round_num > 0:
                self._reset_round()
            
            # Run trading
            self.run_trading_round(duration_minutes, verbose)
            
            # End round and determine winner
            self.end_round()
            
            if verbose:
                self.print_final_standings()

    def _reset_round(self) -> None:
        """Reset the game state for a new round"""
        # Reset player inventories and dollars
        for player in self.players:
            player.inventory = {suit: 0 for suit in Suit}
            player.dollars = 100

        # Reset game state
        self._deck = self._init_cards()
        self._distribute_cards()
        
        # Ante pot
        self._pot = 0
        ANTE = 40
        for player in self.players:
            player.dollars -= ANTE
            self._pot += ANTE
        
        # Reset orderbook
        self.orderbook = {
            suit.name: {
                "bid": {"price": -999, "player": None},
                "ask": {"price": 999, "player": None},
                "last_traded_price": 0,
            } for suit in Suit  
        }

    def print_final_standings(self) -> None:
        """Print final standings sorted by dollars"""
        sorted_players = sorted(self.players, key=lambda p: p.dollars, reverse=True)
        
        print(f"\n{Fore.LIGHTGREEN_EX}=== FINAL STANDINGS ==={Fore.RESET}")
        standings_data = []
        for i, player in enumerate(sorted_players, 1):
            goal_cards = player.inventory[self._goal_suit] if self._goal_suit else 0
            standings_data.append([
                f"{i}.",
                f"{player.name} ({player.get_strategy_name()})",
                f"${player.dollars}",
                f"{goal_cards} {self._goal_suit.name if self._goal_suit else 'N/A'}"
            ])
        
        print(tabulate(standings_data, 
                      headers=["Rank", "Player (Strategy)", "Dollars", "Goal Cards"], 
                      tablefmt='grid'))
        print()

def main():
    # Import strategies
    from strategies import RandomStrategy, ConservativeStrategy, AggressiveStrategy, ValueStrategy
    
    # Create players with different strategies
    p1 = Player("Alice", RandomStrategy(action_probability=0.4))
    p2 = Player("Bob", ConservativeStrategy())
    p3 = Player("Charlie", AggressiveStrategy())
    p4 = Player("Diana", ValueStrategy())
    p5 = Player("Eve", RandomStrategy(action_probability=0.2))

    # Create game controller
    game = GameController([p1, p2, p3, p4, p5])

    # Run automated trading simulation
    print(f"{Fore.LIGHTMAGENTA_EX}Goal suit is: {game._goal_suit.name if game._goal_suit else 'Unknown'}{Fore.RESET}")
    print(f"{Fore.LIGHTMAGENTA_EX}12-card suit is: {game._suit_12.name if game._suit_12 else 'Unknown'}{Fore.RESET}")
    
    # Run a single round of time-based trading (2 minutes)
    game.run_trading_round(duration_minutes=2.0, verbose=True)
    
    # Show final orderbook
    game.print_orderbook()
    
    # End the round
    game.end_round()
    
    # Show final standings
    game.print_final_standings()

def demo_multi_round():
    """Demonstrate multi-round simulation"""
    print(f"\n{Fore.LIGHTCYAN_EX}=== MULTI-ROUND SIMULATION DEMO ==={Fore.RESET}")
    
    # Import strategies
    from strategies import RandomStrategy, ConservativeStrategy, AggressiveStrategy, ValueStrategy
    
    # Create players with different strategies
    players = [
        Player("RandomBot1", RandomStrategy(action_probability=0.3)),
        Player("Conservative", ConservativeStrategy()),
        Player("Aggressive", AggressiveStrategy()),
        Player("ValueTrader", ValueStrategy()),
        Player("RandomBot2", RandomStrategy(action_probability=0.4))
    ]
    
    game = GameController(players)
    
    # Run 3 rounds of simulation (2 minutes each)
    game.run_simulation(num_rounds=3, duration_minutes=2.0, verbose=True)

if __name__ == "__main__":
    # Run single round demo
    #main()
    
    # Uncomment to run multi-round demo
    demo_multi_round()