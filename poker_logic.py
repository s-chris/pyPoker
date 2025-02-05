import random
import itertools
from enum import Enum

class Suit(Enum):
    HEARTS = "♥"
    DIAMONDS = "♦"
    CLUBS = "♣"
    SPADES = "♠"

class Rank(Enum):
    TWO = (2, "2")
    THREE = (3, "3")
    FOUR = (4, "4")
    FIVE = (5, "5")
    SIX = (6, "6")
    SEVEN = (7, "7")
    EIGHT = (8, "8")
    NINE = (9, "9")
    TEN = (10, "T")
    JACK = (11, "J")
    QUEEN = (12, "Q")
    KING = (13, "K")
    ACE = (14, "A")

    def __lt__(self, other):
        return self.value[0] < other.value[0]

# Add to PokerGame class
class GamePhase(Enum):
    PREFLOP = "Pre-flop"
    FLOP = "Flop"
    TURN = "Turn"
    RIVER = "River"
    SHOWDOWN = "Showdown"


    def __lt__(self, other):
        return self.value[0] < other.value[0]

class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit

    def __repr__(self):
        return f"{self.rank.value[1]}{self.suit.value}"

class HandStrength:
    def __init__(self, strength, ranks, kickers=[]):
        self.strength = strength
        self.ranks = ranks
        self.kickers = kickers

    def __lt__(self, other):
        if self.strength == other.strength:
            if self.ranks == other.ranks:
                return self.kickers < other.kickers
            return self.ranks < other.ranks
        return self.strength < other.strength

    def __eq__(self, other):
        return (self.strength == other.strength and 
                self.ranks == other.ranks and 
                self.kickers == other.kickers)

class Player:
    def __init__(self, name, chips=1000, ai_level=1):
        self.name = name
        self.chips = chips
        self.hand = []
        self.ai_level = ai_level
        self.current_bet = 0

    def __repr__(self):
        return f"{self.name} ({self.chips} chips)"

class HandEvaluator:
    @staticmethod
    def evaluate_hand(hole_cards, community_cards):
        all_cards = hole_cards + community_cards
        all_combinations = itertools.combinations(all_cards, 5)
        
        best_hand = None
        for combo in all_combinations:
            hand_strength = HandEvaluator._evaluate_combo(combo)
            if not best_hand or hand_strength > best_hand:
                best_hand = hand_strength
        return best_hand

    @staticmethod
    def _evaluate_combo(combo):
        ranks = sorted([card.rank.value[0] for card in combo], reverse=True)
        suits = [card.suit for card in combo]
        
        # Count occurrences
        rank_counts = {rank: ranks.count(rank) for rank in set(ranks)}
        flush = len(set(suits)) == 1
        straight = (max(ranks) - min(ranks) == 4 and len(set(ranks)) == 5) or \
                   (ranks == [14, 5, 4, 3, 2])
        
        # Determine hand strength
        if straight and flush:
            if max(ranks) == 14: return (9, ranks)  # Royal flush
            return (8, [max(ranks)])  # Straight flush
        if 4 in rank_counts.values():
            quad_rank = [k for k,v in rank_counts.items() if v==4][0]
            return (7, [quad_rank], [k for k in ranks if k != quad_rank])
        if len(rank_counts) == 2 and 3 in rank_counts.values():
            trip_rank = [k for k,v in rank_counts.items() if v==3][0]
            pair_rank = [k for k,v in rank_counts.items() if v==2][0]
            return (6, [trip_rank, pair_rank])
        if flush:
            return (5, ranks)
        if straight:
            return (4, [max(ranks)])
        if 3 in rank_counts.values():
            trip_rank = [k for k,v in rank_counts.items() if v==3][0]
            return (3, [trip_rank], ranks)
        if list(rank_counts.values()).count(2) == 2:
            pairs = sorted([k for k,v in rank_counts.items() if v==2], reverse=True)
            return (2, pairs, ranks)
        if 2 in rank_counts.values():
            pair_rank = [k for k,v in rank_counts.items() if v==2][0]
            return (1, [pair_rank], ranks)
        return (0, ranks)


