import asyncio
import websockets
import json
import random

class Game:
    def __init__(self):
        self.board = [[None for _ in range(5)] for _ in range(5)]
        self.current_player = 'A'
        self.players = {'A': [], 'B': []}
        self.connections = {}

    def initialize_board(self):
        for player in ['A', 'B']:
            characters = ['P1', 'P2', 'P3', 'H1', 'H2']
            random.shuffle(characters)
            row = 0 if player == 'A' else 4
            for col, char in enumerate(characters):
                self.board[row][col] = f"{player}-{char}"
                self.players[player].append(f"{char}")

    def validate_move(self, player, character, move):
        if player != self.current_player:
            return False
        if character not in self.players[player]:
            return False
        
        char_type = character[0]
        row, col = self.find_character(f"{player}-{character}")
        
        if char_type == 'P':
            if move == 'L': col -= 1
            elif move == 'R': col += 1
            elif move == 'F': row += (-1 if player == 'A' else 1)
            elif move == 'B': row += (1 if player == 'A' else -1)
            else: return False
        elif char_type == 'H':
            if character[1] == '1':
                if move == 'L': col -= 2
                elif move == 'R': col += 2
                elif move == 'F': row += (-2 if player == 'A' else 2)
                elif move == 'B': row += (2 if player == 'A' else -2)
                else: return False
            elif character[1] == '2':
                if move == 'FL': row += (-2 if player == 'A' else 2); col -= 2
                elif move == 'FR': row += (-2 if player == 'A' else 2); col += 2
                elif move == 'BL': row += (2 if player == 'A' else -2); col -= 2
                elif move == 'BR': row += (2 if player == 'A' else -2); col += 2
                else: return False

        if not (0 <= row < 5 and 0 <= col < 5):
            return False
        
        target = self.board[row][col]
        if target and target.startswith(player):
            return False

        return True

    def apply_move(self, player, character, move):
        old_row, old_col = self.find_character(f"{player}-{character}")
        self.board[old_row][old_col] = None

        char_type = character[0]
        row, col = old_row, old_col
        
        if char_type == 'P':
            if move == 'L': col -= 1
            elif move == 'R': col += 1
            elif move == 'F': row += (-1 if player == 'A' else 1)
            elif move == 'B': row += (1 if player == 'A' else -1)
        elif char_type == 'H':
            if character[1] == '1':
                if move == 'L': col -= 2
                elif move == 'R': col += 2
                elif move == 'F': row += (-2 if player == 'A' else 2)
                elif move == 'B': row += (2 if player == 'A' else -2)
            elif character[1] == '2':
                if move == 'FL': row += (-2 if player == 'A' else 2); col -= 2
                elif move == 'FR': row += (-2 if player == 'A' else 2); col += 2
                elif move == 'BL': row += (2 if player == 'A' else -2); col -= 2
                elif move == 'BR': row += (2 if player == 'A' else -2); col += 2

        target = self.board[row][col]
        if target:
            opponent = 'B' if player == 'A' else 'A'
            self.players[opponent].remove(target.split('-')[1])

        self.board[row][col] = f"{player}-{character}"
        self.current_player = 'B' if player == 'A' else 'A'

    def find_character(self, char):
        for i, row in enumerate(self.board):
            if char in row:
                return i, row.index(char)
        return -1, -1

    def check_winner(self):
        if not self.players['A']:
            return 'B'
        if not self.players['B']:
            return 'A'
        return None

    def get_state(self):
        return {
            'board': self.board,
            'current_player': self.current_player,
            'players': self.players
        }

game = Game()

async def handle_client(websocket, path):
    player = 'A' if len(game.connections) == 0 else 'B'
    game.connections[player] = websocket
    try:
        if len(game.connections) == 2:
            game.initialize_board()
            await broadcast_state()

        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'move':
                if game.validate_move(player, data['character'], data['move']):
                    game.apply_move(player, data['character'], data['move'])
                    winner = game.check_winner()
                    if winner:
                        await broadcast_message({'type': 'game_over', 'winner': winner})
                    else:
                        await broadcast_state()
                else:
                    await websocket.send(json.dumps({'type': 'invalid_move'}))
    finally:
        del game.connections[player]

async def broadcast_state():
    message = json.dumps({'type': 'state_update', 'state': game.get_state()})
    await broadcast_message(message)

async def broadcast_message(message):
    for connection in game.connections.values():
        await connection.send(json.dumps(message))

start_server = websockets.serve(handle_client, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()