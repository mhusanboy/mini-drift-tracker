from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import get_settings
from bot.db.models import User
from bot.handlers import ui
from bot.keyboards.common import language_kb, main_menu_kb, phone_kb
from bot.locales import t
from bot.states import Registration

router = Router()


async def show_main_menu(message: Message, user_id: int, lang: str) -> None:
    is_admin = get_settings().is_admin(user_id)
    await ui.show_screen(message, t("main_menu_title", lang), main_menu_kb(lang, is_admin))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User | None):
    await state.clear()
    await ui.drop(message)
    if user is not None:
        await show_main_menu(message, message.from_user.id, user.language)
        return
    await ui.show_screen(message, t("choose_language", "ru"), language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def pick_language(cb: CallbackQuery, state: FSMContext, user: User | None, session_factory):
    lang = cb.data.split(":", 1)[1]
    if user is not None:
        # Language change from the menu: persist and edit back to the main menu.
        async with session_factory() as session:
            db_user = await session.get(User, user.telegram_id)
            db_user.language = lang
            await session.commit()
        is_admin = get_settings().is_admin(cb.from_user.id)
        await ui.edit_screen(cb, t("main_menu_title", lang), main_menu_kb(lang, is_admin))
        await cb.answer()
        return
    await state.update_data(language=lang)
    await state.set_state(Registration.full_name)
    await ui.edit_screen(cb, t("ask_full_name", lang))
    await cb.answer()


@router.message(Registration.full_name, F.text)
async def reg_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.phone)
    await ui.replace_screen(message, t("ask_phone", lang), phone_kb(lang))


@router.message(Registration.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext, session_factory):
    data = await state.get_data()
    lang, name = data["language"], data["full_name"]
    async with session_factory() as session:
        session.add(User(
            telegram_id=message.from_user.id,
            full_name=name,
            phone=message.contact.phone_number,
            language=lang,
        ))
        await session.commit()
    await state.clear()
    await ui.drop(message)
    await ui.purge(message.bot, message.chat.id)
    # Only a message carrying ReplyKeyboardRemove dismisses the phone keyboard,
    # so the welcome carries it and is then edited into the menu — one message
    # instead of a greeting left stranded above.
    welcome = ui.own(await message.answer(
        t("registered", lang, name=name), reply_markup=ReplyKeyboardRemove()
    ))
    is_admin = get_settings().is_admin(message.from_user.id)
    await welcome.edit_text(
        t("registered", lang, name=name) + "\n\n" + t("main_menu_title", lang),
        reply_markup=main_menu_kb(lang, is_admin),
    )


@router.message(Registration.phone)
async def reg_phone_wrong(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    await ui.replace_screen(message, t("phone_use_button", lang), phone_kb(lang))


@router.callback_query(F.data == "menu:language")
async def menu_language(cb: CallbackQuery, lang: str):
    await ui.edit_screen(cb, t("choose_language", lang), language_kb(lang, back="back:main"))
    await cb.answer()


@router.callback_query(F.data == "back:main")
async def back_to_main(cb: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    is_admin = get_settings().is_admin(cb.from_user.id)
    await ui.edit_screen(cb, t("main_menu_title", lang), main_menu_kb(lang, is_admin))
    await cb.answer()
