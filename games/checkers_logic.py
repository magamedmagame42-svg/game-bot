EMPTY_BLACK = "⬛"
EMPTY_WHITE = "⬜"
WHITE_PIECE = "⚪"
BLACK_PIECE = "🔴"

def create_board():
    """Создает начальную доску 8х8"""
    board = []
    for row in range(8):
        board_row = []
        for col in range(8):
            if (row + col) % 2 == 1:
                if row < 3:
                    board_row.append(BLACK_PIECE)
                elif row > 4:
                    board_row.append(WHITE_PIECE)
                else:
                    board_row.append(EMPTY_BLACK)
            else:
                board_row.append(EMPTY_WHITE)
        board.append(board_row)
    return board

def is_valid_move(board, from_row, from_col, to_row, to_col, turn):
    """Простая проверка: ходим ли мы по диагонали на пустую черную клетку"""
    piece = board[from_row][from_col]
    target = board[to_row][to_col]
    
    # Проверяем, своей ли фигурой ходит игрок
    if turn == 'white' and piece != WHITE_PIECE: return False
    if turn == 'black' and piece != BLACK_PIECE: return False
    
    # Клетка назначения должна быть пустой и черной
    if target != EMPTY_BLACK: return False
    
    # Проверяем ход на 1 клетку по диагонали
    row_diff = to_row - from_row
    col_diff = abs(to_col - from_col)
    
    if col_diff == 1:
        if turn == 'white' and row_diff == -1: return True  # Белые ходят вверх
        if turn == 'black' and row_diff == 1: return True   # Черные ходят вниз
        
    return False

def check_win(board):
    """Проверяет, остались ли на доске фигуры соперника"""
    white_count = sum(row.count(WHITE_PIECE) for row in board)
    black_count = sum(row.count(BLACK_PIECE) for row in board)
    
    if white_count == 0: return 'black'
    if black_count == 0: return 'white'
    return None
