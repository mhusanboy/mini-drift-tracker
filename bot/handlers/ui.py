"""Shared UI helper for editing the current screen in place.

Inline-button (callback) handlers should update the message the button is
attached to instead of sending a new one, so navigation replaces the screen
rather than stacking messages. Typed input and slash commands still send a new
message (the new keyboard must appear at the bottom, and there is no prior
inline message to edit).
"""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup


async def edit_screen(
    cb: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> None:
    if cb.message is None:
        return
    try:
        await cb.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        # Re-tapping a button that yields the same screen is a no-op, not an error.
        if "message is not modified" in str(exc).lower():
            return
        # Message too old / not editable -> fall back to a fresh message.
        await cb.message.answer(text, reply_markup=reply_markup)
