"""Keeping the chat down to a single live screen.

The bot remembers every message it currently has on screen in a chat. Inline
buttons edit the message they sit on, so navigation replaces the screen in
place. Typed input cannot do that — the reply has to be a new message at the
bottom — so the prompt above it and the user's own message are deleted first,
and the conversation continues in the new message.

The registry is in-memory, like the FSM: a restart leaves one stale screen
behind that later navigation no longer knows to clean up. Deletes are always
best-effort — Telegram refuses them on messages older than 48 hours.
"""
import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

# chat_id -> ids of the bot messages currently on screen: the screen itself plus
# anything sent alongside it (a map pin, the aksiya photos).
_live: dict[int, list[int]] = {}


def _own(chat_id: int, message_id: int) -> None:
    ids = _live.setdefault(chat_id, [])
    if message_id not in ids:
        ids.append(message_id)


async def _delete(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramAPIError as exc:
        # Already gone, too old to delete, or the user blocked the bot.
        logger.debug("Could not delete %s in %s: %s", message_id, chat_id, exc)


def own(sent: Message) -> Message:
    """Count an already-sent message as part of the current screen, so the next
    navigation clears it too."""
    _own(sent.chat.id, sent.message_id)
    return sent


async def drop(message: Message) -> None:
    """Delete a message the user sent — it is not part of the screen."""
    await _delete(message.bot, message.chat.id, message.message_id)


async def purge(bot, chat_id: int, keep: int | None = None) -> None:
    """Delete everything the bot has on screen, optionally sparing one message."""
    kept = []
    for message_id in _live.pop(chat_id, []):
        if message_id == keep:
            kept.append(message_id)
        else:
            await _delete(bot, chat_id, message_id)
    if kept:
        _live[chat_id] = kept


async def send(message: Message, text: str, reply_markup=None) -> Message:
    """Add a message to the current screen without clearing what's there."""
    return own(await message.answer(text, reply_markup=reply_markup))


async def show_screen(message: Message, text: str, reply_markup=None) -> Message:
    """Clear the chat and put a new live screen at the bottom."""
    await purge(message.bot, message.chat.id)
    return await send(message, text, reply_markup)


async def replace_screen(message: Message, text: str, reply_markup=None) -> Message:
    """Answer typed input: drop the user's message and the prompt above it, then
    continue in a new screen at the bottom."""
    await drop(message)
    return await show_screen(message, text, reply_markup)


async def edit_message(bot, chat_id: int, message_id: int, text: str, reply_markup=None) -> None:
    """Rewrite a known message by id — used to put a card back together after
    the admin has typed an answer somewhere below it."""
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup,
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        logger.warning("Could not update message %s in %s: %s", message_id, chat_id, exc)


async def edit_card(cb: CallbackQuery, text: str, reply_markup=None) -> None:
    """Rewrite a standalone message — a booking request card — without making it
    the live screen. Cards are records the admin keeps; navigation elsewhere
    must never sweep them away, and they must never sweep away a screen."""
    if cb.message is None:
        return
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        logger.warning("Could not update card %s: %s", cb.message.message_id, exc)


async def edit_screen(cb: CallbackQuery, text: str, reply_markup=None) -> None:
    """Navigate by rewriting the message the button sits on."""
    if cb.message is None:
        return
    # Anything sent alongside this screen (pins, promos) is now stale.
    await purge(cb.bot, cb.message.chat.id, keep=cb.message.message_id)
    _own(cb.message.chat.id, cb.message.message_id)
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        # Re-tapping a button that yields the same screen is a no-op, not an error.
        if "message is not modified" in str(exc).lower():
            return
        # Message too old / not editable -> fall back to a fresh screen.
        await show_screen(cb.message, text, reply_markup)
