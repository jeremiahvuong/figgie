#!/usr/bin/env python3
"""
Quick demo of the time-based Figgie trading game.
Runs a 30-second trading session to demonstrate the new timing features.
"""

from main import GameController, Player
from strategies import RandomStrategy, ConservativeStrategy, AggressiveStrategy, ValueStrategy

def quick_demo():
    """Run a quick 30-second demo of time-based trading"""
    print("=== FIGGIE QUICK DEMO: 30-Second Trading Session ===\n")
    
    # Create players with different strategies
    players = [
        Player("FastBot", RandomStrategy(action_probability=0.6)),
        Player("Thinker", ConservativeStrategy()),
        Player("Speedy", AggressiveStrategy()),
        Player("Analyst", ValueStrategy()),
        Player("Casual", RandomStrategy(action_probability=0.3))
    ]
    
    print("Players and their thinking patterns:")
    print("- FastBot (Random): Quick decisions (0.2-1.5s)")
    print("- Thinker (Conservative): Careful consideration (1.5-4.0s)")
    print("- Speedy (Aggressive): Fast reactions (0.3-1.0s)")
    print("- Analyst (Value): Calculated moves (1.0-3.5s)")
    print("- Casual (Random): Relaxed pace (0.2-1.5s)")
    print()
    
    # Create game
    game = GameController(players)
    
    print(f"Goal suit: {game._goal_suit.name if game._goal_suit else 'Unknown'}")
    print(f"12-card suit: {game._suit_12.name if game._suit_12 else 'Unknown'}")
    print()
    
    # Run a 30-second trading session
    game.run_trading_round(duration_minutes=0.5, verbose=True)  # 30 seconds
    
    # Show final results
    game.print_orderbook()
    game.end_round()
    game.print_final_standings()

if __name__ == "__main__":
    quick_demo() 