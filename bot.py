import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardButton
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
import keyboards as kb
from config import (
    BOT_TOKEN, ADMINS, VERIFIED_USERS,
    SKIN_CREATE_COST, SKIN_MIN_PRICE, SKIN_MAX_PRICE,
    CASE_COST, ELO_WIN, ELO_LOSS
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ==================== FSM States ====================

class RenameState(StatesGroup):
    waiting_name = State()

class CreateSkinState(StatesGroup):
    waiting_name = State()
    waiting_x = State()
    waiting_o = State()

class SellSkinState(StatesGroup):
    waiting_price = State()
    skin_id = State()

class AddFriendState(StatesGroup):
    waiting_game_id = State()

class PlayFriendState(StatesGroup):
    waiting_game_id = State()

class AdminGiveCoinsState(StatesGroup):
    waiting_username = State()
    waiting_amount = State()
    target_id = State()

class AdminEditCoinsState(StatesGroup):
    waiting_amount = State()
    target_id = State()

class AdminEditEloState(StatesGroup):
    waiting_elo = State()
    target_id = State()

class AdminGiveSkinState(StatesGroup):
    waiting_username = State()
    waiting_skin_id = State()
    target_id = State()

class AdminGiveSkinToState(StatesGroup):
    waiting_skin_id = State()
    target_id = State()

class AdminAddSkinState(StatesGroup):
    waiting_name = State()
    waiting_x = State()
    waiting_o = State()

class AdminCreateCaseState(StatesGroup):
    waiting_name = State()
    waiting_cost = State()
    waiting_skin_ids = State()

class AdminSearchUserState(StatesGroup):
    waiting_username = State()

# ==================== Helpers ====================

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def get_verified_badge(user_id: int) -> str:
    return "✅ " if user_id in VERIFIED_USERS else ""

def format_profile(user: dict) -> str:
    rank_name, rank_emoji = db.get_rank(user['elo'])
    badge = get_verified_badge(user['user_id'])
    total = user['wins'] + user['losses'] + user['draws']
    wr = f"{round(user['wins']/total*100)}%" if total > 0 else "N/A"
    return (
        f"👤 <b>{badge}{user['display_name']}</b>\n"
        f"🆔 Game ID: <code>{user['game_id']}</code>\n"
        f"📛 @{user['username']}\n"
        f"🏆 Ранг: {rank_emoji} {rank_name} ({user['elo']} ELO)\n"
        f"💰 Монеты: {user['coins']}\n"
        f"🎮 Игры: {total} | ✅{user['wins']} ❌{user['losses']} 🤝{user['draws']}\n"
        f"📊 Winrate: {wr}"
    )

def format_board(board: str, skin_x: str = '❌', skin_o: str = '⭕') -> str:
    result = ""
    symbols = {'X': skin_x, 'O': skin_o, '-': '⬜'}
    for i, c in enumerate(board):
        result += symbols.get(c, c)
        if (i+1) % 3 == 0:
            result += '\n'
    return result

async def ensure_user(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        username = message.from_user.username or f"user{message.from_user.id}"
        display_name = message.from_user.full_name or username
        db.create_user(message.from_user.id, username, display_name)
        user = db.get_user(message.from_user.id)
    else:
        # Обновляем username если изменился
        current_username = message.from_user.username or f"user{message.from_user.id}"
        if user['username'] != current_username:
            db.update_username(message.from_user.id, current_username)
            user = db.get_user(message.from_user.id)
    return user

# ==================== Start / Main Menu ====================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await ensure_user(message)
    badge = get_verified_badge(user['user_id'])
    await message.answer(
        f"🎮 <b>Крестики-Нолики</b>\n\n"
        f"Привет, {badge}<b>{user['display_name']}</b>!\n"
        f"Добро пожаловать в игру!",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await ensure_user(call.message)
    if not user:
        user = db.get_user(call.from_user.id)
    badge = get_verified_badge(call.from_user.id)
    await call.message.edit_text(
        f"🎮 <b>Главное меню</b>\n\nПривет, {badge}<b>{user['display_name']}</b>!",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

# ==================== Profile ====================

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    if not user:
        await call.answer("Сначала напиши /start")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Изменить ник", callback_data="rename")
    builder.button(text="◀️ Назад", callback_data="main_menu")
    builder.adjust(1)
    await call.message.edit_text(
        format_profile(user),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "rename")
async def cb_rename(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "✏️ Введи новый отображаемый ник (2-20 символов):",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(RenameState.waiting_name)

@router.message(RenameState.waiting_name)
async def process_rename(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 20:
        await message.answer("❌ Ник должен быть от 2 до 20 символов!")
        return
    db.update_display_name(message.from_user.id, name)
    await state.clear()
    await message.answer(f"✅ Ник изменён на <b>{name}</b>!", parse_mode="HTML",
                         reply_markup=kb.main_menu_kb())

# ==================== Play Menu ====================

@router.callback_query(F.data == "play_menu")
async def cb_play_menu(call: CallbackQuery):
    await call.message.edit_text("🎮 <b>Выбери режим игры:</b>",
                                  reply_markup=kb.play_menu_kb(), parse_mode="HTML")

# ==================== Matchmaking ====================

@router.callback_query(F.data == "matchmaking_join")
async def cb_matchmaking_join(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    if not user:
        await call.answer("Сначала /start")
        return
    
    active = db.get_active_game(call.from_user.id)
    if active:
        await call.answer("У тебя уже есть активная игра!")
        return
    
    opponent = db.find_match(call.from_user.id, user['elo'])
    if opponent:
        db.remove_from_matchmaking(call.from_user.id)
        db.remove_from_matchmaking(opponent['user_id'])
        
        # Определяем скины
        skin_x_sym = get_player_symbol(call.from_user.id, 'x')
        skin_o_sym = get_player_symbol(opponent['user_id'], 'o')
        
        game_id = db.create_game(call.from_user.id, opponent['user_id'], skin_x_sym, skin_o_sym)
        game = db.get_game(game_id)
        
        opp_user = db.get_user(opponent['user_id'])
        cur_user = user
        
        rank1, re1 = db.get_rank(cur_user['elo'])
        rank2, re2 = db.get_rank(opp_user['elo'])
        
        board_text = format_board(game['board'], skin_x_sym, skin_o_sym)
        game_msg = (
            f"🎮 <b>Игра найдена!</b>\n\n"
            f"{get_verified_badge(cur_user['user_id'])}<b>{cur_user['display_name']}</b> "
            f"({re1} {cur_user['elo']}) {skin_x_sym}\n"
            f"vs\n"
            f"{get_verified_badge(opp_user['user_id'])}<b>{opp_user['display_name']}</b> "
            f"({re2} {opp_user['elo']}) {skin_o_sym}\n\n"
            f"{board_text}\n"
            f"🎯 Ход: <b>{cur_user['display_name']}</b>"
        )
        
        board_kb = kb.game_board_custom_kb(game['board'], game_id, skin_x_sym, skin_o_sym)
        
        await call.message.edit_text(game_msg, reply_markup=board_kb, parse_mode="HTML")
        try:
            await bot.send_message(
                opponent['user_id'],
                game_msg,
                reply_markup=board_kb,
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        db.add_to_matchmaking(call.from_user.id, user['elo'])
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="❌ Отменить поиск", callback_data="matchmaking_cancel")
        await call.message.edit_text(
            f"🔍 <b>Поиск соперника...</b>\n\n"
            f"Твой ELO: {user['elo']}\n"
            f"Поиск в диапазоне ±300 ELO",
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )

def get_player_symbol(user_id: int, slot: str) -> str:
    user = db.get_user(user_id)
    if not user:
        return 'X' if slot == 'x' else 'O'
    skin_id = user.get(f'active_skin_{slot}')
    if skin_id:
        skin = db.get_skin(int(skin_id))
        if skin:
            return skin[f'symbol_{slot}']
    return '❌' if slot == 'x' else '⭕'

@router.callback_query(F.data == "matchmaking_cancel")
async def cb_matchmaking_cancel(call: CallbackQuery):
    db.remove_from_matchmaking(call.from_user.id)
    await call.message.edit_text("❌ Поиск отменён.", reply_markup=kb.main_menu_kb())

# ==================== Play with Friend ====================

@router.callback_query(F.data == "play_friend")
async def cb_play_friend(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "👥 Введи Game ID друга (8 символов):",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(PlayFriendState.waiting_game_id)

@router.message(PlayFriendState.waiting_game_id)
async def process_play_friend(message: Message, state: FSMContext):
    game_id_str = message.text.strip().upper()
    opponent = db.get_user_by_game_id(game_id_str)
    if not opponent:
        await message.answer("❌ Игрок с таким Game ID не найден!")
        return
    if opponent['user_id'] == message.from_user.id:
        await message.answer("❌ Нельзя играть с собой!")
        return
    
    user = db.get_user(message.from_user.id)
    skin_x_sym = get_player_symbol(message.from_user.id, 'x')
    skin_o_sym = get_player_symbol(opponent['user_id'], 'o')
    
    game_id = db.create_game(message.from_user.id, opponent['user_id'], skin_x_sym, skin_o_sym)
    game = db.get_game(game_id)
    
    board_text = format_board(game['board'], skin_x_sym, skin_o_sym)
    rank1, re1 = db.get_rank(user['elo'])
    rank2, re2 = db.get_rank(opponent['elo'])
    
    game_msg = (
        f"🎮 <b>Игра с другом!</b>\n\n"
        f"{get_verified_badge(user['user_id'])}<b>{user['display_name']}</b> "
        f"({re1} {user['elo']}) {skin_x_sym}\n"
        f"vs\n"
        f"{get_verified_badge(opponent['user_id'])}<b>{opponent['display_name']}</b> "
        f"({re2} {opponent['elo']}) {skin_o_sym}\n\n"
        f"{board_text}\n"
        f"🎯 Ход: <b>{user['display_name']}</b>"
    )
    
    board_kb = kb.game_board_custom_kb(game['board'], game_id, skin_x_sym, skin_o_sym)
    await state.clear()
    await message.answer(game_msg, reply_markup=board_kb, parse_mode="HTML")
    try:
        await bot.send_message(opponent['user_id'], game_msg, reply_markup=board_kb, parse_mode="HTML")
    except Exception:
        pass

# ==================== Game Move ====================

@router.callback_query(F.data.startswith("move_"))
async def cb_move(call: CallbackQuery):
    parts = call.data.split("_")
    game_id = int(parts[1])
    position = int(parts[2])
    
    game = db.get_game(game_id)
    if not game:
        await call.answer("Игра не найдена")
        return
    if game['status'] != 'active':
        await call.answer("Игра уже завершена")
        return
    if game['current_turn'] != call.from_user.id:
        await call.answer("Сейчас не твой ход!")
        return
    
    skin_x = game['skin_x']
    skin_o = game['skin_o']
    
    success, result = db.make_move(game_id, call.from_user.id, position)
    if not success:
        await call.answer(result)
        return
    
    game = db.get_game(game_id)
    p1 = db.get_user(game['player1_id'])
    p2 = db.get_user(game['player2_id'])
    
    board_text = format_board(game['board'], skin_x, skin_o)
    
    if result in ('X', 'O'):
        winner_id = game['winner_id']
        loser_id = game['player2_id'] if winner_id == game['player1_id'] else game['player1_id']
        winner = db.get_user(winner_id)
        
        db.record_win(winner_id)
        db.record_loss(loser_id)
        
        end_msg = (
            f"🎮 <b>Игра завершена!</b>\n\n"
            f"{board_text}\n"
            f"🏆 Победитель: {get_verified_badge(winner_id)}<b>{winner['display_name']}</b>\n"
            f"📈 +{ELO_WIN} ELO | 💰 +50 монет"
        )
        finished_kb = kb.back_main_kb()
        await call.message.edit_text(end_msg, reply_markup=finished_kb, parse_mode="HTML")
        other_id = game['player2_id'] if call.from_user.id == game['player1_id'] else game['player1_id']
        try:
            await bot.send_message(other_id, end_msg, reply_markup=finished_kb, parse_mode="HTML")
        except Exception:
            pass
    elif result == 'draw':
        db.record_draw(game['player1_id'])
        db.record_draw(game['player2_id'])
        end_msg = (
            f"🎮 <b>Ничья!</b>\n\n"
            f"{board_text}\n"
            f"🤝 Оба получают +5 ELO | 💰 +10 монет"
        )
        finished_kb = kb.back_main_kb()
        await call.message.edit_text(end_msg, reply_markup=finished_kb, parse_mode="HTML")
        other_id = game['player2_id'] if call.from_user.id == game['player1_id'] else game['player1_id']
        try:
            await bot.send_message(other_id, end_msg, reply_markup=finished_kb, parse_mode="HTML")
        except Exception:
            pass
    else:
        current_turn_user = db.get_user(game['current_turn'])
        updated_msg = (
            f"🎮 <b>Игра #{game_id}</b>\n\n"
            f"{get_verified_badge(p1['user_id'])}<b>{p1['display_name']}</b> {skin_x} vs "
            f"{get_verified_badge(p2['user_id'])}<b>{p2['display_name']}</b> {skin_o}\n\n"
            f"{board_text}\n"
            f"🎯 Ход: <b>{current_turn_user['display_name']}</b>"
        )
        board_kb = kb.game_board_custom_kb(game['board'], game_id, skin_x, skin_o)
        await call.message.edit_text(updated_msg, reply_markup=board_kb, parse_mode="HTML")
        other_id = game['player2_id'] if call.from_user.id == game['player1_id'] else game['player1_id']
        try:
            await bot.send_message(other_id, updated_msg, reply_markup=board_kb, parse_mode="HTML")
        except Exception:
            pass

# ==================== Skins ====================

@router.callback_query(F.data == "skins_menu")
async def cb_skins_menu(call: CallbackQuery):
    await call.message.edit_text("🎨 <b>Меню скинов</b>", reply_markup=kb.skins_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("my_skins_"))
async def cb_my_skins(call: CallbackQuery):
    page = int(call.data.split("_")[2])
    per_page = 8
    skins = db.get_all_skins(call.from_user.id)
    total_pages = (len(skins) + per_page - 1) // per_page
    page_skins = skins[page * per_page:(page + 1) * per_page]
    
    if not page_skins and page == 0:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ Создать скин", callback_data="create_skin_start")
        builder.button(text="◀️ Назад", callback_data="skins_menu")
        builder.adjust(1)
        await call.message.edit_text(
            "🎨 У тебя нет скинов!\nСоздай или купи на рынке.",
            reply_markup=builder.as_markup()
        )
        return
    
    await call.message.edit_text(
        f"🎨 <b>Мои скины</b> ({len(skins)} шт.)",
        reply_markup=kb.my_skins_kb(page_skins, page, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("skin_action_"))
async def cb_skin_action(call: CallbackQuery):
    skin_id = int(call.data.split("_")[2])
    skin = db.get_skin(skin_id)
    if not skin:
        await call.answer("Скин не найден")
        return
    creator = f"@{skin['creator_username']}" if skin['creator_username'] else "Администратор"
    text = (
        f"🎨 <b>{skin['name']}</b>\n"
        f"✨ Редкость: <b>{skin['rarity']}</b>\n"
        f"❌ Символ X: <b>{skin['symbol_x']}</b>\n"
        f"⭕ Символ O: <b>{skin['symbol_o']}</b>\n"
        f"👤 Автор: {creator}"
    )
    await call.message.edit_text(text, reply_markup=kb.skin_action_kb(skin_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("equip_x_"))
async def cb_equip_x(call: CallbackQuery):
    skin_id = int(call.data.split("_")[2])
    if not db.has_skin(call.from_user.id, skin_id):
        await call.answer("У тебя нет этого скина!")
        return
    db.set_active_skin(call.from_user.id, skin_id, 'x')
    await call.answer("✅ Скин надет на X!")

@router.callback_query(F.data.startswith("equip_o_"))
async def cb_equip_o(call: CallbackQuery):
    skin_id = int(call.data.split("_")[2])
    if not db.has_skin(call.from_user.id, skin_id):
        await call.answer("У тебя нет этого скина!")
        return
    db.set_active_skin(call.from_user.id, skin_id, 'o')
    await call.answer("✅ Скин надет на O!")

@router.callback_query(F.data == "create_skin_start")
async def cb_create_skin_start(call: CallbackQuery, state: FSMContext):
    user = db.get_user(call.from_user.id)
    if user['coins'] < SKIN_CREATE_COST:
        await call.message.edit_text(
            f"❌ Недостаточно монет!\nНужно: {SKIN_CREATE_COST} 💰\nУ тебя: {user['coins']} 💰",
            reply_markup=kb.back_main_kb()
        )
        return
    await call.message.edit_text(
        f"✏️ <b>Создание скина</b>\n\n"
        f"Стоимость: {SKIN_CREATE_COST} 💰\n\n"
        f"Введи название скина:",
        reply_markup=kb.back_main_kb(),
        parse_mode="HTML"
    )
    await state.set_state(CreateSkinState.waiting_name)

@router.message(CreateSkinState.waiting_name)
async def process_skin_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 30:
        await message.answer("❌ Название от 2 до 30 символов!")
        return
    await state.update_data(skin_name=name)
    await message.answer(
        f"✏️ Название: <b>{name}</b>\n\n"
        f"Введи символ/эмодзи для X (1 символ или 1 эмодзи):",
        parse_mode="HTML"
    )
    await state.set_state(CreateSkinState.waiting_x)

@router.message(CreateSkinState.waiting_x)
async def process_skin_x(message: Message, state: FSMContext):
    sym = message.text.strip()
    if len(sym) > 4:
        await message.answer("❌ Символ слишком длинный! Используй 1 эмодзи или символ.")
        return
    await state.update_data(skin_x=sym)
    data = await state.get_data()
    await message.answer(
        f"✏️ X: <b>{sym}</b>\n\n"
        f"Теперь введи символ/эмодзи для O:",
        parse_mode="HTML"
    )
    await state.set_state(CreateSkinState.waiting_o)

@router.message(CreateSkinState.waiting_o)
async def process_skin_o(message: Message, state: FSMContext):
    sym = message.text.strip()
    if len(sym) > 4:
        await message.answer("❌ Символ слишком длинный!")
        return
    
    data = await state.get_data()
    user = db.get_user(message.from_user.id)
    
    if user['coins'] < SKIN_CREATE_COST:
        await message.answer("❌ Недостаточно монет!")
        await state.clear()
        return
    
    db.add_coins(message.from_user.id, -SKIN_CREATE_COST, "Создание скина")
    skin_id = db.create_skin(data['skin_name'], data['skin_x'], sym, message.from_user.id)
    db.give_skin(message.from_user.id, skin_id)
    
    await state.clear()
    await message.answer(
        f"🎨 <b>Скин создан!</b>\n\n"
        f"📛 Название: <b>{data['skin_name']}</b>\n"
        f"❌ X: <b>{data['skin_x']}</b>\n"
        f"⭕ O: <b>{sym}</b>\n"
        f"✨ Редкость: <b>Кастомный</b>\n\n"
        f"💰 Списано: {SKIN_CREATE_COST} монет",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

# ==================== Market ====================

@router.callback_query(F.data.startswith("market_page_"))
async def cb_market_page(call: CallbackQuery):
    page = int(call.data.split("_")[2])
    per_page = 8
    listings = db.get_market_listings(page, per_page)
    total = db.count_market_listings()
    total_pages = (total + per_page - 1) // per_page
    
    if not listings and page == 0:
        await call.message.edit_text(
            "🛒 <b>Рынок</b>\n\nПока нет лотов!",
            reply_markup=kb.back_main_kb(),
            parse_mode="HTML"
        )
        return
    
    await call.message.edit_text(
        f"🛒 <b>Рынок скинов</b> (всего: {total})\n\n"
        f"💡 25% от продажи идёт создателю скина",
        reply_markup=kb.market_kb(listings, page, total_pages),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("market_buy_"))
async def cb_market_buy(call: CallbackQuery):
    listing_id = int(call.data.split("_")[2])
    
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, s.name, s.symbol_x, s.symbol_o, u.username as seller_name,
               cr.username as creator_username, s.creator_id
        FROM market m
        JOIN skins s ON m.skin_id = s.skin_id
        JOIN users u ON m.seller_id = u.user_id
        LEFT JOIN users cr ON s.creator_id = cr.user_id
        WHERE m.listing_id = ?
    """, (listing_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        await call.answer("Лот не найден или уже куплен!")
        return
    
    listing = dict(row)
    from config import MARKET_CREATOR_PERCENT
    creator_cut = int(listing['price'] * MARKET_CREATOR_PERCENT)
    seller_gets = listing['price'] - creator_cut
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Купить за {listing['price']} 💰", callback_data=f"confirm_buy_{listing_id}")
    builder.button(text="❌ Отмена", callback_data="market_page_0")
    builder.adjust(1)
    
    creator_info = f"@{listing['creator_username']}" if listing['creator_username'] else "Неизвестен"
    
    await call.message.edit_text(
        f"🛒 <b>Покупка скина</b>\n\n"
        f"📛 {listing['name']}\n"
        f"❌ X: {listing['symbol_x']} | ⭕ O: {listing['symbol_o']}\n"
        f"💰 Цена: {listing['price']}\n"
        f"👤 Продавец: @{listing['seller_name']}\n"
        f"🎨 Создатель: {creator_info} (получит {creator_cut} 💰)\n"
        f"💵 Продавец получит: {seller_gets} 💰",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_buy_"))
async def cb_confirm_buy(call: CallbackQuery):
    listing_id = int(call.data.split("_")[2])
    user = db.get_user(call.from_user.id)
    
    success, result = db.buy_from_market(call.from_user.id, listing_id)
    if not success:
        await call.answer(f"❌ {result}")
        return
    
    if isinstance(result, dict):
        creator_id = result.get('creator_id')
        creator_cut = result.get('creator_cut', 0)
        if creator_id and creator_id != call.from_user.id:
            try:
                await bot.send_message(
                    creator_id,
                    f"💰 Ты получил <b>{creator_cut}</b> монет как создатель скина!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    
    await call.message.edit_text(
        "✅ <b>Скин успешно куплен!</b>",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("list_skin_"))
async def cb_list_skin(call: CallbackQuery, state: FSMContext):
    skin_id = int(call.data.split("_")[2])
    if not db.has_skin(call.from_user.id, skin_id):
        await call.answer("У тебя нет этого скина!")
        return
    await state.update_data(listing_skin_id=skin_id)
    await call.message.edit_text(
        f"💰 Введи цену продажи ({SKIN_MIN_PRICE} - {SKIN_MAX_PRICE} монет):",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(SellSkinState.waiting_price)

@router.message(SellSkinState.waiting_price)
async def process_sell_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    
    if price < SKIN_MIN_PRICE or price > SKIN_MAX_PRICE:
        await message.answer(f"❌ Цена должна быть от {SKIN_MIN_PRICE} до {SKIN_MAX_PRICE}!")
        return
    
    data = await state.get_data()
    skin_id = data['listing_skin_id']
    
    if not db.has_skin(message.from_user.id, skin_id):
        await message.answer("❌ Скин не найден!")
        await state.clear()
        return
    
    db.list_skin_on_market(message.from_user.id, skin_id, price)
    await state.clear()
    await message.answer(
        f"✅ Скин выставлен на рынок за <b>{price}</b> 💰!",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "my_listings")
async def cb_my_listings(call: CallbackQuery):
    conn = db.get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT m.*, s.name, s.symbol_x, s.symbol_o 
        FROM market m 
        JOIN skins s ON m.skin_id = s.skin_id 
        WHERE m.seller_id = ?
    """, (call.from_user.id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    if not rows:
        builder.button(text="◀️ Назад", callback_data="market_page_0")
        await call.message.edit_text("📦 У тебя нет активных лотов.", reply_markup=builder.as_markup())
        return
    
    text = "📦 <b>Мои лоты:</b>\n\n"
    for r in rows:
        text += f"#{r['listing_id']} {r['name']} [{r['symbol_x']}/{r['symbol_o']}] — {r['price']} 💰\n"
        builder.button(text=f"❌ Снять #{r['listing_id']}", callback_data=f"unlist_{r['listing_id']}")
    
    builder.button(text="◀️ Назад", callback_data="market_page_0")
    builder.adjust(1)
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("unlist_"))
async def cb_unlist(call: CallbackQuery):
    listing_id = int(call.data.split("_")[1])
    success = db.remove_my_listing(call.from_user.id, listing_id)
    if success:
        await call.answer("✅ Лот снят, скин возвращён!")
    else:
        await call.answer("❌ Ошибка!")
    await cb_my_listings(call)

# ==================== Cases ====================

@router.callback_query(F.data == "cases_menu")
async def cb_cases_menu(call: CallbackQuery):
    cases = db.get_cases()
    if not cases:
        await call.message.edit_text(
            "📦 <b>Кейсы</b>\n\nПока нет доступных кейсов!",
            reply_markup=kb.back_main_kb(),
            parse_mode="HTML"
        )
        return
    await call.message.edit_text(
        "📦 <b>Выбери кейс:</b>",
        reply_markup=kb.cases_kb(cases),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("open_case_"))
async def cb_open_case(call: CallbackQuery):
    case_id = int(call.data.split("_")[2])
    case = db.get_case(case_id)
    if not case:
        await call.answer("Кейс не найден!")
        return
    
    user = db.get_user(call.from_user.id)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Открыть за {case['cost']} 💰", callback_data=f"confirm_case_{case_id}")
    builder.button(text="❌ Отмена", callback_data="cases_menu")
    builder.adjust(1)
    
    skin_ids = [int(x) for x in case['skin_ids'].split(',') if x.strip()]
    skins_preview = ""
    for sid in skin_ids[:5]:
        s = db.get_skin(sid)
        if s:
            creator = f"@{s['creator_username']}" if s['creator_username'] else "Админ"
            skins_preview += f"• {s['name']} [{s['symbol_x']}/{s['symbol_o']}] by {creator}\n"
    
    await call.message.edit_text(
        f"📦 <b>{case['name']}</b>\n"
        f"💰 Стоимость: {case['cost']}\n"
        f"💳 У тебя: {user['coins']}\n\n"
        f"🎁 Возможные скины:\n{skins_preview}",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("confirm_case_"))
async def cb_confirm_case(call: CallbackQuery):
    case_id = int(call.data.split("_")[2])
    success, result = db.open_case(call.from_user.id, case_id)
    if not success:
        await call.answer(f"❌ {result}")
        return
    
    skin = db.get_skin(result)
    creator = f"@{skin['creator_username']}" if skin['creator_username'] else "Администратор"
    
    await call.message.edit_text(
        f"🎊 <b>Кейс открыт!</b>\n\n"
        f"Ты получил:\n"
        f"🎨 <b>{skin['name']}</b>\n"
        f"✨ Редкость: <b>{skin['rarity']}</b>\n"
        f"❌ X: {skin['symbol_x']} | ⭕ O: {skin['symbol_o']}\n"
        f"👤 Создатель: {creator}",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

# ==================== Friends ====================

@router.callback_query(F.data == "friends_menu")
async def cb_friends_menu(call: CallbackQuery):
    friends = db.get_friends(call.from_user.id)
    await call.message.edit_text(
        f"👥 <b>Друзья</b> ({len(friends)})",
        reply_markup=kb.friends_kb(friends),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "add_friend_start")
async def cb_add_friend(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "👥 Введи Game ID друга:",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(AddFriendState.waiting_game_id)

@router.message(AddFriendState.waiting_game_id)
async def process_add_friend(message: Message, state: FSMContext):
    game_id_str = message.text.strip().upper()
    friend = db.get_user_by_game_id(game_id_str)
    if not friend:
        await message.answer("❌ Игрок не найден!")
        return
    if friend['user_id'] == message.from_user.id:
        await message.answer("❌ Нельзя добавить себя!")
        return
    db.add_friend(message.from_user.id, friend['user_id'])
    await state.clear()
    badge = get_verified_badge(friend['user_id'])
    await message.answer(
        f"✅ {badge}<b>{friend['display_name']}</b> добавлен в друзья!",
        reply_markup=kb.main_menu_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("friend_view_"))
async def cb_friend_view(call: CallbackQuery):
    friend_id = int(call.data.split("_")[2])
    friend = db.get_user(friend_id)
    if not friend:
        await call.answer("Игрок не найден")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 Вызвать на игру", callback_data=f"challenge_{friend_id}")
    builder.button(text="◀️ Назад", callback_data="friends_menu")
    builder.adjust(1)
    await call.message.edit_text(
        format_profile(friend),
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("challenge_"))
async def cb_challenge(call: CallbackQuery):
    friend_id = int(call.data.split("_")[1])
    friend = db.get_user(friend_id)
    user = db.get_user(call.from_user.id)
    
    skin_x_sym = get_player_symbol(call.from_user.id, 'x')
    skin_o_sym = get_player_symbol(friend_id, 'o')
    
    game_id = db.create_game(call.from_user.id, friend_id, skin_x_sym, skin_o_sym)
    game = db.get_game(game_id)
    
    rank1, re1 = db.get_rank(user['elo'])
    rank2, re2 = db.get_rank(friend['elo'])
    
    game_msg = (
        f"🎮 <b>Вызов на игру!</b>\n\n"
        f"{get_verified_badge(user['user_id'])}<b>{user['display_name']}</b> "
        f"({re1} {user['elo']}) {skin_x_sym}\nvs\n"
        f"{get_verified_badge(friend_id)}<b>{friend['display_name']}</b> "
        f"({re2} {friend['elo']}) {skin_o_sym}\n\n"
        f"{format_board(game['board'], skin_x_sym, skin_o_sym)}\n"
        f"🎯 Ход: <b>{user['display_name']}</b>"
    )
    board_kb = kb.game_board_custom_kb(game['board'], game_id, skin_x_sym, skin_o_sym)
    await call.message.edit_text(game_msg, reply_markup=board_kb, parse_mode="HTML")
    try:
        await bot.send_message(friend_id, game_msg, reply_markup=board_kb, parse_mode="HTML")
    except Exception:
        pass

# ==================== Leaderboard ====================

@router.callback_query(F.data.startswith("leaderboard_"))
async def cb_leaderboard(call: CallbackQuery):
    page = int(call.data.split("_")[1])
    per_page = 10
    users, total = db.get_all_users(page, per_page)
    total_pages = (total + per_page - 1) // per_page
    
    text = "🏆 <b>Таблица лидеров</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(users):
        global_rank = page * per_page + i + 1
        medal = medals[global_rank-1] if global_rank <= 3 else f"#{global_rank}"
        rank_name, rank_emoji = db.get_rank(u['elo'])
        badge = get_verified_badge(u['user_id'])
        text += f"{medal} {badge}<b>{u['display_name']}</b> — {rank_emoji} {u['elo']} ELO\n"
    
    await call.message.edit_text(
        text,
        reply_markup=kb.leaderboard_kb(page, total_pages),
        parse_mode="HTML"
    )

# ==================== Admin Panel ====================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа!")
        return
    await message.answer("👑 <b>Админ панель</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Нет доступа!")
        return
    await call.message.edit_text("👑 <b>Админ панель</b>", reply_markup=kb.admin_main_kb(), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_users_"))
async def cb_admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    page = int(call.data.split("_")[2])
    per_page = 10
    users, total = db.get_all_users(page, per_page)
    await call.message.edit_text(
        f"👥 <b>Игроки</b> (всего: {total})",
        reply_markup=kb.admin_users_kb(users, page, total, per_page),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_user_"))
async def cb_admin_user_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    user_id = int(call.data.split("_")[2])
    user = db.get_user(user_id)
    if not user:
        await call.answer("Игрок не найден")
        return
    rank_name, rank_emoji = db.get_rank(user['elo'])
    badge = get_verified_badge(user_id)
    text = (
        f"👤 <b>Игрок</b>\n\n"
        f"{badge}@{user['username']}\n"
        f"🆔 Game ID: <code>{user['game_id']}</code>\n"
        f"💬 Ник: {user['display_name']}\n"
        f"🏆 ELO: {user['elo']} ({rank_emoji} {rank_name})\n"
        f"💰 Монеты: {user['coins']}\n"
        f"🎮 В/П/Н: {user['wins']}/{user['losses']}/{user['draws']}\n"
        f"📅 Регистрация: {user['created_at']}"
    )
    await call.message.edit_text(text, reply_markup=kb.admin_user_detail_kb(user_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_edit_coins_"))
async def cb_admin_edit_coins(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    user_id = int(call.data.split("_")[3])
    await state.update_data(target_id=user_id)
    await call.message.edit_text(
        "💰 Введи новое количество монет:",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(AdminEditCoinsState.waiting_amount)

@router.message(AdminEditCoinsState.waiting_amount)
async def process_admin_edit_coins(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    data = await state.get_data()
    target_id = data['target_id']
    db.admin_set_coins(target_id, amount)
    user = db.get_user(target_id)
    await state.clear()
    await message.answer(
        f"✅ Монеты @{user['username']} установлены: <b>{amount}</b>",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_edit_elo_"))
async def cb_admin_edit_elo(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    user_id = int(call.data.split("_")[3])
    await state.update_data(target_id=user_id)
    await call.message.edit_text(
        "🏅 Введи новое значение ELO:",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(AdminEditEloState.waiting_elo)

@router.message(AdminEditEloState.waiting_elo)
async def process_admin_edit_elo(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        elo = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    data = await state.get_data()
    target_id = data['target_id']
    db.admin_set_elo(target_id, elo)
    user = db.get_user(target_id)
    await state.clear()
    await message.answer(
        f"✅ ELO @{user['username']} установлено: <b>{elo}</b>",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "admin_search_user")
async def cb_admin_search(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    await call.message.edit_text(
        "🔍 Введи @username для поиска:",
        reply_markup=kb.back_main_kb()
    )
    await state.set_state(AdminSearchUserState.waiting_username)

@router.message(AdminSearchUserState.waiting_username)
async def process_admin_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    username = message.text.strip().lstrip('@')
    user = db.get_user_by_username(username)
    await state.clear()
    if not user:
        await message.answer("❌ Пользователь не найден!", reply_markup=kb.admin_main_kb())
        return
    rank_name, rank_emoji = db.get_rank(user['elo'])
    badge = get_verified_badge(user['user_id'])
    text = (
        f"👤 <b>Найден игрок</b>\n\n"
        f"{badge}@{user['username']}\n"
        f"🆔 Game ID: <code>{user['game_id']}</code>\n"
        f"💬 Ник: {user['display_name']}\n"
        f"🏆 ELO: {user['elo']} ({rank_emoji} {rank_name})\n"
        f"💰 Монеты: {user['coins']}\n"
        f"🎮 В/П/Н: {user['wins']}/{user['losses']}/{user['draws']}"
    )
    await message.answer(text, reply_markup=kb.admin_user_detail_kb(user['user_id']), parse_mode="HTML")

# ==================== Admin Skins ====================

@router.callback_query(F.data.startswith("admin_skins_"))
async def cb_admin_skins(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    page = int(call.data.split("_")[2])
    per_page = 10
    skins, total = db.get_all_skins_admin(page, per_page)
    await call.message.edit_text(
        f"🎨 <b>Все скины</b> (всего: {total})",
        reply_markup=kb.admin_skins_kb(skins, page, total, per_page),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_skin_"))
async def cb_admin_skin_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    skin_id = int(call.data.split("_")[2])
    skin = db.get_skin(skin_id)
    if not skin:
        await call.answer("Скин не найден")
        return
    creator = f"@{skin['creator_username']}" if skin['creator_username'] else "Администратор"
    text = (
        f"🎨 <b>Скин #{skin['skin_id']}</b>\n\n"
        f"📛 Название: {skin['name']}\n"
        f"❌ X: {skin['symbol_x']}\n"
        f"⭕ O: {skin['symbol_o']}\n"
        f"✨ Редкость: {skin['rarity']}\n"
        f"👤 Создатель: {creator}\n"
        f"📅 Создан: {skin['created_at']}"
    )
    await call.message.edit_text(text, reply_markup=kb.admin_skin_detail_kb(skin_id), parse_mode="HTML")

@router.callback_query(F.data.startswith("admin_del_skin_"))
async def cb_admin_del_skin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    skin_id = int(call.data.split("_")[3])
    db.delete_skin_admin(skin_id)
    await call.answer("🗑️ Скин удалён!")
    await call.message.edit_text("✅ Скин удалён!", reply_markup=kb.admin_main_kb())

@router.callback_query(F.data == "admin_add_skin")
async def cb_admin_add_skin(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    await call.message.edit_text("📛 Введи название скина:", reply_markup=kb.back_main_kb())
    await state.set_state(AdminAddSkinState.waiting_name)

@router.message(AdminAddSkinState.waiting_name)
async def process_admin_skin_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text.strip())
    await message.answer("❌ Введи символ/эмодзи для X:")
    await state.set_state(AdminAddSkinState.waiting_x)

@router.message(AdminAddSkinState.waiting_x)
async def process_admin_skin_x(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(sym_x=message.text.strip())
    await message.answer("⭕ Введи символ/эмодзи для O:")
    await state.set_state(AdminAddSkinState.waiting_o)

@router.message(AdminAddSkinState.waiting_o)
async def process_admin_skin_o(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    skin_id = db.create_skin(data['name'], data['sym_x'], message.text.strip(), None)
    await state.clear()
    await message.answer(
        f"✅ <b>Скин создан администратором!</b>\n"
        f"📛 {data['name']} | ❌{data['sym_x']} ⭕{message.text.strip()}\n"
        f"🆔 ID: #{skin_id}",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ==================== Admin Give Skin ====================

@router.callback_query(F.data == "admin_give_skin")
async def cb_admin_give_skin(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    await call.message.edit_text("👤 Введи @username игрока:", reply_markup=kb.back_main_kb())
    await state.set_state(AdminGiveSkinState.waiting_username)

@router.message(AdminGiveSkinState.waiting_username)
async def process_admin_give_skin_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    username = message.text.strip().lstrip('@')
    user = db.get_user_by_username(username)
    if not user:
        await message.answer("❌ Игрок не найден!")
        return
    await state.update_data(target_id=user['user_id'])
    await message.answer(f"🆔 Введи ID скина (число):")
    await state.set_state(AdminGiveSkinState.waiting_skin_id)

@router.message(AdminGiveSkinState.waiting_skin_id)
async def process_admin_give_skin_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        skin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    skin = db.get_skin(skin_id)
    if not skin:
        await message.answer(f"❌ Скин #{skin_id} не найден!")
        return
    data = await state.get_data()
    target_id = data['target_id']
    db.give_skin(target_id, skin_id)
    target = db.get_user(target_id)
    await state.clear()
    try:
        await bot.send_message(
            target_id,
            f"🎁 Тебе выдан скин <b>{skin['name']}</b> [{skin['symbol_x']}/{skin['symbol_o']}] от администратора!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await message.answer(
        f"✅ Скин <b>{skin['name']}</b> выдан @{target['username']}!",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_give_skin_to_"))
async def cb_admin_give_skin_to(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    user_id = int(call.data.split("_")[4])
    await state.update_data(target_id=user_id)
    await call.message.edit_text("🆔 Введи ID скина:", reply_markup=kb.back_main_kb())
    await state.set_state(AdminGiveSkinToState.waiting_skin_id)

@router.message(AdminGiveSkinToState.waiting_skin_id)
async def process_admin_give_skin_to_id(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        skin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    skin = db.get_skin(skin_id)
    if not skin:
        await message.answer(f"❌ Скин #{skin_id} не найден!")
        return
    data = await state.get_data()
    target_id = data['target_id']
    db.give_skin(target_id, skin_id)
    target = db.get_user(target_id)
    await state.clear()
    try:
        await bot.send_message(
            target_id,
            f"🎁 Тебе выдан скин <b>{skin['name']}</b> [{skin['symbol_x']}/{skin['symbol_o']}] от администратора!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await message.answer(
        f"✅ Скин выдан @{target['username']}!",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ==================== Admin Give Coins ====================

@router.callback_query(F.data == "admin_give_coins")
async def cb_admin_give_coins(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    await call.message.edit_text("👤 Введи @username:", reply_markup=kb.back_main_kb())
    await state.set_state(AdminGiveCoinsState.waiting_username)

@router.message(AdminGiveCoinsState.waiting_username)
async def process_admin_coins_user(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    username = message.text.strip().lstrip('@')
    user = db.get_user_by_username(username)
    if not user:
        await message.answer("❌ Не найден!")
        return
    await state.update_data(target_id=user['user_id'])
    await message.answer(f"💰 Сколько монет выдать @{username}?")
    await state.set_state(AdminGiveCoinsState.waiting_amount)

@router.message(AdminGiveCoinsState.waiting_amount)
async def process_admin_coins_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    data = await state.get_data()
    target_id = data['target_id']
    db.add_coins(target_id, amount, "Выдача администратором")
    target = db.get_user(target_id)
    await state.clear()
    try:
        await bot.send_message(
            target_id,
            f"💰 Тебе выдано <b>{amount}</b> монет администратором!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await message.answer(
        f"✅ @{target['username']} выдано {amount} монет!",
        reply_markup=kb.admin_main_kb()
    )

# ==================== Admin Games ====================

@router.callback_query(F.data.startswith("admin_games_"))
async def cb_admin_games(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    page = int(call.data.split("_")[2])
    per_page = 10
    games, total = db.get_all_games_admin(page, per_page)
    await call.message.edit_text(
        f"🎮 <b>Все игры</b> (всего: {total})",
        reply_markup=kb.admin_games_kb(games, page, total, per_page),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_game_"))
async def cb_admin_game_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    game_id = int(call.data.split("_")[2])
    game = db.get_game(game_id)
    if not game:
        await call.answer("Игра не найдена")
        return
    p1 = db.get_user(game['player1_id'])
    p2 = db.get_user(game['player2_id'])
    board_text = format_board(game['board'], game['skin_x'], game['skin_o'])
    p1_name = f"@{p1['username']}" if p1 else f"#{game['player1_id']}"
    p2_name = f"@{p2['username']}" if p2 else f"#{game['player2_id']}"
    status_map = {"active": "🟢 Активна", "finished": "🔴 Завершена", "cancelled": "⛔ Отменена"}
    text = (
        f"🎮 <b>Игра #{game_id}</b>\n\n"
        f"👤 {p1_name} vs {p2_name}\n"
        f"📊 Статус: {status_map.get(game['status'], game['status'])}\n"
        f"🗓️ Создана: {game['created_at']}\n\n"
        f"{board_text}"
    )
    if game['admin_cancelled']:
        text += "\n⚠️ Отменена администратором (ELO не снималось)"
    await call.message.edit_text(
        text,
        reply_markup=kb.admin_game_detail_kb(game_id, game['status']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("admin_cancel_game_"))
async def cb_admin_cancel_game(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    game_id = int(call.data.split("_")[3])
    game = db.get_game(game_id)
    if not game or game['status'] != 'active':
        await call.answer("Игра не активна!")
        return
    db.admin_cancel_game(game_id)
    p1 = db.get_user(game['player1_id'])
    p2 = db.get_user(game['player2_id'])
    cancel_msg = "⛔ <b>Игра отменена администратором.</b>\nELO не изменилось."
    try:
        await bot.send_message(game['player1_id'], cancel_msg, parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(game['player2_id'], cancel_msg, parse_mode="HTML")
    except Exception:
        pass
    await call.answer("✅ Игра отменена без снятия ELO!")
    await call.message.edit_text(
        f"✅ Игра #{game_id} отменена.\nELO игроков не изменилось.",
        reply_markup=kb.admin_main_kb()
    )

# ==================== Admin Create Case ====================

@router.callback_query(F.data == "admin_create_case")
async def cb_admin_create_case(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("❌")
        return
    await call.message.edit_text("📦 Введи название кейса:", reply_markup=kb.back_main_kb())
    await state.set_state(AdminCreateCaseState.waiting_name)

@router.message(AdminCreateCaseState.waiting_name)
async def process_case_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(case_name=message.text.strip())
    await message.answer("💰 Введи стоимость открытия кейса:")
    await state.set_state(AdminCreateCaseState.waiting_cost)

@router.message(AdminCreateCaseState.waiting_cost)
async def process_case_cost(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        cost = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи число!")
        return
    await state.update_data(case_cost=cost)
    await message.answer("🎨 Введи ID скинов через запятую (пример: 1,2,3):")
    await state.set_state(AdminCreateCaseState.waiting_skin_ids)

@router.message(AdminCreateCaseState.waiting_skin_ids)
async def process_case_skins(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    try:
        skin_ids = [int(x.strip()) for x in message.text.strip().split(',')]
    except ValueError:
        await message.answer("❌ Некорректный формат!")
        return
    
    valid_ids = []
    for sid in skin_ids:
        if db.get_skin(sid):
            valid_ids.append(sid)
    
    if not valid_ids:
        await message.answer("❌ Ни один скин не найден!")
        return
    
    data = await state.get_data()
    case_id = db.create_case_db(data['case_name'], data['case_cost'], valid_ids)
    await state.clear()
    await message.answer(
        f"✅ <b>Кейс создан!</b>\n"
        f"📦 {data['case_name']}\n"
        f"💰 Стоимость: {data['case_cost']}\n"
        f"🎨 Скинов: {len(valid_ids)}\n"
        f"🆔 ID кейса: #{case_id}",
        reply_markup=kb.admin_main_kb(),
        parse_mode="HTML"
    )

# ==================== Noop ====================

@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()

# ==================== Main ====================

async def main():
    db.init_db()
    logging.info("База данных инициализирована")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())