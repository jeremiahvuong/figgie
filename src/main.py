import asyncio

from game_controller import GameController
from player import Player
from strategy import RandomStrategy


async def main():
    p1 = Player(RandomStrategy("John"))
    p2 = Player(RandomStrategy("Erick"))
    p3 = Player(RandomStrategy("Jane"))
    p4 = Player(RandomStrategy("Jim"))
    p5 = Player(RandomStrategy("Jill"))

    game = GameController(players=[p1, p2, p3, p4, p5], verbose_orderbook=False)

    await game.start_round(round_duration=10)

if __name__ == "__main__":
    asyncio.run(main())