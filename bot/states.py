from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    full_name = State()
    phone = State()


class BookingRequest(StatesGroup):
    when = State()
    people = State()


class EditPrice(StatesGroup):
    text = State()


class EditHours(StatesGroup):
    open_at = State()
    close_at = State()


class EditLocation(StatesGroup):
    value = State()


class EditUsername(StatesGroup):
    value = State()


class AddPromo(StatesGroup):
    text = State()
    media = State()


class EditCard(StatesGroup):
    """Editing a booking request from its notification card."""

    time = State()
    duration = State()
    people = State()
