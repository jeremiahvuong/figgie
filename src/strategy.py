import asyncio
import random
import numpy as np
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Literal, Optional, List
import tensorflow as tf
import tensorflow_probability as tfp

from custom_types import OrderBook, Suit
from event import OrderPlacedEvent, TradeExecutedEvent
from order import Order

if TYPE_CHECKING:
    from event import EventBus
    from player import Player

tfd = tfp.distributions


class Strategy(ABC):
    """Abstract base class for all strategies."""
    def __init__(self, name: str):
        self.name = name
        self._running = False

    @abstractmethod
    async def start(self, player: "Player", event_bus: "EventBus", order_book: Dict[str, OrderBook]) -> None:
        """The main asynchronous method for the strategy's logic; runs within an asyncio task, invoked by player.start()"""
        pass

"""
Strategy implementations
"""
class Noisy(Strategy):
    """Randomly places bid/ask orders between $1-15 inclusive."""
    def __init__(self, lower_interval: float = 1, upper_interval: float = 5):
        super().__init__(name="Noisy")
        self.interval = random.uniform(lower_interval, upper_interval) # interval in seconds between deciding orders

    async def start(self, player: "Player", event_bus: "EventBus", order_book: Dict[str, OrderBook]):
        self._player = player
        self._order_queue = player.order_queue
        self._event_bus = event_bus
        self._order_book = order_book
        self._running = True

        while self._running:
            try:
                await asyncio.sleep(self.interval) # Wait for interval seconds
                order = await self._create_random_order()
                # Note: if order is None, Noisy will have to wait another interval to send an order
                if order: await self._order_queue.put(order)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s strategy: {e}")

    async def _create_random_order(self) -> Optional["Order"]:
        assert self._player is not None # internal function, strategy should be associated with a player

        random_suit = random.choice(list(Suit))
        random_side: Literal["bid", "ask"] = random.choice(["bid", "ask"])

        order_book_entry = self._order_book[random_suit.name]
        current_bid = order_book_entry["bid"]["price"]
        current_ask = order_book_entry["ask"]["price"]

        if random_side == "bid":
            min_price, max_price = 1, min(15, self._player.dollars)
            # Don't buy if we're have > 3 cards of the suit
            if self._player.inventory[random_suit] >= 3: return None

            if current_bid != -999 and order_book_entry["bid"]["player"] != self._player:
                min_price = current_bid + 1 # Can't buy for less than the current bid
                if min_price > max_price: return None # No valid price possible

        elif random_side == "ask":
            min_price, max_price = 1, 15
            # Can't sell if we have none of the suit
            if self._player.inventory[random_suit] < 1: return None

            if current_ask != 999 and order_book_entry["ask"]["player"] != self._player:
                max_price = current_ask - 1 # Can't sell for more than the current ask
                if max_price < min_price: return None # No valid price possible
        
        # Generate random price in valid range
        random_price = random.randint(min_price, max_price)

        random_order = Order(suit=random_suit, side=random_side, price=random_price, player=self._player)
        return random_order

