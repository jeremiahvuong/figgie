import asyncio

from game_controller import GameController
from player import Player
from strategy import RandomStrategy


async def main():
    p1 = Player(strategy=RandomStrategy(), alias="John")
    p2 = Player(strategy=RandomStrategy(), alias="Erick")
    p3 = Player(strategy=RandomStrategy(), alias="Jane")
    p4 = Player(strategy=RandomStrategy(), alias="Jim")
    p5 = Player(strategy=RandomStrategy(), alias="Jill")

    game = GameController(players=[p1, p2, p3, p4, p5], verbose_orderbook=False)

    await game.start_round(round_duration=10)

if __name__ == "__main__":
    asyncio.run(main())