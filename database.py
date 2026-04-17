import sqlite3
import random
import string
from datetime import datetime

DB_PATH = "tictactoe.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        display_name TEXT,
        game_id TEXT UNIQUE,
        elo INTEGER DEFAULT 1000,
        coins INTEGER DEFAULT 500,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        active_skin_x TEXT DEFAULT NULL,
        active_skin_o TEXT DEFAULT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS friends (
        user_id INTEGER,
        friend_id INTEGER,
        PRIMARY KEY (user_id, friend_id)
    );

    CREATE TABLE IF NOT EXISTS skins (
        skin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        symbol_x TEXT NOT NULL,
        symbol_o TEXT NOT NULL,
        rarity TEXT DEFAULT 'Кастомный',
        creator_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS user_skins (
        user_id INTEGER,
        skin_id INTEGER,
        acquired_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, skin_id)
    );
    
    CREATE TABLE IF NOT EXISTS market (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        skin_id INTEGER,
        seller_id INTEGER,
        price INTEGER,
        listed_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS cases (
        case_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cost INTEGER NOT NULL,
        skin_ids TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER,
        player2_id INTEGER,
        status TEXT DEFAULT 'waiting',
        board TEXT DEFAULT '---------',
        current_turn INTEGER,
        winner_id INTEGER DEFAULT NULL,
        skin_x TEXT DEFAULT 'X',
        skin_o TEXT DEFAULT 'O',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        admin_cancelled INTEGER DEFAULT 0
    );
    
    CREATE TABLE IF NOT EXISTS matchmaking (
        user_id INTEGER PRIMARY KEY,
        elo INTEGER,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        reason TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    conn.commit()
    conn.close()

def generate_game_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_game_id(game_id: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE game_id = ?", (game_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_username(username: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username.lstrip('@'),))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(user_id: int, username: str, display_name: str):
    conn = get_conn()
    c = conn.cursor()
    game_id = generate_game_id()
    while True:
        c.execute("SELECT 1 FROM users WHERE game_id = ?", (game_id,))
        if not c.fetchone():
            break
        game_id = generate_game_id()
    c.execute("""
        INSERT OR IGNORE INTO users (user_id, username, display_name, game_id)
        VALUES (?, ?, ?, ?)
    """, (user_id, username, display_name, game_id))
    conn.commit()
    conn.close()

def update_username(user_id: int, username: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    conn.close()

def update_display_name(user_id: int, name: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET display_name = ? WHERE user_id = ?", (name, user_id))
    conn.commit()
    conn.close()

def add_coins(user_id: int, amount: int, reason: str = ""):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (amount, user_id))
    c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
              (user_id, amount, reason))
    conn.commit()
    conn.close()

def get_rank(elo: int) -> tuple:
    from config import RANKS
    for rank_name, data in RANKS.items():
        if data["min"] <= elo <= data["max"]:
            return rank_name, data["emoji"]
    return "Легенда", "🌟"

def update_elo(user_id: int, delta: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET elo = MAX(0, elo + ?) WHERE user_id = ?", (delta, user_id))
    conn.commit()
    conn.close()

def record_win(user_id: int):
    from config import ELO_WIN
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET wins = wins + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    update_elo(user_id, ELO_WIN)
    add_coins(user_id, 50, "Победа в игре")

def record_loss(user_id: int):
    from config import ELO_LOSS
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET losses = losses + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    update_elo(user_id, -ELO_LOSS)

def record_draw(user_id: int):
    from config import ELO_DRAW
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET draws = draws + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    update_elo(user_id, ELO_DRAW)
    add_coins(user_id, 10, "Ничья в игре")

def get_all_skins(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.username as creator_username
        FROM skins s
        LEFT JOIN users u ON s.creator_id = u.user_id
        WHERE s.skin_id IN (SELECT skin_id FROM user_skins WHERE user_id = ?)
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_skin(skin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.username as creator_username
        FROM skins s
        LEFT JOIN users u ON s.creator_id = u.user_id
        WHERE s.skin_id = ?
    """, (skin_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def create_skin(name: str, symbol_x: str, symbol_o: str, creator_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO skins (name, symbol_x, symbol_o, creator_id)
        VALUES (?, ?, ?, ?)
    """, (name, symbol_x, symbol_o, creator_id))
    skin_id = c.lastrowid
    conn.commit()
    conn.close()
    return skin_id

def give_skin(user_id: int, skin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)
    """, (user_id, skin_id))
    conn.commit()
    conn.close()

def has_skin(user_id: int, skin_id: int) -> bool:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM user_skins WHERE user_id = ? AND skin_id = ?", (user_id, skin_id))
    result = c.fetchone() is not None
    conn.close()
    return result

def set_active_skin(user_id: int, skin_id: int, slot: str):
    conn = get_conn()
    c = conn.cursor()
    if slot == 'x':
        c.execute("UPDATE users SET active_skin_x = ? WHERE user_id = ?", (skin_id, user_id))
    else:
        c.execute("UPDATE users SET active_skin_o = ? WHERE user_id = ?", (skin_id, user_id))
    conn.commit()
    conn.close()

def get_market_listings(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, s.name, s.symbol_x, s.symbol_o, u.username as seller_name,
               cr.username as creator_username, s.creator_id
        FROM market m
        JOIN skins s ON m.skin_id = s.skin_id
        JOIN users u ON m.seller_id = u.user_id
        LEFT JOIN users cr ON s.creator_id = cr.user_id
        ORDER BY m.listed_at DESC
        LIMIT ? OFFSET ?
    """, (per_page, page * per_page))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def count_market_listings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM market")
    result = c.fetchone()[0]
    conn.close()
    return result

def list_skin_on_market(seller_id: int, skin_id: int, price: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO market (skin_id, seller_id, price) VALUES (?, ?, ?)
    """, (skin_id, seller_id, price))
    listing_id = c.lastrowid
    c.execute("DELETE FROM user_skins WHERE user_id = ? AND skin_id = ?", (seller_id, skin_id))
    conn.commit()
    conn.close()
    return listing_id

def buy_from_market(buyer_id: int, listing_id: int):
    from config import MARKET_CREATOR_PERCENT
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM market WHERE listing_id = ?", (listing_id,))
    listing = c.fetchone()
    if not listing:
        conn.close()
        return False, "Лот не найден"
    listing = dict(listing)
    
    c.execute("SELECT * FROM users WHERE user_id = ?", (buyer_id,))
    buyer = dict(c.fetchone())
    if buyer['coins'] < listing['price']:
        conn.close()
        return False, "Недостаточно монет"
    
    if listing['seller_id'] == buyer_id:
        conn.close()
        return False, "Нельзя купить свой товар"
    
    c.execute("SELECT creator_id FROM skins WHERE skin_id = ?", (listing['skin_id'],))
    skin_row = c.fetchone()
    creator_id = skin_row['creator_id'] if skin_row else None
    
    creator_cut = int(listing['price'] * MARKET_CREATOR_PERCENT) if creator_id else 0
    seller_gets = listing['price'] - creator_cut
    
    c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (listing['price'], buyer_id))
    c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (seller_gets, listing['seller_id']))
    if creator_id and creator_id != listing['seller_id']:
        c.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (creator_cut, creator_id))
    
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)",
              (buyer_id, listing['skin_id']))
    c.execute("DELETE FROM market WHERE listing_id = ?", (listing_id,))
    c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
              (buyer_id, -listing['price'], f"Покупка скина #{listing['skin_id']}"))
    c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
              (listing['seller_id'], seller_gets, f"Продажа скина #{listing['skin_id']}"))
    if creator_id and creator_id != listing['seller_id']:
        c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
                  (creator_id, creator_cut, f"Роялти за скин #{listing['skin_id']}"))
    conn.commit()
    conn.close()
    return True, {"seller_gets": seller_gets, "creator_cut": creator_cut, "creator_id": creator_id}

def remove_my_listing(seller_id: int, listing_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM market WHERE listing_id = ? AND seller_id = ?", (listing_id, seller_id))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    row = dict(row)
    c.execute("DELETE FROM market WHERE listing_id = ?", (listing_id,))
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)",
              (seller_id, row['skin_id']))
    conn.commit()
    conn.close()
    return True

def get_cases():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cases")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_case(case_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def open_case(user_id: int, case_id: int):
    conn = get_conn()
    c = conn.cursor()
    case = get_case(case_id)
    if not case:
        conn.close()
        return False, "Кейс не найден"
    
    c.execute("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row or row['coins'] < case['cost']:
        conn.close()
        return False, "Недостаточно монет"
    
    skin_ids = [int(x) for x in case['skin_ids'].split(',') if x.strip()]
    if not skin_ids:
        conn.close()
        return False, "Кейс пуст"
    
    won_skin_id = random.choice(skin_ids)
    c.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (case['cost'], user_id))
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)",
              (user_id, won_skin_id))
    c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
              (user_id, -case['cost'], f"Открытие кейса #{case_id}"))
    conn.commit()
    conn.close()
    return True, won_skin_id

def create_game(player1_id: int, player2_id: int, skin_x: str = 'X', skin_o: str = 'O'):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO games (player1_id, player2_id, current_turn, skin_x, skin_o, status)
        VALUES (?, ?, ?, ?, ?, 'active')
    """, (player1_id, player2_id, player1_id, skin_x, skin_o))
    game_id = c.lastrowid
    conn.commit()
    conn.close()
    return game_id

def get_game(game_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_game(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM games 
        WHERE (player1_id = ? OR player2_id = ?) AND status = 'active'
        ORDER BY game_id DESC LIMIT 1
    """, (user_id, user_id))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def make_move(game_id: int, user_id: int, position: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
    game = dict(c.fetchone())
    
    if game['current_turn'] != user_id:
        conn.close()
        return False, "Не ваш ход"
    
    board = list(game['board'])
    if board[position] != '-':
        conn.close()
        return False, "Клетка занята"
    
    symbol = 'X' if user_id == game['player1_id'] else 'O'
    board[position] = symbol
    board_str = ''.join(board)
    
    winner = check_winner(board_str)
    next_turn = game['player2_id'] if user_id == game['player1_id'] else game['player1_id']
    
    if winner == 'X':
        winner_id = game['player1_id']
        c.execute("UPDATE games SET board=?, status='finished', winner_id=? WHERE game_id=?",
                  (board_str, winner_id, game_id))
    elif winner == 'O':
        winner_id = game['player2_id']
        c.execute("UPDATE games SET board=?, status='finished', winner_id=? WHERE game_id=?",
                  (board_str, winner_id, game_id))
    elif '-' not in board_str:
        c.execute("UPDATE games SET board=?, status='finished', winner_id=NULL WHERE game_id=?",
                  (board_str, game_id))
        winner = 'draw'
    else:
        c.execute("UPDATE games SET board=?, current_turn=? WHERE game_id=?",
                  (board_str, next_turn, game_id))
    
    conn.commit()
    conn.close()
    return True, winner

def check_winner(board: str):
    lines = [
        (0,1,2),(3,4,5),(6,7,8),
        (0,3,6),(1,4,7),(2,5,8),
        (0,4,8),(2,4,6)
    ]
    b = list(board)
    for a,bb,cc in lines:
        if b[a] != '-' and b[a] == b[bb] == b[cc]:
            return b[a]
    return None

def add_to_matchmaking(user_id: int, elo: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO matchmaking (user_id, elo, joined_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
              (user_id, elo))
    conn.commit()
    conn.close()

def remove_from_matchmaking(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM matchmaking WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def find_match(user_id: int, elo: int, range_delta: int = 300):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM matchmaking 
        WHERE user_id != ? AND ABS(elo - ?) <= ?
        ORDER BY ABS(elo - ?) ASC, joined_at ASC
        LIMIT 1
    """, (user_id, elo, range_delta, elo))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_friend(user_id: int, friend_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO friends (user_id, friend_id) VALUES (?, ?)", (user_id, friend_id))
    conn.commit()
    conn.close()

def get_friends(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT u.* FROM users u
        JOIN friends f ON f.friend_id = u.user_id
        WHERE f.user_id = ?
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_users(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY elo DESC LIMIT ? OFFSET ?",
              (per_page, page * per_page))
    rows = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total

def admin_set_coins(user_id: int, amount: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET coins = ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def admin_set_elo(user_id: int, elo: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET elo = ? WHERE user_id = ?", (elo, user_id))
    conn.commit()
    conn.close()

def admin_cancel_game(game_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE games SET status='cancelled', admin_cancelled=1 WHERE game_id=?", (game_id,))
    conn.commit()
    conn.close()

def get_all_skins_admin(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT s.*, u.username as creator_username
        FROM skins s
        LEFT JOIN users u ON s.creator_id = u.user_id
        ORDER BY s.skin_id DESC
        LIMIT ? OFFSET ?
    """, (per_page, page * per_page))
    rows = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM skins").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total

def get_all_games_admin(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT g.*, 
               u1.username as p1_username,
               u2.username as p2_username
        FROM games g
        LEFT JOIN users u1 ON g.player1_id = u1.user_id
        LEFT JOIN users u2 ON g.player2_id = u2.user_id
        ORDER BY g.game_id DESC
        LIMIT ? OFFSET ?
    """, (per_page, page * per_page))
    rows = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total

def create_case_db(name: str, cost: int, skin_ids: list):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO cases (name, cost, skin_ids) VALUES (?, ?, ?)",
              (name, cost, ','.join(map(str, skin_ids))))
    case_id = c.lastrowid
    conn.commit()
    conn.close()
    return case_id

def delete_skin_admin(skin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM skins WHERE skin_id = ?", (skin_id,))
    c.execute("DELETE FROM user_skins WHERE skin_id = ?", (skin_id,))
    c.execute("DELETE FROM market WHERE skin_id = ?", (skin_id,))
    conn.commit()
    conn.close()

def ban_user(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET elo = -1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()