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

    game.add_order(Order(Suit.hearts, "ask", 10, p1)) # sell 10
    game.add_order(Order(Suit.hearts, "bid", 11, p2)) # buy 11

    game.add_order(Order(Suit.hearts, "bid", 10, p2)) # buy 10
    game.add_order(Order(Suit.hearts, "ask", 9, p1)) # sell 9

    game.add_order(Order(Suit.hearts, "bid", 10, p2)) # buy 10

    game.end_round()

    game.print_orderbook()

if __name__ == "__main__":
    main()