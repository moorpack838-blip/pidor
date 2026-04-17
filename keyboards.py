from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Профиль", callback_data="profile")
    kb.button(text="🎮 Играть", callback_data="play_menu")
    kb.button(text="🎨 Скины", callback_data="skins_menu")
    kb.button(text="🛒 Рынок", callback_data="market_page_0")
    kb.button(text="📦 Кейсы", callback_data="cases_menu")
    kb.button(text="👥 Друзья", callback_data="friends_menu")
    kb.button(text="🏆 Топ", callback_data="leaderboard_0")
    kb.adjust(2)
    return kb.as_markup()

def play_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Найти матч", callback_data="matchmaking_join")
    kb.button(text="🤝 Играть с другом", callback_data="play_friend")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def game_board_kb(board: str, game_id: int, active: bool = True):
    kb = InlineKeyboardBuilder()
    symbols = {'X': '❌', 'O': '⭕', '-': '⬜'}
    for i, cell in enumerate(board):
        if cell == '-' and active:
            kb.button(text="⬜", callback_data=f"move_{game_id}_{i}")
        else:
            kb.button(text=symbols.get(cell, cell), callback_data="noop")
    kb.adjust(3)
    return kb.as_markup()

def game_board_custom_kb(board: str, game_id: int, skin_x: str, skin_o: str, active: bool = True):
    kb = InlineKeyboardBuilder()
    for i, cell in enumerate(board):
        if cell == 'X':
            kb.button(text=skin_x, callback_data="noop")
        elif cell == 'O':
            kb.button(text=skin_o, callback_data="noop")
        elif active:
            kb.button(text="⬜", callback_data=f"move_{game_id}_{i}")
        else:
            kb.button(text="⬜", callback_data="noop")
    kb.adjust(3)
    return kb.as_markup()

