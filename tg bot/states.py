from aiogram.fsm.state import State, StatesGroup


class FindMovie(StatesGroup):
    waiting_code = State()


class AdminAddMovie(StatesGroup):
    code = State()
    title = State()
    description = State()
    link = State()


class AdminEditMovie(StatesGroup):
    title = State()
    description = State()
    link = State()


class AdminAddSub(StatesGroup):
    link = State()
    duration = State()


class AdminPost(StatesGroup):
    waiting_content = State()
    confirm = State()
