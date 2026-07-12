def create_board():
    """Создает начальную доску 8х8, соответствующую формату фронтенда"""
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
    """Проверяет, может ли конкретная шашка или дамка совершить взятие"""
    piece = board[r][c]
    if not piece['type']:
        return False
        
    enemy_type = 'B' if piece['type'] == 'W' else 'W'
    dirs = [[-1, -1], [-1, 1], [1, -1], [1, 1]]

    if piece['isKing']:
        # Логика взятия для Дамки (короля)
        for d in dirs:
            step = 1
            found_enemy = None
            while True:
                nr, nc = r + d[0] * step, c + d[1] * step
                if not (0 <= nr < 8 and 0 <= nc < 8):
                    break
                target = board[nr][nc]
                if target['type'] == piece['type']:
                    break
                if target['type'] == enemy_type:
                    if found_enemy:
                        break  # Два врага подряд бить нельзя
                    found_enemy = {'r': nr, 'c': nc}
                elif target['type'] == '':
                    if found_enemy:
                        return True  # Есть свободное поле за врагом
                step += 1
    else:
        # Логика взятия для простой шашки
        for d in dirs:
            mid_r, mid_c = r + d[0], c + d[1]
            end_r, end_c = r + d[0] * 2, c + d[1] * 2
            if 0 <= end_r < 8 and 0 <= end_c < 8:
                if board[mid_r][mid_c]['type'] == enemy_type and board[end_r][end_c]['type'] == '':
                    return True
    return False

def check_move_validity(board, turn, from_r, from_c, to_r, to_c):
    """
    Полная серверная проверка корректности хода.
    Возвращает (is_valid, is_hit, enemy_r, enemy_c)
    """
    if not (0 <= from_r < 8 and 0 <= from_c < 8 and 0 <= to_r < 8 and 0 <= to_c < 8):
        return False, False, None, None
        
    piece = board[from_r][from_c]
    target = board[to_r][to_c]
    current_type = 'W' if turn == 'white' else 'B'
    
    # Базовые проверки
    if piece['type'] != current_type or target['type'] != '':
        return False, False, None, None
        
    row_diff = to_r - from_r
    col_diff = abs(to_c - from_c)
    
    # Проверяем, есть ли обязательные взятия на доске
    must_hit = get_must_hit_pieces(board, turn)
    if must_hit:
        # Если бить обязательно, но этот ход совершается не той шашкой или не является прыжком
        is_obligated = any(p['r'] == from_r and p['c'] == from_c for p in must_hit)
        if not is_obligated:
            return False, False, None, None

    # --- ЛОГИКА ДАМКИ ---
    if piece['isKing']:
        if abs(row_diff) == col_diff:
            dir_r = 1 if row_diff > 0 else -1
            dir_c = 1 if (to_c - from_c) > 0 else -1
            step = 1
            enemies = []
            
            while step < col_diff:
                check_r = from_r + dir_r * step
                check_c = from_c + dir_c * step
                if board[check_r][check_c]['type'] != '':
                    enemies.append({'r': check_r, 'c': check_c, 'type': board[check_r][check_c]['type']})
                step += 1
                
            # Тихий ход дамки
            if not enemies and not must_hit:
                return True, False, None, None
            # Взятие дамкой
            elif len(enemies) == 1 and enemies[0]['type'] != current_type:
                return True, True, enemies[0]['r'], enemies[0]['c']
        return False, False, None, None

    # --- ЛОГИКА ПРОСТОЙ ШАШКИ ---
    if must_hit and col_diff != 2:
        return False, False, None, None

    # Обычный ход (только вперед)
    if col_diff == 1 and not must_hit:
        if turn == 'white' and row_diff == -1:
            return True, False, None, None
        if turn == 'black' and row_diff == 1:
            return True, False, None, None

    # Обычное взятие
    if col_diff == 2 and abs(row_diff) == 2:
        mid_r = (from_r + to_r) // 2
        mid_c = (from_c + to_c) // 2
        enemy_type = 'B' if turn == 'white' else 'W'
        if board[mid_r][mid_c]['type'] == enemy_type:
            return True, True, mid_r, mid_c

    return False, False, None, None