def skins_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎨 Мои скины", callback_data="my_skins_0")
    kb.button(text="✏️ Создать скин", callback_data="create_skin_start")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def market_kb(listings, page, total_pages):
    kb = InlineKeyboardBuilder()
    for l in listings:
        kb.button(
            text=f"{l['name']} | {l['symbol_x']}/{l['symbol_o']} | 💰{l['price']}",
            callback_data=f"market_buy_{l['listing_id']}"
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"market_page_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"market_page_{page+1}"))
    kb.row(*nav)
    kb.button(text="📤 Мои лоты", callback_data="my_listings")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def my_skins_kb(skins, page, total_pages):
    kb = InlineKeyboardBuilder()
    for s in skins:
        kb.button(
            text=f"{s['name']} [{s['symbol_x']}/{s['symbol_o']}]",
            callback_data=f"skin_action_{s['skin_id']}"
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"my_skins_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"my_skins_{page+1}"))
    kb.row(*nav)
    kb.button(text="◀️ Назад", callback_data="skins_menu")
    kb.adjust(1)
    return kb.as_markup()

def skin_action_kb(skin_id: int, seller_listing: bool = False):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎮 Надеть X", callback_data=f"equip_x_{skin_id}")
    kb.button(text="🎮 Надеть O", callback_data=f"equip_o_{skin_id}")
    kb.button(text="💰 Выставить на продажу", callback_data=f"list_skin_{skin_id}")
    kb.button(text="◀️ Назад", callback_data="my_skins_0")
    kb.adjust(2)
    return kb.as_markup()

def cases_kb(cases):
    kb = InlineKeyboardBuilder()
    for c in cases:
        kb.button(text=f"📦 {c['name']} | 💰{c['cost']}", callback_data=f"open_case_{c['case_id']}")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def friends_kb(friends):
    kb = InlineKeyboardBuilder()
    for f in friends:
        kb.button(text=f"👤 @{f['username']} | {f['display_name']}", callback_data=f"friend_view_{f['user_id']}")
    kb.button(text="➕ Добавить друга", callback_data="add_friend_start")
    kb.button(text="◀️ Назад", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()

def leaderboard_kb(page, total_pages):
    kb = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"leaderboard_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"leaderboard_{page+1}"))
    kb.row(*nav)
    kb.button(text="◀️ Назад", callback_data="main_menu")
    return kb.as_markup()

def admin_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👥 Игроки", callback_data="admin_users_0")
    kb.button(text="🎨 Скины", callback_data="admin_skins_0")
    kb.button(text="🎮 Игры", callback_data="admin_games_0")
    kb.button(text="📦 Создать кейс", callback_data="admin_create_case")
    kb.button(text="➕ Добавить скин", callback_data="admin_add_skin")
    kb.button(text="💰 Выдать монеты", callback_data="admin_give_coins")
    kb.button(text="🏅 Выдать скин игроку", callback_data="admin_give_skin")
    kb.button(text="◀️ Главное меню", callback_data="main_menu")
    kb.adjust(2)
    return kb.as_markup()

def admin_users_kb(users, page, total, per_page=10):
    from config import VERIFIED_USERS
    kb = InlineKeyboardBuilder()
    total_pages = (total + per_page - 1) // per_page
    for u in users:
        check = "✅ " if u['user_id'] in VERIFIED_USERS else ""
        rank_name, rank_emoji = __import__('database').get_rank(u['elo'])
        kb.button(
            text=f"{check}@{u['username']} | {rank_emoji}{u['elo']} | 💰{u['coins']}",
            callback_data=f"admin_user_{u['user_id']}"
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_{page+1}"))
    kb.row(*nav)
    kb.button(text="🔍 Найти по @username", callback_data="admin_search_user")
    kb.button(text="◀️ Админ панель", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def admin_user_detail_kb(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Изменить монеты", callback_data=f"admin_edit_coins_{user_id}")
    kb.button(text="🏅 Изменить ELO", callback_data=f"admin_edit_elo_{user_id}")
    kb.button(text="🎨 Выдать скин", callback_data=f"admin_give_skin_to_{user_id}")
    kb.button(text="◀️ Назад", callback_data="admin_users_0")
    kb.adjust(2)
    return kb.as_markup()

def admin_skins_kb(skins, page, total, per_page=10):
    kb = InlineKeyboardBuilder()
    total_pages = (total + per_page - 1) // per_page
    for s in skins:
        creator = f"@{s['creator_username']}" if s['creator_username'] else "Админ"
        kb.button(
            text=f"#{s['skin_id']} {s['name']} [{s['symbol_x']}/{s['symbol_o']}] by {creator}",
            callback_data=f"admin_skin_{s['skin_id']}"
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_skins_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_skins_{page+1}"))
    kb.row(*nav)
    kb.button(text="◀️ Админ панель", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def admin_skin_detail_kb(skin_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑️ Удалить скин", callback_data=f"admin_del_skin_{skin_id}")
    kb.button(text="◀️ Назад", callback_data="admin_skins_0")
    kb.adjust(1)
    return kb.as_markup()

def admin_games_kb(games, page, total, per_page=10):
    kb = InlineKeyboardBuilder()
    total_pages = (total + per_page - 1) // per_page
    for g in games:
        p1 = f"@{g['p1_username']}" if g['p1_username'] else f"#{g['player1_id']}"
        p2 = f"@{g['p2_username']}" if g['p2_username'] else f"#{g['player2_id']}"
        status_emoji = {"active": "🟢", "finished": "🔴", "cancelled": "⛔"}.get(g['status'], "❓")
        kb.button(
            text=f"#{g['game_id']} {status_emoji} {p1} vs {p2}",
            callback_data=f"admin_game_{g['game_id']}"
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_games_{page-1}"))
    nav.append(InlineKeyboardButton(text=f"{page+1}/{max(total_pages,1)}", callback_data="noop"))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_games_{page+1}"))
    kb.row(*nav)
    kb.button(text="◀️ Админ панель", callback_data="admin_panel")
    kb.adjust(1)
    return kb.as_markup()

def admin_game_detail_kb(game_id: int, status: str):
    kb = InlineKeyboardBuilder()
    if status == 'active':
        kb.button(text="⛔ Отменить (без ELO)", callback_data=f"admin_cancel_game_{game_id}")
    kb.button(text="◀️ Назад", callback_data="admin_games_0")
    kb.adjust(1)
    return kb.as_markup()

def back_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Главное меню", callback_data="main_menu")
    return kb.as_markup()

def confirm_kb(action: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да", callback_data=f"confirm_{action}")
    kb.button(text="❌ Нет", callback_data="main_menu")
    kb.adjust(2)
    return kb.as_markup()