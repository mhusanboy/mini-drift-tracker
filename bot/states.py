from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    phone = State()


class Booking(StatesGroup):
    day = State()
    time = State()
    people = State()
    confirm = State()


class EditService(StatesGroup):
    name = State()
    address = State()
    open_hour = State()
    close_hour = State()
    location = State()
