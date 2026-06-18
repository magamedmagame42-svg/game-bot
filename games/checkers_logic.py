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
    """
    Проверяет ход. 
    Возвращает (True, True), если это прыжок со взятием фигуры.
    Возвращает (True, False), если это обычный тихий ход.
    Возвращает (False, False), если ход невозможен.
    """
    piece = board[from_row][from_col]
    target = board[to_row][to_col]
    
    # Проверка цвета
    if turn == 'white' and piece != WHITE_PIECE: return False, False
    if turn == 'black' and piece != BLACK_PIECE: return False, False
    if target != EMPTY_BLACK: return False, False
    
    row_diff = to_row - from_row
    col_diff = abs(to_col - from_col)
    
    # 1. Проверка на обычный ход (на 1 клетку по диагонали вперед)
    if col_diff == 1:
        if turn == 'white' and row_diff == -1: return True, False
        if turn == 'black' and row_diff == 1: return True, False
        
    # 2. Проверка на взятие (прыжок на 2 клетки через фигуру соперника)
    if col_diff == 2 and abs(row_diff) == 2:
        mid_row = (from_row + to_row) // 2
        mid_col = (from_col + to_col) // 2
        mid_piece = board[mid_row][mid_col]
        
        # Белые бьют красных, красные бьют белых (в любую сторону)
        if turn == 'white' and mid_piece == BLACK_PIECE:
            return True, True
        if turn == 'black' and mid_piece == WHITE_PIECE:
            return True, True
            
    return False, False

def check_win(board):
    """Проверяет, остались ли фигуры"""
    white_count = sum(row.count(WHITE_PIECE) for row in board)
    black_count = sum(row.count(BLACK_PIECE) for row in board)
    
    if white_count == 0: return 'black'
    if black_count == 0: return 'white'
    return None
