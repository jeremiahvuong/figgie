import asyncio
from custom_types import Suit
from game_controller import GameController
from order import Order
from player import Player
from event import TradeExecutedEvent


# Event handler for trade events
async def handle_trade_event(trade_event: TradeExecutedEvent):
    print(f"🎉 TRADE EVENT DETECTED:")
    print(f"   Giver: {trade_event.giver.name} (sold {trade_event.suit.name})")
    print(f"   Receiver: {trade_event.receiver.name} (bought {trade_event.suit.name})")
    print(f"   Price: ${trade_event.price}")
    print(f"   Suit: {trade_event.suit.name}")
    print("   ---")

# Subscriber queue for trade events
trade_event_queue: asyncio.Queue[TradeExecutedEvent] = asyncio.Queue()

async def event_processor():
    """Background task to process trade events"""
    while True:
        try:
            trade_event = await trade_event_queue.get()
            await handle_trade_event(trade_event)
        except asyncio.CancelledError:
            break

async def main():
    p1 = Player("John")
    p2 = Player("Erick")
    p3 = Player("Jane")
    p4 = Player("Jim")
    p5 = Player("Jill")

    game = GameController([p1, p2, p3, p4, p5])
    
    # Subscribe to trade events
    await game.event_bus.subscribe(TradeExecutedEvent, trade_event_queue)

    # Start the event processor in the background
    event_task = asyncio.create_task(event_processor())

    print("=== Testing Trade Events ===")
    
    # Test 1: Create orders that will trigger a trade
    print("\n1. Setting up orders that will trigger trades...")
    await game.add_order(Order(Suit.hearts, "ask", 10, p1)) # John sells hearts for 10
    await game.add_order(Order(Suit.hearts, "bid", 10, p2)) # Erick buys hearts for 10 - TRADE!

    await asyncio.sleep(1)

    # Test 2: Another trade with different suit
    print("\n2. Testing another trade...")
    await game.add_order(Order(Suit.spades, "ask", 15, p3)) # Jane sells spades for 15
    await game.add_order(Order(Suit.spades, "bid", 15, p4)) # Jim buys spades for 15 - TRADE!

    await asyncio.sleep(1)
    
    # Test 3: Cross the spread (bid higher than ask)
    print("\n3. Testing crossing the spread...")
    await game.add_order(Order(Suit.diamonds, "ask", 8, p1)) # John sells diamonds for 8
    await game.add_order(Order(Suit.diamonds, "bid", 12, p2)) # Erick bids 12 (higher than 8) - TRADE at 8!

    await asyncio.sleep(1)

    # Test 4: Non-matching orders (no trade)
    print("\n4. Testing non-matching orders (no trade expected)...")
    await game.add_order(Order(Suit.clubs, "ask", 20, p3)) # Jane sells clubs for 20
    await game.add_order(Order(Suit.clubs, "bid", 15, p4)) # Jim bids 15 (lower than 20) - NO TRADE
    
    # Give some time for events to be processed
    await asyncio.sleep(0.1)
    
    # Cancel the event processor
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass

    game.end_round()
    game.print_orderbook()

if __name__ == "__main__":
    asyncio.run(main())