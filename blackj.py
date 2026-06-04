import random
from fns import *
class Blackjackclass():
    # Blackjack values for cards
    def __init__(self,user_id,bet):
        self.user_id = user_id
        self.bet = bet
        self.user_hand = []
        self.bot_hand = []
        self.user_value = 0
        self.bot_value = 0
    def create_deck(self):
        suits = ["Spades", "Hearts", "Diamonds", "Clubs"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "Jack", "Queen", "King", "Ace"]
        self.deck = [f"{rank}_of_{suit}" for suit in suits for rank in ranks]
        random.shuffle(self.deck)
    def calculate_score(self, hand):
        card_values = {
                "2": 2, "3": 3, "4": 4, "5": 5,
                "6": 6, "7": 7, "8": 8, "9": 9,
                "10": 10, "Jack": 10, "Queen": 10, "King": 10, "Ace": 11  
            }
        score = 0
        aces = 0
        for card in hand:
            rank = card.split('_')[0]
            value = card_values[rank]   
            score += value
            if rank == "Ace":
                aces +=1
        while score>21 and aces and len(hand)==2:
            score -= 10
            aces -= 1
        return score
    def pick_hand(self):
        self.user_hand = [self.deck.pop(), self.deck.pop()]
        self.user_value = self.calculate_score(self.user_hand)
        self.bot_hand = [self.deck.pop(), self.deck.pop()]
        while self.calculate_score(self.bot_hand) < 17:
            self.bot_hand.append(self.deck.pop())
        self.bot_value = self.calculate_score(self.bot_hand)
    def draw(self):
        self.user_hand.append(self.deck.pop())
        self.user_value = self.calculate_score(self.user_hand)
    def check_result(self, guild_id: int):
        try:
            if self.user_value > 21:
                glob_fns().update_balance(self.user_id,self.bet,guild_id,True)
                return "Busted!"
            if self.bot_value > 21:
                glob_fns().update_balance(self.user_id,self.bet,guild_id,False)
                return "Won"
            if self.user_value > self.bot_value:
                glob_fns().update_balance(self.user_id,self.bet,guild_id,False)
                return "Won"
            if self.user_value == self.bot_value:
                return "Drew"
            glob_fns().update_balance(self.user_id,self.bet,guild_id,True)
            return "Lost"
        except Exception as e:
            print(f"❌ check_result crash: {type(e).__name__}: {e}")
            return "Error processing game"
    def is_blackjack(self,hand):
        ranks = [card.split("_")[0] for card in hand]
        return "Ace" in ranks and any(face in ranks for face in ["10", "Jack", "Queen", "King"])
    def init_game(self):
        self.create_deck()
        self.pick_hand()