class PokerGame:
    def __init__(self, players):
         # Add these initializations
        self.current_player = None
        self.current_player_index = 0
        self.active_players = []
        
        # Existing initialization code
        self.current_phase = GamePhase.PREFLOP
        self.phase_order = [
            GamePhase.PREFLOP,
            GamePhase.FLOP,
            GamePhase.TURN,
            GamePhase.RIVER,
            GamePhase.SHOWDOWN
        ]
        self.players = players
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.small_blind = 50
        self.big_blind = 100
        self.dealer_position = 0
        self.new_deck()
       

    def start_new_hand(self):
        ## Initialize a new hand of poker

        # Reset game state
        self.new_deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        
        # Reset player states
        for player in self.players:
            player.hand = []
            player.folded = False
            player.current_bet = 0
        
         # Initialize active players
        self.active_players = [p for p in self.players if p.chips > 0]

        # Set initial player rotation
        if self.active_players:
            self.current_player_index = 0
            self.current_player = self.active_players[self.current_player_index]

              
        # Post blinds and set initial game state
        self.active_players = [p for p in self.players if p.chips > 0]
        self.current_phase = GamePhase.PREFLOP
        self.current_player_index = (self.dealer_position + 3) % len(self.active_players)
        self.current_player = self.active_players[self.current_player_index]

        # Post blinds and deal cards
        self._post_blinds()
        self.deal_hole_cards()

    def _post_blinds(self):
        ### Handle small/big blind posting
        if len(self.active_players) >= 2:
            sb_player = self.active_players[(self.dealer_position + 1) % len(self.active_players)]
            bb_player = self.active_players[(self.dealer_position + 2) % len(self.active_players)]
            
            sb_player.chips -= self.small_blind
            bb_player.chips -= self.big_blind
            self.pot = self.small_blind + self.big_blind
            self.current_bet = self.big_blind

    def new_round(self):
       # Reset player states
        for p in self.players:
            p.folded = False
            p.current_bet = 0
        
        # Reset game state
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.deck = self.new_deck()
        self.deal_hole_cards()
        self.current_phase = GamePhase.PREFLOP

        # Post blinds only if enough players
        if len(self.active_players) >= 2:
            self.dealer_position = (self.dealer_position + 1) % len(self.active_players)
            sb_index = (self.dealer_position + 1) % len(self.active_players)
            bb_index = (self.dealer_position + 2) % len(self.active_players)
            
            sb = self.active_players[sb_index]
            bb = self.active_players[bb_index]
            
            sb.chips -= self.small_blind
            bb.chips -= self.big_blind
            self.pot = self.small_blind + self.big_blind
            self.current_bet = self.big_blind

        self.current_player_index = (self.dealer_position + 3) % len(self.active_players)

    def betting_round(self):
        if not self.active_players:
            return

        # Start with first active player after big blind
        self.current_player_index = 0
        last_raise_index = -1
        players_acted = 0
        needs_to_act = len([p for p in self.active_players if not p.folded])

        while True:
            if not self.active_players:
                break

            # Rotate through active players
            current_player = self.active_players[self.current_player_index % len(self.active_players)]
            
            if current_player.folded:
                self.current_player_index += 1
                continue

            # Get player action (AI or human)
            action = self.get_player_action(current_player)
            
            if action == 'raise':
                last_raise_index = self.current_player_index
                players_acted = 0
            elif action == 'fold':
                current_player.folded = True
                needs_to_act -= 1

            players_acted += 1
            self.current_player_index += 1

            # End betting when all players have acted and no raises remain
            if players_acted >= needs_to_act and self.current_player_index > last_raise_index:
                break

            # Check if only one player remains
            if len([p for p in self.active_players if not p.folded]) <= 1:
                break

    def advance_phase(self):
        phases = list(GamePhase)
        current_index = phases.index(self.current_phase)
        if current_index < len(phases) - 1:
            self.current_phase = phases[current_index + 1]
            
            if self.current_phase == GamePhase.FLOP:
                self.deal_community_cards(3)
            elif self.current_phase in [GamePhase.TURN, GamePhase.RIVER]:
                self.deal_community_cards(1)

    def new_deck(self):
        ##  Create and shuffle a new deck
        self.deck = [Card(rank, suit) for suit in Suit for rank in Rank]
        random.shuffle(self.deck)
        self.community_cards = []

    def deal_hole_cards(self):
        ## Deal 2 private cards to each player
        print(f"Dealing cards from deck size: {len(self.deck)}")
        for _ in range(2):  # Deal two cards
            for player in self.active_players:
                if len(self.deck) < 1:
                    raise ValueError("Not enough cards in deck")
                player.hand.append(self.deck.pop())

    def deal_community_cards(self, num=1):
        if not self.active_players:
            return
        
        for _ in range(num):
            self.community_cards.append(self.deck.pop())

    def evaluate_hand(self, player):
        all_cards = player.hand + self.community_cards
        return self._evaluate(all_cards)

    def _evaluate(self, cards):
        # Convert ranks to their numerical values
        ranks = sorted([card.rank.value[0] for card in cards], reverse=True)
        return HandStrength(0, ranks)

    def ai_decision(self, player):
        if player.ai_level == 1:
            return random.choice(['fold', 'call', 'raise'])
        elif player.ai_level == 2:
            hand_strength = self.evaluate_hand(player)
            if hand_strength.strength > 3 or random.random() < 0.7:
                return random.choice(['call', 'raise'])
            else:
                return 'fold'
        else:
            # Advanced AI logic
            return 'call'

    def betting_round(self, start_player_index=0):

        if not self.active_players:
            return
        
        active_players = [p for p in self.active_players if p.chips > 0]
        current_player = start_player_index
        num_players = len(active_players)
        round_complete = False

        while not round_complete:
            player = active_players[current_player]
            if player.current_bet < self.current_bet:
                if player.ai_level > 0:
                    decision = self.ai_decision(player)
                    if decision == 'fold':
                        active_players.remove(player)
                    elif decision == 'call':
                        diff = self.current_bet - player.current_bet
                        player.chips -= diff
                        self.pot += diff
                        player.current_bet = self.current_bet
                    elif decision == 'raise':
                        diff = self.current_bet - player.current_bet + 10
                        player.chips -= diff
                        self.pot += diff
                        self.current_bet += 10
                        player.current_bet = self.current_bet
                else:
                    # Human player input
                    print(f"Current bet: {self.current_bet}, Your chips: {player.chips}")
                    action = input("Choose action (fold, call, raise): ")
                    # Handle human input
            else:
                # Player has already matched current bet
                pass

            current_player = (current_player + 1) % num_players
            if all(p.current_bet == self.current_bet for p in active_players):
                round_complete = True

    def play_round(self):

        if not self.active_players:
            return

        self.new_deck()
        self.deal_hole_cards()
        self.betting_round()
        
        self.deal_community_cards(3)  # Flop
        self.betting_round()
        
        self.deal_community_cards(1)  # Turn
        self.betting_round()
        
        self.deal_community_cards(1)  # River
        self.betting_round()

        # Showdown
        active_players = [p for p in self.players if p.chips > 0]
        best_hand = None
        winner = None
        for player in active_players:
            hand_strength = self.evaluate_hand(player)
            if not best_hand or hand_strength > best_hand:
                best_hand = hand_strength
                winner = player
        winner.chips += self.pot
        print(f"Winner: {winner.name} with {best_hand.strength}")
     
    def determine_winners(self):
        active_players = [p for p in self.players if not p.folded]
        if len(active_players) == 1:
            return [active_players[0]]
        
        evaluations = []
        for player in active_players:
            strength = HandEvaluator.evaluate_hand(player.hand, self.community_cards)
            evaluations.append((player, strength))
        
        evaluations.sort(key=lambda x: x[1], reverse=True)
        best_strength = evaluations[0][1]
        return [p for p, s in evaluations if s == best_strength]

