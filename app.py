# app.py (Backend)
from enum import Enum
from flask import Flask, render_template, request, session
from flask_socketio import SocketIO, emit, join_room
import uuid
from poker_logic import PokerGame, Player, GamePhase  # Import your existing game logic
from threading import Lock

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

games = {}
game_lock = Lock()



class WebPlayer(Player):
    def __init__(self, sid, name, chips=1000, ai_level=0):
        super().__init__(name, chips, ai_level)
        self.sid = sid
        self.is_ai = False


class GameSession:

    def __init__(self, game_id, num_ai):
        self.game_id = game_id
        self.players = []
        self.ai_count = num_ai
        self.game = None  # Changed from empty PokerGame to None
        self.started = False  # Add game status flag
        
    def add_human(self, sid, name):
        if len(self.players) + self.ai_count > 10:
            return False
        player = WebPlayer(sid, name)
        self.players.append(player)
        return True

    # def start_game(self):
    #     # Only create AI players after human joins
    #     for i in range(self.ai_count):
    #         self.players.append(Player(f"AI {i+1}", ai_level=1))
        
    #         # Reinitialize game with actual players
    #         self.game = PokerGame(self.players)
    #         self.game.new_deck()
    #         self.game.deal_hole_cards()

    def start_game(self):
        # Create AI players first
        for i in range(self.ai_count):
            self.players.append(Player(f"AI {i+1}", ai_level=1))
        
        # Initialize game with validated players
        self.game = PokerGame(self.players)  # start_new_hand is called automatically in __init__
        self.game.current_player = self.game.players[0]
        self.started = True
     

    def get_game_state(self, for_player=None):
        with game_lock:
            state = {
                'current_player': None,
                'phase': 'Waiting to Start',
                'community_cards': [],
                'pot': 0,
                'players': [],
                'current_bet': 0,
                'is_player_turn': False,
                'player_chips': 0
            }
            
            if self.game:
                state['current_player'] = self.game.current_player.name if self.game.current_player else None

                state['phase'] = self.game.current_phase.value
                 # Add actual game data
                state.update({
                    'community_cards': [str(c) for c in self.game.community_cards],
                    'pot': self.game.pot,
                    'phase': self.game.current_phase.value,
                    'current_bet': self.game.current_bet,
                    'current_player': self.game.current_player.name if self.game.current_player else None
                })
                
                # Add proper player states
                for p in self.game.players:
                    player_state = {
                        'name': p.name,
                        'chips': p.chips,
                        'current_bet': p.current_bet,
                        'hand': [str(c) for c in p.hand] if p == for_player else ['XX']*2,
                        'is_ai': p.ai_level > 0
                    }
                    state['players'].append(player_state)
                    
                    if p == for_player:
                        state['is_player_turn'] = (self.game.current_player == p)
                        state['player_chips'] = p.chips
            
            return state


@app.route('/')
def index():
    return render_template('lobby.html')

@app.route('/game/<game_id>')
def game(game_id):
    return render_template('game.html')

@socketio.on('create_game')
def handle_create_game(data):
    try:
        num_ai = int(data['num_ai'])
        if not 1 <= num_ai <= 9:
            raise ValueError("AI players must be between 1-9")
            
        game_id = str(uuid.uuid4())
        session = GameSession(game_id, num_ai)
        games[game_id] = session
        
        # Add temporary human player placeholder
        session.players.append(Player("Human", ai_level=0))
        session.start_game()
        
        emit('game_created', {'game_id': game_id})
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('join_game')
def handle_join_game(data):

    try: 
        game_id = data['game_id']
        name = data['name']
        session = games.get(game_id)
        
        if session:
        # Replace temporary human placeholder
            human_player = next((p for p in session.players if p.name == "Human"), None)

            if human_player:
                human_player.name = name
                human_player.sid = request.sid
                join_room(game_id)
                session.start_game()
                emit('game_update', session.get_game_state(human_player), room=game_id)
            else:
                emit('error', {'message': 'Game is full'})

    except Exception as e:
        print(f"Error: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('start_game')
def handle_start_game(data):
    game_id = data['game_id']
    session = games.get(game_id)
    if session and not session.started:
        session.start_game()
        session.started = True # set the game status to started
        emit('game_update', session.get_game_state(), room=game_id)

@socketio.on('player_action')
def handle_player_action(data):
    game_id = data['game_id']
    session = games.get(game_id)
    
    if session and session.game:
        player = next((p for p in session.players if p.sid == request.sid), None)
        
        # Handle action
        if data['action'] == 'fold':
            player.folded = True
        elif data['action'] == 'call':
            amount = session.game.current_bet - player.current_bet
            player.chips -= amount
            player.current_bet += amount
            session.pot += amount
        elif data['action'] == 'raise':
            amount = data['amount']
            player.chips -= amount
            player.current_bet += amount
            session.game.current_bet = player.current_bet
            session.pot += amount
        
        # Check round completion
        if session.game.betting_round_complete():
            session.game.advance_phase()
            if session.game.current_phase == GamePhase.SHOWDOWN:
                winners = session.game.determine_winners()
                for winner in winners:
                    winner.chips += session.pot // len(winners)
                emit('game_result', {
                    'winners': [w.name for w in winners],
                    'pot': session.pot
                }, room=game_id)

                session.game.new_round()
            else:
                session.game.betting_round()

        emit('game_update', session.get_game_state(), room=game_id)

if __name__ == '__main__':
    socketio.run(app, debug=True)