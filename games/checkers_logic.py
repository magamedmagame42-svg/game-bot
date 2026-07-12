def create_board():
    """Создает начальную доску 8х8 (как на фронтенде)"""
    board = []
    for r in range(8):
        board_row = []
        for c in range(8):
            if (r + c) % 2 == 1:
                if r < 3:
                    board_row.append({'type': 'B', 'isKing': False})
                elif r > 4:
                    board_row.append({'type': 'W', 'isKing': False})
                else:
                    board_row.append({'type': '', 'isKing': False})
            else:
                board_row.append({'type': '', 'isKing': False})
        board.append(board_row)
    return board

def get_must_hit_pieces(board, turn):
    """Находит все шашки текущего игрока, которые ОБЯЗАНЫ бить"""
    must_hit = []
    current_type = 'W' if turn == 'white' else 'B'
    for r in range(8):
        for c in range(8):
            if board[r][c]['type'] == current_type:
                if can_capture(board, r, c):
                    must_hit.append({'r': r, 'c': c})
    return must_hit

def can_capture(board, r, c):
    """Проверяет, может ли конкретная шашка совершить взятие"""
    piece = board[r][c]
    enemy_type = 'B' if piece['type'] == 'W' else 'W'
    dirs = [[-1, -1], [-1, 1], [1, -1], [1, 1]]

    # Логика для простой шашки (дамки проверяются иначе, это базовый вариант)
    for d in dirs:
        mid_r, mid_c = r + d[0], c + d[1]
        end_r, end_c = r + d[0] * 2, c + d[1] * 2
        if 0 <= end_r < 8 and 0 <= end_c < 8:
            if board[mid_r][mid_c]['type'] == enemy_type and board[end_r][end_c]['type'] == '':
                return True
    return False

def check_move_validity(board, turn, from_r, from_c, to_r, to_c):
    """
    Серверная валидация хода.
    Возвращает (is_valid, is_hit, enemy_r, enemy_c)
    """
    if from_r < 0 or from_r >= 8 or from_c < 0 or from_c >= 8: return False, False, None, None
    if to_r < 0 or to_r >= 8 or to_c < 0 or to_c >= 8: return False, False, None, None
    
    piece = board[from_r][from_col := from_c]
    target = board[to_r][to_c]
    
    current_type = 'W' if turn == 'white' else 'B'
    if piece['type'] != current_type or target['type'] != '': return False, False, None, None

    row_diff = to_r - from_r
    col_diff = abs(to_c - from_c)
    
    must_hit = get_must_hit_pieces(board, turn)
    
    # Если есть шашки, обязанные бить, а текущий ход — не прыжок
    if must_hit and col_diff != 2:
        return False, False, None, None
    if must_hit and not any(p['r'] == from_r and p['c'] == from_c for p in must_hit):
        return False, False, None, None

    # Обычный ход
    if col_diff == 1 and not must_hit:
        if turn == 'white' and row_diff == -1: return True, False, None, None
        if turn == 'black' and row_diff == 1: return True, False, None, None

    # Ход со взятием
    if col_diff == 2 and abs(row_diff) == 2:
        mid_r = (from_r + to_r) // 2
        mid_c = (from_c + to_c) // 2
        enemy_type = 'B' if turn == 'white' else 'W'
        if board[mid_r][mid_c]['type'] == enemy_type:
            return True, True, mid_r, mid_c

    return False, False, None, None
