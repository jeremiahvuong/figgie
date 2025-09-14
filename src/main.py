import asyncio

from game_controller import GameController
from player import Player
from strategy import BayesianInference, Noisy


async def main():
    p1 = Player(strategy=BayesianInference(), alias="GrexCrew")
    p2 = Player(strategy=Noisy(lower_interval=0.5, upper_interval=3), alias="Erick")
    p3 = Player(strategy=Noisy(lower_interval=0.5, upper_interval=3), alias="Zoe")
    p4 = Player(strategy=Noisy(lower_interval=0.5, upper_interval=3), alias="Kevin")
    p5 = Player(strategy=Noisy(lower_interval=0.5, upper_interval=3), alias="Jill")

    game = GameController(players=[p1, p2, p3, p4, p5], verbose_orderbook=False)

    await game.start_round(round_duration=60)

if __name__ == "__main__":
    asyncio.run(main())