from custom_types import Suit
from game_controller import GameController
from order import Order
from player import Player


def main():
    p1 = Player("John")
    p2 = Player("Erick")
    p3 = Player("Jane")
    p4 = Player("Jim")
    p5 = Player("Jill")

    game = GameController([p1, p2, p3, p4, p5])

    game.add_order(Order(Suit.hearts, "bid", 10, p1)) # wants to buy hearts for 10 dollars
    game.add_order(Order(Suit.hearts, "ask", 10, p2)) # wants to sell hearts for 10 dollars

    game.end_round()

    game.print_orderbook()

if __name__ == "__main__":
    main()