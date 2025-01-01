# TODO: Implement Qiskit for superposition
# TODO: Implement entaglment
# TODO: Make it modular, package the code
# TODO: Tests
# TODO: Only classical moves when king in check

import sys
import time
import random
from threading import Timer

from os import environ
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
pygame.init()

# Constants
WINDOW_SIZE = 800
BOARD_SIZE = 8
SQUARE_SIZE = WINDOW_SIZE // BOARD_SIZE

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
HIGHLIGHT = (255, 255, 0, 128)
MOVE_HIGHLIGHT = (0, 255, 0, 128)
QUANTUM_HIGHLIGHT = (0, 0, 255, 128)
QUANTUM_DOT = (255, 255, 0)
QUANTUM_SQUARE = (128, 0, 128, 128)
MENU_BG = (240, 240, 240)
MESSAGE_BG = (0, 0, 0, 180)
TIMER_COLOR = (255, 0, 0)
INSTRUCTION_BG = (0, 0, 0, 220)

# Pieces unicodes
PIECES = {
    'white': {
        'king': '\u2654', 
        'queen': '\u2655', 
        'rook': '\u2656',
        'bishop': '\u2657', 
        'knight': '\u2658', 
        'pawn': '\u2659'
    },
    'black': {
        'king': '\u265A', 
        'queen': '\u265B', 
        'rook': '\u265C',
        'bishop': '\u265D', 
        'knight': '\u265E', 
        'pawn': '\u265F'
    }
}

class QuantumState:
    def __init__(self, piece_type, color, pos1, pos2):
        self.piece_type = piece_type
        self.color = color
        self.positions = [pos1, pos2]
        self.timer = 90
        self.last_update = time.time()
        
    def update_timer(self):
        current_time = time.time()
        elapsed = current_time - self.last_update
        self.timer -= elapsed
        self.last_update = current_time
        return self.timer <= 0

    def collapse(self, position_index):
        return self.positions[position_index]


class ChessGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption('Quantum Chess')
        self.font = pygame.font.SysFont('segoeuisymbol', SQUARE_SIZE - 20)
        self.message_font = pygame.font.SysFont('times', 36)
        self.instruction_font = pygame.font.SysFont('arial', 22)
        self.show_instructions = True 
        self.reset()


    def reset(self):
        self.board = self.create_board()
        self.active_piece = None
        self.valid_moves = []
        self.turn = 'white'
        self.game_over = False
        self.promotion_menu_active = False
        self.promotion_square = None
        self.game_end_message = None
        self.king_positions = {'white': (7, 4), 'black': (0, 4)}
        self.castling_rights = {
            'white': {'kingside': True, 'queenside': True},
            'black': {'kingside': True, 'queenside': True}
        }
        self.last_move = None
        self.promotion_menu_pos = None
        
        self.quantum_mode = False
        self.quantum_states = []
        self.quantum_selection = []


    def create_board(self):
        board = [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        pieces_ = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        
        for col in range(BOARD_SIZE):
            board[1][col] = {'piece': 'pawn', 'color': 'black'}
            board[6][col] = {'piece': 'pawn', 'color': 'white'}
            board[0][col] = {'piece': pieces_[col], 'color': 'black'}
            board[7][col] = {'piece': pieces_[col], 'color': 'white'}
        
        return board


    def is_quantum_piece(self, row, col):
        for state in self.quantum_states:
            if (row, col) in state.positions:
                return True
        return False


    def get_quantum_state(self, row, col):
        for state in self.quantum_states:
            if (row, col) in state.positions:
                return state
        return None


    def calculate_moves(self, row, col, check_castling=True, check_check=False):
        piece = self.board[row][col]
        if not piece:
            return []
        
        moves = []
        color = piece['color']
        piece_type = piece['piece']

        # Pawn
        if piece_type == 'pawn':
            direction = 1 if color == 'black' else -1
            start_row = 1 if color == 'black' else 6

            # Forward moves
            if 0 <= row + direction < 8 and not self.board[row + direction][col]:
                moves.append((row + direction, col))
                if row == start_row and not self.board[row + 2 * direction][col]:
                    moves.append((row + 2 * direction, col))

            for col_offset in [-1, 1]:
                new_col = col + col_offset
                if 0 <= new_col < 8 and 0 <= row + direction < 8:
                    target = self.board[row + direction][new_col]
                    if target and target['color'] != color:
                        moves.append((row + direction, new_col))
                    elif (self.last_move and self.board[row][new_col] and 
                          self.board[row][new_col]['piece'] == 'pawn' and 
                          self.board[row][new_col]['color'] != color):
                        last_from_row, last_from_col, last_to_row, last_to_col = self.last_move
                        if (last_from_row == (1 if color == 'white' else 6) and
                            last_to_row == row and last_to_col == new_col and
                            abs(last_from_row - last_to_row) == 2):
                            moves.append((row + direction, new_col))

        # Knight
        elif piece_type == 'knight':
            offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                      (1, -2), (1, 2), (2, -1), (2, 1)]
            for dr, dc in offsets:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < 8 and 0 <= new_col < 8 and
                    (not self.board[new_row][new_col] or 
                     self.board[new_row][new_col]['color'] != color)):
                    moves.append((new_row, new_col))

        # Bishop/Queen/Rook
        if piece_type in ['bishop', 'queen', 'rook']:
            directions = []
            if piece_type in ['rook', 'queen']:
                directions.extend([(0, 1), (0, -1), (1, 0), (-1, 0)])
            if piece_type in ['bishop', 'queen']:
                directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])

            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                while 0 <= new_row < 8 and 0 <= new_col < 8:
                    target = self.board[new_row][new_col]
                    if not target:
                        moves.append((new_row, new_col))
                    else:
                        if target['color'] != color:
                            moves.append((new_row, new_col))
                        break
                    new_row += dr
                    new_col += dc

        # King
        elif piece_type == 'king':
            offsets = [(0, 1), (0, -1), (1, 0), (-1, 0),
                      (1, 1), (1, -1), (-1, 1), (-1, -1)]
            for dr, dc in offsets:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < 8 and 0 <= new_col < 8 and
                    (not self.board[new_row][new_col] or 
                     self.board[new_row][new_col]['color'] != color)):
                    moves.append((new_row, new_col))

            if check_castling and not check_check and not self.is_in_check(color):
                if self.castling_rights[color]['kingside']:
                    if (not self.board[row][5] and not self.board[row][6] and
                        not self.is_square_attacked(row, 5, color) and
                        not self.is_square_attacked(row, 6, color)):
                        moves.append((row, 6))
                
                if self.castling_rights[color]['queenside']:
                    if (not self.board[row][3] and not self.board[row][2] and
                        not self.board[row][1] and
                        not self.is_square_attacked(row, 3, color) and
                        not self.is_square_attacked(row, 2, color)):
                        moves.append((row, 2))

        if self.quantum_mode:
            moves = [(r, c) for r, c in moves if not self.board[r][c] and not self.get_quantum_state(r, c)]
            
            if piece_type == 'pawn':
                start_row = 6 if color == 'white' else 1
                if row != start_row:
                    moves = []

        if not check_check:
            legal_moves = []
            for move_row, move_col in moves:
                if not self.would_be_in_check(row, col, move_row, move_col):
                    legal_moves.append((move_row, move_col))
            return legal_moves

        return moves


    def is_square_attacked(self, row, col, defending_color):
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece and piece['color'] != defending_color:
                    if (row, col) in self.calculate_moves(r, c, check_castling=False, check_check=True):
                        return True
        return False


    def would_be_in_check(self, from_row, from_col, to_row, to_col):
        original_piece = self.board[to_row][to_col]
        moving_piece = self.board[from_row][from_col]
        self.board[to_row][to_col] = moving_piece
        self.board[from_row][from_col] = None

        original_king_pos = None
        if moving_piece['piece'] == 'king':
            original_king_pos = self.king_positions[moving_piece['color']]
            self.king_positions[moving_piece['color']] = (to_row, to_col)

        king_pos = self.king_positions[moving_piece['color']]
        is_check = self.is_square_attacked(*king_pos, moving_piece['color'])

        self.board[from_row][from_col] = moving_piece
        self.board[to_row][to_col] = original_piece
        if original_king_pos:
            self.king_positions[moving_piece['color']] = original_king_pos

        return is_check


    def is_in_check(self, color):
        return self.is_square_attacked(*self.king_positions[color], color)


    def handle_quantum_selection(self, row, col):
        if len(self.quantum_selection) == 0:
            if self.board[row][col] is not None:
                return  
            self.quantum_selection.append((row, col))
        elif len(self.quantum_selection) == 1:
            if self.board[row][col] is not None:
                return 
            if (row, col) != self.quantum_selection[0]:
                self.quantum_selection.append((row, col))
                piece = self.board[self.active_piece[0]][self.active_piece[1]]
                new_state = QuantumState(
                    piece['piece'],
                    piece['color'],
                    self.quantum_selection[0],
                    self.quantum_selection[1]
                )
                self.quantum_states.append(new_state)
                
                self.board[self.quantum_selection[0][0]][self.quantum_selection[0][1]] = piece.copy()
                self.board[self.quantum_selection[1][0]][self.quantum_selection[1][1]] = piece.copy()
                if (self.active_piece[0], self.active_piece[1]) not in self.quantum_selection:
                    self.board[self.active_piece[0]][self.active_piece[1]] = None
                
                self.quantum_selection = []
                self.active_piece = None
                self.valid_moves = []
                self.quantum_mode = False
                self.next_turn()


    def check_quantum_collapse(self, row, col):
        state = self.get_quantum_state(row, col)
        if not state:
            return False
        
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                piece = self.board[r][c]
                if piece and piece['color'] != state.color:
                    moves = self.calculate_moves(r, c)
                    for pos in state.positions:
                        if pos in moves:
                            final_pos = state.collapse(random.choice([0, 1]))
                            other_pos = state.positions[1] if final_pos == state.positions[0] else state.positions[0]
                            
                            if pos == final_pos:
                                self.board[final_pos[0]][final_pos[1]] = None
                                self.board[other_pos[0]][other_pos[1]] = {
                                    'piece': state.piece_type,
                                    'color': state.color
                                }
                            else:
                                self.board[final_pos[0]][final_pos[1]] = {
                                    'piece': state.piece_type,
                                    'color': state.color
                                }
                                self.board[other_pos[0]][other_pos[1]] = None
                                
                            self.quantum_states.remove(state)
                            return True
        return False


    def make_move(self, from_row, from_col, to_row, to_col):
        moving_piece = self.board[from_row][from_col]
        target_piece = self.board[to_row][to_col]
        
        quantum_state = self.get_quantum_state(from_row, from_col)
        if quantum_state:
            if target_piece is not None or self.get_quantum_state(to_row, to_col):
                final_pos = quantum_state.collapse(random.choice([0, 1]))
                other_pos = quantum_state.positions[1] if final_pos == quantum_state.positions[0] else quantum_state.positions[0]
                
                self.board[quantum_state.positions[0][0]][quantum_state.positions[0][1]] = None
                self.board[quantum_state.positions[1][0]][quantum_state.positions[1][1]] = None
                
                self.board[final_pos[0]][final_pos[1]] = {
                    'piece': quantum_state.piece_type,
                    'color': quantum_state.color
                }
                
                self.quantum_states.remove(quantum_state)
                
                if final_pos == (from_row, from_col):
                    self.board[to_row][to_col] = moving_piece
                    self.board[from_row][from_col] = None
            else:
                other_pos = [pos for pos in quantum_state.positions 
                            if pos != (from_row, from_col)][0]
                quantum_state.positions = [(to_row, to_col), other_pos]
                self.board[to_row][to_col] = moving_piece
                self.board[from_row][from_col] = None
            
            self.next_turn()
            return

        target_quantum_state = self.get_quantum_state(to_row, to_col)
        if target_quantum_state:
            final_pos = target_quantum_state.collapse(random.choice([0, 1]))
            other_pos = target_quantum_state.positions[1] if final_pos == target_quantum_state.positions[0] else target_quantum_state.positions[0]
            
            self.board[target_quantum_state.positions[0][0]][target_quantum_state.positions[0][1]] = None
            self.board[target_quantum_state.positions[1][0]][target_quantum_state.positions[1][1]] = None
            
            self.board[final_pos[0]][final_pos[1]] = {
                'piece': target_quantum_state.piece_type,
                'color': target_quantum_state.color
            }
            
            self.quantum_states.remove(target_quantum_state)
            
            if final_pos == (to_row, to_col):
                self.board[to_row][to_col] = moving_piece
                self.board[from_row][from_col] = None

            self.next_turn()
            return

        if moving_piece['piece'] == 'pawn' and abs(to_col - from_col) == 1 and not self.board[to_row][to_col]:
            self.board[from_row][to_col] = None

        if moving_piece['piece'] == 'king' and abs(to_col - from_col) == 2:
            rook_row = to_row
            old_rook_col = 7 if to_col > from_col else 0
            new_rook_col = 5 if to_col > from_col else 3
            self.board[rook_row][new_rook_col] = self.board[rook_row][old_rook_col]
            self.board[rook_row][old_rook_col] = None

        if moving_piece['piece'] == 'king':
            self.king_positions[moving_piece['color']] = (to_row, to_col)
            self.castling_rights[moving_piece['color']] = {'kingside': False, 'queenside': False}
        elif moving_piece['piece'] == 'rook':
            if from_col == 0:
                self.castling_rights[moving_piece['color']]['queenside'] = False
            elif from_col == 7:
                self.castling_rights[moving_piece['color']]['kingside'] = False

        self.board[to_row][to_col] = moving_piece
        self.board[from_row][from_col] = None
        self.last_move = (from_row, from_col, to_row, to_col)

        if moving_piece['piece'] == 'pawn' and (to_row == 0 or to_row == 7):
            self.promotion_menu_active = True
            self.promotion_square = (to_row, to_col)
            return

        self.next_turn()


    def handle_promotion(self, choice):
        if self.promotion_square:
            row, col = self.promotion_square
            self.board[row][col]['piece'] = choice
            self.promotion_menu_active = False
            self.promotion_square = None
            self.next_turn()


    def handle_promotion_click(self, x, y):
        menu_x, menu_y = self.promotion_menu_pos
        if menu_x <= x <= menu_x + SQUARE_SIZE:
            choice_index = (y - menu_y) // SQUARE_SIZE
            choices = ['queen', 'rook', 'bishop', 'knight']
            if 0 <= choice_index < len(choices):
                self.handle_promotion(choices[choice_index])


    def next_turn(self):
        self.turn = 'black' if self.turn == 'white' else 'white'
        
        if not any(self.calculate_moves(r, c) for r in range(8) for c in range(8)
                  if self.board[r][c] and self.board[r][c]['color'] == self.turn):
            if self.is_in_check(self.turn):
                winner = 'black' if self.turn == 'white' else 'white'
                self.game_end_message = f"{winner.capitalize()} wins by checkmate!"
            else:
                self.game_end_message = "Game drawn by stalemate!"
            self.game_over = True


    def update_quantum_timers(self):
        for state in self.quantum_states[:]:
            if state.update_timer():
                final_pos = state.collapse(random.choice([0, 1]))
                other_pos = state.positions[1] if final_pos == state.positions[0] else state.positions[0]
                self.board[other_pos[0]][other_pos[1]] = None
                self.board[final_pos[0]][final_pos[1]] = {
                    'piece': state.piece_type,
                    'color': state.color
                }
                self.quantum_states.remove(state)



    def draw_board(self):
        self.screen.fill(WHITE)
        self.update_quantum_timers()
        
        
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                color = WHITE if (row + col) % 2 == 0 else GRAY
                pygame.draw.rect(self.screen, color,
                               (col * SQUARE_SIZE, row * SQUARE_SIZE, 
                                SQUARE_SIZE, SQUARE_SIZE))
                
                quantum_state = self.get_quantum_state(row, col)
                if quantum_state:
                    s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    pygame.draw.rect(s, QUANTUM_SQUARE, s.get_rect())
                    self.screen.blit(s, (col * SQUARE_SIZE, row * SQUARE_SIZE))

                    timer_width = (quantum_state.timer / 90) * SQUARE_SIZE
                    pygame.draw.rect(self.screen, TIMER_COLOR,
                                   (col * SQUARE_SIZE, 
                                    (row + 1) * SQUARE_SIZE - 5,
                                    timer_width, 5))
                
                piece = self.board[row][col]
                if piece:
                    text = self.font.render(PIECES[piece['color']][piece['piece']], True, BLACK)
                    text_rect = text.get_rect(center=(col * SQUARE_SIZE + SQUARE_SIZE // 2,
                                                    row * SQUARE_SIZE + SQUARE_SIZE // 2))
                    self.screen.blit(text, text_rect)

        if self.active_piece:
            row, col = self.active_piece
            s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
            pygame.draw.rect(s, HIGHLIGHT, s.get_rect())
            self.screen.blit(s, (col * SQUARE_SIZE, row * SQUARE_SIZE))
            
            highlight_color = QUANTUM_HIGHLIGHT if self.quantum_mode else MOVE_HIGHLIGHT
            for move_row, move_col in self.valid_moves:
                s = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(s, highlight_color, s.get_rect())
                self.screen.blit(s, (move_col * SQUARE_SIZE, move_row * SQUARE_SIZE))

        for row, col in self.quantum_selection:
            pygame.draw.circle(self.screen, QUANTUM_DOT,
                             (col * SQUARE_SIZE + SQUARE_SIZE // 2,
                              row * SQUARE_SIZE + SQUARE_SIZE // 2),
                             10)

        if self.promotion_menu_active:
            self.draw_promotion_menu()
        
        if self.game_end_message:
            self.draw_game_end_message()
            
        if self.show_instructions:
            self.draw_instructions()

        pygame.display.flip()


    def draw_promotion_menu(self):
        if not self.promotion_square:
            return
            
        row, col = self.promotion_square
        pieces = ['queen', 'rook', 'bishop', 'knight']
        menu_height = SQUARE_SIZE * len(pieces)
        
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        menu_x = min(col * SQUARE_SIZE, WINDOW_SIZE - SQUARE_SIZE)
        menu_y = SQUARE_SIZE if row == 0 else max(0, WINDOW_SIZE - menu_height - SQUARE_SIZE)
        self.promotion_menu_pos = (menu_x, menu_y)
        
        pygame.draw.rect(self.screen, MENU_BG,
                        (menu_x, menu_y, SQUARE_SIZE, menu_height))
        pygame.draw.rect(self.screen, BLACK,
                        (menu_x, menu_y, SQUARE_SIZE, menu_height), 2)
        
        for i, piece in enumerate(pieces):
            text = self.font.render(PIECES[self.turn][piece], True, BLACK)
            text_rect = text.get_rect(center=(menu_x + SQUARE_SIZE // 2,
                                            menu_y + SQUARE_SIZE // 2 + i * SQUARE_SIZE))
            self.screen.blit(text, text_rect)
            
            pygame.draw.rect(self.screen, BLACK,
                           (menu_x, menu_y + i * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 1)


    def draw_game_end_message(self):
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        message_surf = pygame.Surface((400, 100), pygame.SRCALPHA)
        message_surf.fill(MESSAGE_BG)
        text = self.message_font.render(self.game_end_message, True, WHITE)
        text_rect = text.get_rect(center=(200, 50))
        message_surf.blit(text, text_rect)
        message_rect = message_surf.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2))
        self.screen.blit(message_surf, message_rect)


    def draw_instructions(self):
        overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
        overlay.fill(INSTRUCTION_BG)
        self.screen.blit(overlay, (0, 0))
        
        instructions = [
            "Quantum Chess Instructions:",
            "",
            "",
            "1. Basic Rules:",
            "   - All standard chess rules apply",
            "   - Press 'Q' when a piece is selected to enter quantum mode",
            "   - Only classical moves are allowed when king is in check",
            "",
            "2. Quantum Mode:",
            "   - Pieces can superimpose in two positions simultaneously",
            "   - Cannot capture pieces to initiate quantum mode",
            "   - Pawns can only enter quantum state on their first move",
            "   - Quantum states collapse after 90 seconds or when observed",
            "   - Quantum pieces are observed when they attack or are attacked",  
            "",
            "3. Controls:",
            "   - Click to select and move pieces",
            "   - Press 'Q' for quantum moves",
            "   - Press 'I' to toggle instructions",
            "",
            "",
            "Press 'I' to close instructions"
        ]
        
        y_offset = 50
        for line in instructions:
            text = self.instruction_font.render(line, True, WHITE)
            text_rect = text.get_rect(x=50, y=y_offset)
            self.screen.blit(text, text_rect)
            y_offset += 30



    def run(self):
        running = True
        game_over_timestamp = None
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                
                if not self.game_over:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_q:
                            if self.active_piece:
                                row, col = self.active_piece
                                piece = self.board[row][col]
                                if piece and piece['piece'] != 'king':
                                    self.quantum_mode = not self.quantum_mode
                                    self.quantum_selection = []
                                    self.valid_moves = self.calculate_moves(row, col)
                        
                        elif event.key == pygame.K_i:
                            self.show_instructions = not self.show_instructions
                    
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        x, y = event.pos
                        col = x // SQUARE_SIZE
                        row = y // SQUARE_SIZE
                        
                        if self.promotion_menu_active:
                            self.handle_promotion_click(x, y)
                            continue

                        if self.quantum_mode and self.active_piece:
                            if (row, col) in self.valid_moves:
                                self.handle_quantum_selection(row, col)
                            continue

                        if self.active_piece:
                            if (row, col) in self.valid_moves:
                                self.make_move(self.active_piece[0], 
                                            self.active_piece[1], row, col)
                                self.active_piece = None
                                self.valid_moves = []
                                self.quantum_mode = False
                            else:
                                piece = self.board[row][col]
                                if piece and piece['color'] == self.turn:
                                    self.active_piece = (row, col)
                                    self.valid_moves = self.calculate_moves(row, col)
                                    self.quantum_mode = False
                                else:
                                    self.active_piece = None
                                    self.valid_moves = []
                                    self.quantum_mode = False
                        else:
                            piece = self.board[row][col]
                            if piece and piece['color'] == self.turn:
                                self.active_piece = (row, col)
                                self.valid_moves = self.calculate_moves(row, col)

            if self.game_over:
                if game_over_timestamp is None:
                    game_over_timestamp = time.time()
                elif time.time() - game_over_timestamp >= 5:
                    self.reset()
                    game_over_timestamp = None
            
            self.draw_board()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = ChessGame()
    game.run()