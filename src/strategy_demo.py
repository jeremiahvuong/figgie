"""
Demo script showcasing different algorithmic trading strategies in Figgie.

This script demonstrates various trading strategies and allows for easy
experimentation with different combinations of players and strategies.
"""

from main import GameController, Player
from strategies import (
    RandomStrategy, ConservativeStrategy, AggressiveStrategy, 
    ValueStrategy, MarketMakerStrategy, MomentumStrategy, InformationStrategy
)


def demo_all_strategies():
    """Demonstrate all available trading strategies"""
    print("=== FIGGIE ALGORITHMIC TRADING STRATEGIES DEMO ===\n")
    
    # Create players with different strategies
    players = [
        Player("RandomBot", RandomStrategy(action_probability=0.4)),
        Player("Conservative", ConservativeStrategy()),
        Player("Aggressive", AggressiveStrategy()),
        Player("ValueTrader", ValueStrategy()),
        Player("MarketMaker", MarketMakerStrategy(target_spread=2, max_position=3)),
        Player("MomentumBot", MomentumStrategy(momentum_threshold=2)),
        Player("InfoTrader", InformationStrategy())
    ]
    
    # Take only 5 players for the game
    game_players = players[:5]
    
    print("Strategies being tested:")
    for player in game_players:
        print(f"  - {player.name}: {player.get_strategy_name()}")
    print()
    
    # Create and run game
    game = GameController(game_players)
    
    # Run multiple rounds to see strategy performance
    game.run_simulation(num_rounds=3, actions_per_round=60, verbose=True)


def demo_strategy_comparison():
    """Compare specific strategies head-to-head"""
    print("\n=== STRATEGY COMPARISON: Conservative vs Aggressive vs Value ===\n")
    
    players = [
        Player("Conservative1", ConservativeStrategy()),
        Player("Conservative2", ConservativeStrategy()),
        Player("Aggressive1", AggressiveStrategy()),
        Player("Aggressive2", AggressiveStrategy()),
        Player("ValueTrader", ValueStrategy())
    ]
    
    game = GameController(players)
    game.run_simulation(num_rounds=5, actions_per_round=50, verbose=False)
    
    # Analyze results
    print("\n=== STRATEGY PERFORMANCE ANALYSIS ===")
    strategy_performance = {}
    
    for player in players:
        strategy = player.get_strategy_name()
        if strategy not in strategy_performance:
            strategy_performance[strategy] = []
        strategy_performance[strategy].append(player.dollars)
    
    for strategy, dollars_list in strategy_performance.items():
        avg_dollars = sum(dollars_list) / len(dollars_list)
        print(f"{strategy}: Average ${avg_dollars:.1f} (Players: {len(dollars_list)})")


def demo_market_maker_vs_others():
    """Demonstrate market maker strategy against other strategies"""
    print("\n=== MARKET MAKER STRATEGY DEMO ===\n")
    
    players = [
        Player("MarketMaker1", MarketMakerStrategy(target_spread=2, max_position=4)),
        Player("MarketMaker2", MarketMakerStrategy(target_spread=3, max_position=3)),
        Player("RandomTrader", RandomStrategy(action_probability=0.5)),
        Player("ValueTrader", ValueStrategy()),
        Player("AggressiveBot", AggressiveStrategy())
    ]
    
    game = GameController(players)
    game.run_simulation(num_rounds=2, actions_per_round=80, verbose=True)


def demo_information_strategy():
    """Demonstrate the information-based strategy"""
    print("\n=== INFORMATION STRATEGY DEMO ===\n")
    
    players = [
        Player("InfoBot1", InformationStrategy()),
        Player("InfoBot2", InformationStrategy()),
        Player("RandomBot", RandomStrategy(action_probability=0.3)),
        Player("Conservative", ConservativeStrategy()),
        Player("Aggressive", AggressiveStrategy())
    ]
    
    game = GameController(players)
    
    # Run with more actions to let information strategies learn
    game.run_simulation(num_rounds=2, actions_per_round=100, verbose=True)


def custom_strategy_tournament():
    """Run a tournament with custom strategy configurations"""
    print("\n=== CUSTOM STRATEGY TOURNAMENT ===\n")
    
    # Different configurations of the same strategy types
    players = [
        Player("FastRandom", RandomStrategy(action_probability=0.6)),
        Player("SlowRandom", RandomStrategy(action_probability=0.2)),
        Player("TightMM", MarketMakerStrategy(target_spread=1, max_position=2)),
        Player("WideMM", MarketMakerStrategy(target_spread=4, max_position=5)),
        Player("ValueBot", ValueStrategy())
    ]
    
    game = GameController(players)
    game.run_simulation(num_rounds=4, actions_per_round=70, verbose=False)
    
    # Show final tournament results
    print("\n=== TOURNAMENT RESULTS ===")
    sorted_players = sorted(players, key=lambda p: p.dollars, reverse=True)
    
    for i, player in enumerate(sorted_players, 1):
        print(f"{i}. {player.name} ({player.get_strategy_name()}): ${player.dollars}")


if __name__ == "__main__":
    # Run all demos
    demo_all_strategies()
    demo_strategy_comparison()
    demo_market_maker_vs_others()
    demo_information_strategy()
    custom_strategy_tournament()
    
    print("\n=== DEMO COMPLETE ===")
    print("You can modify the strategies or create new ones by:")
    print("1. Inheriting from TradingStrategy in strategies.py")
    print("2. Implementing decide_action() and get_strategy_name() methods")
    print("3. Adding your strategy to the demo scripts") 