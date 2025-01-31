from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    waiting_for_email = State()  # Состояние ожидания email