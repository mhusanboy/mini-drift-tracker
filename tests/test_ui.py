import pytest
from aiogram.exceptions import TelegramBadRequest

from bot.handlers import ui

CHAT = 42


class _Chat:
    def __init__(self, chat_id):
        self.id = chat_id


class FakeMessage:
    def __init__(self, bot, chat_id, message_id, text=None):
        self.bot = bot
        self.chat = _Chat(chat_id)
        self.message_id = message_id
        self.text = text

    async def answer(self, text, reply_markup=None):
        return self.bot.new_message(self.chat.id, text)

    async def edit_text(self, text, reply_markup=None):
        if text == self.text:
            raise TelegramBadRequest(method=None, message="message is not modified")
        self.bot.edited.append((self.message_id, text))
        self.text = text
        return self


class FakeBot:
    """Records what the handlers would have asked Telegram to do."""

    def __init__(self):
        self.deleted, self.edited = [], []
        self.undeletable = set()
        self._next_id = 0

    def new_message(self, chat_id, text=None):
        self._next_id += 1
        return FakeMessage(self, chat_id, self._next_id, text)

    async def delete_message(self, chat_id, message_id):
        if message_id in self.undeletable:
            raise TelegramBadRequest(method=None, message="message can't be deleted")
        self.deleted.append(message_id)


class FakeCallback:
    def __init__(self, bot, message):
        self.bot, self.message = bot, message


@pytest.fixture(autouse=True)
def _clean_registry():
    ui._live.clear()
    yield
    ui._live.clear()


async def test_show_screen_clears_the_previous_screen():
    bot = FakeBot()
    root = bot.new_message(CHAT)
    first = await ui.show_screen(root, "one")
    second = await ui.show_screen(root, "two")
    assert bot.deleted == [first.message_id]
    assert ui._live[CHAT] == [second.message_id]


async def test_replace_screen_drops_the_users_message_and_the_prompt_above_it():
    bot = FakeBot()
    root = bot.new_message(CHAT)
    prompt = await ui.show_screen(root, "which day and time?")
    typed = bot.new_message(CHAT, "ertaga 18:00")  # what the user sent
    answer = await ui.replace_screen(typed, "here is your link")
    assert typed.message_id in bot.deleted
    assert prompt.message_id in bot.deleted
    # Only the new message is left on screen.
    assert ui._live[CHAT] == [answer.message_id]


async def test_messages_sent_alongside_the_screen_are_cleared_with_it():
    bot = FakeBot()
    root = bot.new_message(CHAT)
    pin = ui.own(bot.new_message(CHAT, "venue"))
    promo = ui.own(bot.new_message(CHAT, "photo"))
    menu = await ui.send(root, "menu")  # send() adds, it does not clear
    assert ui._live[CHAT] == [pin.message_id, promo.message_id, menu.message_id]

    await ui.show_screen(root, "prices")
    assert sorted(bot.deleted) == sorted([pin.message_id, promo.message_id, menu.message_id])


async def test_edit_screen_clears_extras_but_keeps_the_message_it_edits():
    bot = FakeBot()
    root = bot.new_message(CHAT)
    pin = ui.own(bot.new_message(CHAT, "venue"))
    menu = await ui.send(root, "menu")

    await ui.edit_screen(FakeCallback(bot, menu), "prices")
    assert bot.deleted == [pin.message_id]
    assert bot.edited == [(menu.message_id, "prices")]
    assert ui._live[CHAT] == [menu.message_id]


async def test_edit_screen_adopts_an_untracked_message():
    # After a restart the live screen is unknown; editing it must re-track it.
    bot = FakeBot()
    stray = bot.new_message(CHAT, "old menu")
    await ui.edit_screen(FakeCallback(bot, stray), "prices")
    assert ui._live[CHAT] == [stray.message_id]


async def test_edit_screen_tolerates_an_unchanged_screen():
    bot = FakeBot()
    menu = bot.new_message(CHAT, "menu")
    await ui.edit_screen(FakeCallback(bot, menu), "menu")  # must not raise
    assert bot.edited == []


async def test_purge_can_spare_one_message():
    bot = FakeBot()
    a = ui.own(bot.new_message(CHAT))
    b = ui.own(bot.new_message(CHAT))
    await ui.purge(bot, CHAT, keep=b.message_id)
    assert bot.deleted == [a.message_id]
    assert ui._live[CHAT] == [b.message_id]


async def test_undeletable_messages_do_not_break_navigation():
    # Telegram refuses to delete anything older than 48h — that must not stop
    # the next screen from being shown.
    bot = FakeBot()
    root = bot.new_message(CHAT)
    first = await ui.show_screen(root, "one")
    bot.undeletable.add(first.message_id)
    second = await ui.show_screen(root, "two")
    assert ui._live[CHAT] == [second.message_id]


async def test_chats_do_not_clear_each_others_screens():
    bot = FakeBot()
    a_root, b_root = bot.new_message(1), bot.new_message(2)
    a = await ui.show_screen(a_root, "chat one")
    await ui.show_screen(b_root, "chat two")
    assert a.message_id not in bot.deleted
    assert ui._live[1] == [a.message_id]
