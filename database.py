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
        creator_id INTEGER DEFAULT NULL,
        added_by_admin INTEGER DEFAULT NULL,
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
        skin_ids TEXT NOT NULL,
        added_by_admin INTEGER DEFAULT NULL
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

    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS chat_members (
        chat_id INTEGER,
        user_id INTEGER,
        joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS chat_messages (
        msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        user_id INTEGER,
        text TEXT,
        file_id TEXT DEFAULT NULL,
        file_type TEXT DEFAULT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS group_chats (
        tg_chat_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT DEFAULT 'group',
        added_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS group_duels (
        duel_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_chat_id INTEGER,
        challenger_id INTEGER,
        opponent_id INTEGER DEFAULT NULL,
        status TEXT DEFAULT 'waiting',
        board TEXT DEFAULT '---------',
        current_turn INTEGER,
        winner_id INTEGER DEFAULT NULL,
        elo_bet INTEGER DEFAULT 0,
        coin_bet INTEGER DEFAULT 0,
        message_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS duel_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_chat_id INTEGER,
        challenger_id INTEGER,
        opponent_id INTEGER,
        status TEXT DEFAULT 'pending',
        message_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    conn.close()

def migrate_db():
    conn = get_conn()
    c = conn.cursor()
    migrations = [
        "ALTER TABLE skins ADD COLUMN added_by_admin INTEGER DEFAULT NULL",
        "ALTER TABLE cases ADD COLUMN added_by_admin INTEGER DEFAULT NULL",
    ]
    for sql in migrations:
        try:
            c.execute(sql)
        except Exception:
            pass
    conn.commit()
    conn.close()

def generate_game_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ==================== Users ====================

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

# ==================== Skins ====================

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

def create_skin_by_admin(name: str, symbol_x: str, symbol_o: str, admin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO skins (name, symbol_x, symbol_o, creator_id, added_by_admin)
        VALUES (?, ?, ?, NULL, ?)
    """, (name, symbol_x, symbol_o, admin_id))
    skin_id = c.lastrowid
    conn.commit()
    conn.close()
    return skin_id

def edit_skin(skin_id: int, name: str, symbol_x: str, symbol_o: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE skins SET name = ?, symbol_x = ?, symbol_o = ? WHERE skin_id = ?
    """, (name, symbol_x, symbol_o, skin_id))
    conn.commit()
    conn.close()

def get_admin_username(admin_id: int) -> str:
    user = get_user(admin_id)
    if user and user['username']:
        return f"@{user['username']}"
    return f"Админ#{admin_id}"

def give_skin(user_id: int, skin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, skin_id))
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

# ==================== Market ====================

def get_market_listings(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, s.name, s.symbol_x, s.symbol_o, u.username as seller_name,
               cr.username as creator_username, s.creator_id, s.added_by_admin
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
    c.execute("INSERT INTO market (skin_id, seller_id, price) VALUES (?, ?, ?)", (skin_id, seller_id, price))
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
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (buyer_id, listing['skin_id']))
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
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (seller_id, row['skin_id']))
    conn.commit()
    conn.close()
    return True

# ==================== Cases ====================

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
    c.execute("INSERT OR IGNORE INTO user_skins (user_id, skin_id) VALUES (?, ?)", (user_id, won_skin_id))
    c.execute("INSERT INTO transactions (user_id, amount, reason) VALUES (?, ?, ?)",
              (user_id, -case['cost'], f"Открытие кейса #{case_id}"))
    conn.commit()
    conn.close()
    return True, won_skin_id

def create_case_by_admin(name: str, cost: int, skin_ids: list, admin_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO cases (name, cost, skin_ids, added_by_admin)
        VALUES (?, ?, ?, ?)
    """, (name, cost, ','.join(map(str, skin_ids)), admin_id))
    case_id = c.lastrowid
    conn.commit()
    conn.close()
    return case_id

def edit_case(case_id: int, name: str, cost: int, skin_ids: list):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE cases SET name = ?, cost = ?, skin_ids = ? WHERE case_id = ?
    """, (name, cost, ','.join(map(str, skin_ids)), case_id))
    conn.commit()
    conn.close()

def delete_case_db(case_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
    conn.commit()
    conn.close()

def get_all_cases_admin(page: int = 0, per_page: int = 10):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cases ORDER BY case_id DESC LIMIT ? OFFSET ?",
              (per_page, page * per_page))
    rows = c.fetchall()
    total = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total

# ==================== Games ====================

def create_game(player1_id: int, player2_id: int, 
