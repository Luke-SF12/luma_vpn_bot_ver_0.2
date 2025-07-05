from aiogram.fsm.state import State, StatesGroup

class AddKeyState(StatesGroup):
    waiting_for_name_and_key = State()  # Состояние ожидания ввода имени и ключа

class AddAdminState(StatesGroup):
    waiting_for_admin_id = State()  # Состояние ожидания ввода Telegram ID администратора

class BroadcastState(StatesGroup):
    waiting_for_broadcast_message = State()
    confirmation = State()