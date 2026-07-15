from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.config import get_settings
from bot.db.models import User
from bot.keyboards.common import language_kb, main_menu_kb, phone_kb
from bot.locales import t
from bot.services import slots
from bot.states import Registration

router = Router()


async def send_service_location(message: Message, service, lang: str) -> None:
    """Show where the service is: a Telegram venue pin if we have coordinates,
    otherwise the saved map link."""
    if service.latitude is not None and service.longitude is not None:
        await message.answer_venue(
            latitude=service.latitude, longitude=service.longitude,
            title=service.name, address=service.address,
        )
    elif service.location_url:
        await message.answer(t("service_location_link", lang, name=service.name,
                              address=service.address, url=service.location_url))


async def show_main_menu(message: Message, user_id: int, lang: str, session_factory) -> None:
    async with session_factory() as session:
        service = await slots.get_service(session)
    if service is not None:
        await send_service_location(message, service, lang)
    is_admin = get_settings().is_admin(user_id)
    await message.answer(t("main_menu_title", lang), reply_markup=main_menu_kb(lang, is_admin))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User | None, session_factory):
    await state.clear()
    if user is not None:
        await show_main_menu(message, message.from_user.id, user.language, session_factory)
        return
    await message.answer(t("choose_language", "ru"), reply_markup=language_kb())


@router.callback_query(F.data.startswith("lang:"))
async def pick_language(cb: CallbackQuery, state: FSMContext, user: User | None,
                        session_factory):
    lang = cb.data.split(":", 1)[1]
    if user is not None:
        # Language change from menu: persist immediately.
        async with session_factory() as session:
            db_user = await session.get(User, user.telegram_id)
            db_user.language = lang
            await session.commit()
        await show_main_menu(cb.message, cb.from_user.id, lang, session_factory)
        await cb.answer()
        return
    await state.update_data(language=lang)
    await state.set_state(Registration.full_name)
    await cb.message.answer(t("ask_full_name", lang))
    await cb.answer()


@router.message(Registration.full_name, F.text)
async def reg_full_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data["language"]
    await state.update_data(full_name=message.text.strip())
    await state.set_state(Registration.phone)
    await message.answer(t("ask_phone", lang), reply_markup=phone_kb(lang))


@router.message(Registration.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext, session_factory):
    data = await state.get_data()
    lang = data["language"]
    async with session_factory() as session:
        session.add(User(
            telegram_id=message.from_user.id,
            full_name=data["full_name"],
            phone=message.contact.phone_number,
            language=lang,
        ))
        await session.commit()
    await state.clear()
    await message.answer(t("registered", lang, name=data["full_name"]),
                         reply_markup=ReplyKeyboardRemove())
    await show_main_menu(message, message.from_user.id, lang, session_factory)


@router.message(Registration.phone)
async def reg_phone_wrong(message: Message, state: FSMContext):
    data = await state.get_data()
    await message.answer(t("phone_use_button", data["language"]),
                         reply_markup=phone_kb(data["language"]))


@router.callback_query(F.data == "menu:language")
async def menu_language(cb: CallbackQuery):
    await cb.message.answer(t("choose_language", "ru"), reply_markup=language_kb())
    await cb.answer()