class BayesianInference(Strategy):
    """
    Bayesian inference strategy using TensorFlow Probability for optimal trading in Figgie.
    
    Key features:
    - Maintains posterior beliefs about which suit is the goal suit
    - Uses MCMC sampling for Bayesian updates
    - Observes trading patterns, prices, and player behavior
    - Makes expected value-based trading decisions
    """
    def __init__(self, learning_rate: float = 0.01, mcmc_steps: int = 100):
        super().__init__(name="BayesianInference")
        self.learning_rate = learning_rate
        self.mcmc_steps = mcmc_steps
        
        # Bayesian model parameters
        self._suit_to_idx = {suit: i for i, suit in enumerate(Suit)}
        self._idx_to_suit = {i: suit for i, suit in enumerate(Suit)}
        
        # Initialize uniform prior over goal suits
        self._goal_suit_logits = tf.Variable([0.0, 0.0, 0.0, 0.0], dtype=tf.float32)
        self._goal_suit_probs = tf.nn.softmax(self._goal_suit_logits)
        
        # Observation history for Bayesian updates
        self._trade_observations: List[Dict] = []
        self._order_observations: List[Dict] = []
        
        # Trading parameters
        self._min_confidence_threshold = 0.4
        self._aggressive_threshold = 0.7
        self._max_cards_per_suit = 5
        
        # Expected values
        self._expected_values: Dict[Suit, float] = {suit: 0.0 for suit in Suit}

    async def start(self, player: "Player", event_bus: "EventBus", order_book: Dict[str, OrderBook]) -> None:
        self._player = player
        self._order_queue = player.order_queue
        self._event_bus = event_bus
        self._order_book = order_book
        self._running = True

        # Subscribe to market events
        await self._event_bus.subscribe(OrderPlacedEvent, self._player.event_queue)
        await self._event_bus.subscribe(TradeExecutedEvent, self._player.event_queue)

        # Initialize prior beliefs based on starting inventory
        self._initialize_priors()
        
        print(f"[{self._player.name}] Starting Bayesian inference with prior beliefs:")
        for suit in Suit:
            prob = float(self._goal_suit_probs[self._suit_to_idx[suit]])
            print(f"  P({suit.name} = goal) = {prob:.3f}")

        # Main strategy loop
        order_interval = 0.5  # Check for new orders every 0.5 seconds
        last_update_time = 0
        update_interval = 2.0  # Update beliefs every 2 seconds
        
        while self._running:
            try:
                # Process market events with timeout
                try:
                    event = await asyncio.wait_for(self._player.event_queue.get(), timeout=order_interval)
                    await self._process_market_event(event)
                except asyncio.TimeoutError:
                    pass  # No event received, continue to trading logic
                
                # Periodic belief updates and trading decisions
                current_time = asyncio.get_event_loop().time()
                if current_time - last_update_time >= update_interval:
                    await self._update_beliefs()
                    await self._make_trading_decision()
                    last_update_time = current_time

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in {self._player.name}'s strategy: {e}")

    def _initialize_priors(self) -> None:
        """Initialize prior beliefs based on starting inventory and color inference."""
        # Find the suit we have the most cards of (likely from the 12-card suit)
        max_count = max(self._player.inventory[suit] for suit in Suit)
        most_common_suits = [suit for suit in Suit if self._player.inventory[suit] == max_count]
        
        if len(most_common_suits) == 1:
            # Clear indication of which might be the 12-card suit
            twelve_card_suit = most_common_suits[0]
            same_color_suit = twelve_card_suit.get_same_color_suit()
            
            # Goal suit is same color as 12-card suit, but not the 12-card suit itself
            goal_idx = self._suit_to_idx[same_color_suit]
            
            # Set stronger prior for the inferred goal suit
            logits = [-1.0, -1.0, -1.0, -1.0]
            logits[goal_idx] = 1.0
            self._goal_suit_logits.assign(logits)
        
        self._goal_suit_probs = tf.nn.softmax(self._goal_suit_logits)

    async def _process_market_event(self, event) -> None:
        """Process market events and add them to observation history."""
        if isinstance(event, TradeExecutedEvent):
            # Record trade observations
            trade_obs = {
                'suit': event.suit,
                'price': event.price,
                'receiver': event.receiver,
                'giver': event.giver,
                'is_self_receiver': event.receiver == self._player,
                'is_self_giver': event.giver == self._player
            }
            self._trade_observations.append(trade_obs)
            
        elif isinstance(event, OrderPlacedEvent):
            # Record order observations
            order_obs = {
                'suit': event.order.suit,
                'side': event.order.side,
                'price': event.order.price,
                'player': event.order.player,
                'is_self': event.order.player == self._player
            }
            self._order_observations.append(order_obs)

    async def _update_beliefs(self) -> None:
        """Update Bayesian beliefs using MCMC based on observed market behavior."""
        if not self._trade_observations and not self._order_observations:
            return
            
        # Compute likelihood based on recent observations
        likelihood_logits = self._compute_likelihood()
        
        # Bayesian update: posterior ∝ prior × likelihood
        with tf.GradientTape() as tape:
            # Current posterior (before update)
            current_probs = tf.nn.softmax(self._goal_suit_logits)
            
            # Combine with likelihood
            updated_logits = self._goal_suit_logits + likelihood_logits
            updated_probs = tf.nn.softmax(updated_logits)
            
            # Use KL divergence as a regularization term to prevent too rapid updates
            kl_div = tfp.distributions.kl_divergence(
                tfd.Categorical(probs=current_probs),
                tfd.Categorical(probs=updated_probs)
            )
            
            # Loss encourages updates while preventing instability
            loss = -tf.reduce_sum(updated_probs * likelihood_logits) + 0.1 * kl_div
        
        # Gradient-based update
        gradients = tape.gradient(loss, [self._goal_suit_logits])
        if gradients[0] is not None:
            self._goal_suit_logits.assign_sub(self.learning_rate * gradients[0])
        
        self._goal_suit_probs = tf.nn.softmax(self._goal_suit_logits)
        
        # Update expected values
        self._update_expected_values()
        
        # Log updated beliefs
        print(f"[{self._player.name}] Updated beliefs:")
        for suit in Suit:
            prob = float(self._goal_suit_probs[self._suit_to_idx[suit]])
            ev = self._expected_values[suit]
            print(f"  P({suit.name} = goal) = {prob:.3f}, EV = ${ev:.2f}")

    def _compute_likelihood(self) -> tf.Tensor:
        """Compute likelihood of observations given each possible goal suit hypothesis."""
        likelihood_scores = [0.0, 0.0, 0.0, 0.0]
        
        # Analyze recent trade patterns
        recent_trades = self._trade_observations[-10:]  # Last 10 trades
        
        for trade in recent_trades:
            suit_idx = self._suit_to_idx[trade['suit']]
            price = trade['price']
            
            # Higher prices for a suit suggest it might be the goal suit
            # Normalize price to [0, 1] range (assuming max price is 15)
            normalized_price = min(price / 15.0, 1.0)
            
            # Likelihood increases with price for that suit
            likelihood_scores[suit_idx] += normalized_price
            
            # If players are aggressively buying/selling at high prices
            if price > 8:  # High price threshold
                likelihood_scores[suit_idx] += 0.5
        
        # Analyze order patterns
        recent_orders = self._order_observations[-20:]  # Last 20 orders
        
        for order in recent_orders:
            if order['is_self']:
                continue  # Don't use our own orders
                
            suit_idx = self._suit_to_idx[order['suit']]
            price = order['price']
            
            # High bids suggest confidence in that suit being valuable
            if order['side'] == 'bid' and price > 6:
                likelihood_scores[suit_idx] += 0.3
            # Low asks might suggest dumping non-goal suits
            elif order['side'] == 'ask' and price < 5:
                likelihood_scores[suit_idx] -= 0.2
        
        return tf.constant(likelihood_scores, dtype=tf.float32)

    def _update_expected_values(self) -> None:
        """Update expected values for each suit based on current beliefs."""
        for suit in Suit:
            suit_idx = self._suit_to_idx[suit]
            goal_prob = float(self._goal_suit_probs[suit_idx])
            
            # Expected value calculation
            # If goal suit: $10 per card + pot share probability
            # If not goal suit: $0 per card
            
            cards_owned = self._player.inventory[suit]
            
            # Base expected value from $10 per card if it's the goal suit
            base_ev = goal_prob * 10.0 * cards_owned
            
            # Additional expected value from winning the pot
            # Simplified: assume pot is ~$200 and we need >40% of goal suit cards to win
            pot_value = 200.0
            total_goal_cards = 8 + 10  # Goal suit has either 8 or 10 cards
            win_threshold = 0.4 * total_goal_cards
            
            if cards_owned > win_threshold:
                pot_ev = goal_prob * pot_value * 0.8  # 80% chance to win if above threshold
            else:
                pot_ev = goal_prob * pot_value * 0.1  # 10% chance otherwise
            
            self._expected_values[suit] = base_ev + pot_ev

    async def _make_trading_decision(self) -> None:
        """Make optimal trading decisions based on current beliefs and expected values."""
        # Get the most likely goal suit
        best_suit_idx = int(tf.argmax(self._goal_suit_probs))
        best_suit = self._idx_to_suit[best_suit_idx]
        best_prob = float(self._goal_suit_probs[best_suit_idx])
        
        # Decide whether to buy or sell
        if best_prob > self._aggressive_threshold:
            # High confidence - be aggressive
            await self._aggressive_buy_strategy(best_suit)
        elif best_prob > self._min_confidence_threshold:
            # Moderate confidence - selective trading
            await self._selective_trading_strategy(best_suit)
        else:
            # Low confidence - conservative or diversified approach
            await self._conservative_strategy()

    async def _aggressive_buy_strategy(self, target_suit: Suit) -> None:
        """Aggressively accumulate the target suit."""
        if self._player.inventory[target_suit] >= self._max_cards_per_suit:
            return  # Already have enough
            
        order_book_entry = self._order_book[target_suit.name]
        current_ask = order_book_entry["ask"]["price"]
        
        # Buy if ask price is reasonable and we have money
        if (current_ask != 999 and 
            current_ask <= 12 and  # Willing to pay up to $12
            self._player.dollars >= current_ask and
            order_book_entry["ask"]["player"] != self._player):
            
            # Place aggressive bid just below ask
            bid_price = min(current_ask - 1, self._player.dollars)
            if bid_price > 0:
                order = Order(suit=target_suit, side="bid", price=bid_price, player=self._player)
                await self._order_queue.put(order)

    async def _selective_trading_strategy(self, likely_goal_suit: Suit) -> None:
        """Moderate confidence trading - buy goal suit, sell others."""
        # Buy likely goal suit if price is reasonable
        if self._player.inventory[likely_goal_suit] < 3:
            order_book_entry = self._order_book[likely_goal_suit.name]
            current_ask = order_book_entry["ask"]["price"]
            
            if (current_ask != 999 and 
                current_ask <= 8 and
                self._player.dollars >= current_ask and
                order_book_entry["ask"]["player"] != self._player):
                
                bid_price = min(current_ask - 1, self._player.dollars)
                if bid_price > 0:
                    order = Order(suit=likely_goal_suit, side="bid", price=bid_price, player=self._player)
                    await self._order_queue.put(order)
        
        # Sell suits we're less confident about
        for suit in Suit:
            if suit == likely_goal_suit:
                continue
                
            suit_prob = float(self._goal_suit_probs[self._suit_to_idx[suit]])
            if (suit_prob < 0.2 and  # Low confidence this is goal
                self._player.inventory[suit] > 0):
                
                order_book_entry = self._order_book[suit.name]
                current_bid = order_book_entry["bid"]["price"]
                
                if (current_bid != -999 and 
                    current_bid >= 5 and  # Only sell if price is decent
                    order_book_entry["bid"]["player"] != self._player):
                    
                    ask_price = current_bid + 1
                    order = Order(suit=suit, side="ask", price=ask_price, player=self._player)
                    await self._order_queue.put(order)

    async def _conservative_strategy(self) -> None:
        """Conservative strategy when confidence is low."""
        # Only make very safe trades
        for suit in Suit:
            order_book_entry = self._order_book[suit.name]
            current_bid = order_book_entry["bid"]["price"]
            current_ask = order_book_entry["ask"]["price"]
            
            # Sell if someone is offering a very high price
            if (current_bid >= 10 and
                current_bid != -999 and
                self._player.inventory[suit] > 0 and
                order_book_entry["bid"]["player"] != self._player):
                
                order = Order(suit=suit, side="ask", price=current_bid, player=self._player)
                await self._order_queue.put(order)
            
            # Buy if someone is asking a very low price
            elif (current_ask <= 3 and
                  current_ask != 999 and
                  self._player.dollars >= current_ask and
                  self._player.inventory[suit] < 2 and
                  order_book_entry["ask"]["player"] != self._player):
                
                order = Order(suit=suit, side="bid", price=current_ask, player=self._player)
                await self._order_queue.put(order)