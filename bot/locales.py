LANGUAGES = {"ru": "Русский", "uz": "O'zbekcha"}

_STRINGS = {
    "ru": {
        # registration
        "choose_language": "Выберите язык:",
        "ask_full_name": "Введите ваше полное имя (например, Анвар Анваров):",
        "ask_phone": "Поделитесь номером телефона, нажав кнопку ниже.",
        "share_phone_button": "📱 Поделиться номером",
        "phone_use_button": "Пожалуйста, используйте кнопку ниже, чтобы поделиться номером.",
        "registered": "Готово! Добро пожаловать, {name}.",
        # main menu
        "main_menu_title": "Чтобы не ждать по приезде, рекомендуем забронировать заранее 🏁",
        "btn_location": "📍 Локация",
        "btn_prices": "💰 Цены",
        "btn_promos": "🎁 Акции",
        "btn_book": "✍️ Забронировать",
        "btn_language": "🌐 Язык",
        "btn_admin": "🔧 Админ-панель",
        "back": "⬅️ Назад",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        # location
        "location_not_set": "Локация пока не добавлена. Загляните позже.",
        "location_link": "📍 Мы находимся здесь:\n{url}",
        # prices
        "prices_not_set": "Цены пока не добавлены. Загляните позже.",
        # promos
        "promos_empty": "Сейчас акций нет. Загляните позже 🙂",
        "promos_title": "🎁 Наши акции:",
        # booking request
        "booking_unavailable": "Бронирование сейчас недоступно. Загляните позже.",
        "ask_booking_when": (
            "На какой день и время хотите забронировать?\n\n"
            "Напишите одним сообщением — например: «завтра в 18:00» или «25 июля, 19:30»."
        ),
        "booking_when_too_long": "Слишком длинно. Напишите короче — только день и время.",
        "ask_booking_people": "Сколько человек придёт? Введите число:",
        "people_invalid": "Введите положительное целое число (например, 5).",
        "booking_link_intro": (
            "Готово! Нажмите кнопку — откроется чат с админом, сообщение уже набрано.\n"
            "Осталось только отправить его 👇\n\n{message}"
        ),
        "btn_open_dm": "✍️ Отправить админу",
        # Written by the customer, read by the admin — so it follows the
        # customer's language, not the admin's.
        "booking_dm_template": (
            "Здравствуйте! Меня зовут {name}.\n"
            "Хотел(а) бы забронировать место на {when} — есть свободное время?\n"
            "Нас будет {people} чел.\n\n"
            "Контакт: {phone}"
        ),
        # admin panel
        "not_authorized": "Эта команда только для админов.",
        "admin_panel_title": "🔧 Админ-панель",
        "btn_admin_settings": "⚙️ Настройки",
        "btn_admin_free": "🕐 Свободное время",
        "btn_admin_stats": "📊 Статистика",
        "btn_admin_history": "📗 История броней (Excel)",
        "btn_admin_users": "👥 Пользователи",
        # request card
        "card": (
            "🆕 Заявка на бронь — {status}\n\n"
            "Клиент: {name}\n"
            "Телефон: {phone}\n"
            "Время: {when}\n"
            "Человек: {people}\n"
            "Ожидаемая длительность: {hours} ч\n\n"
            "Бронь принята?"
        ),
        "card_when": "{date} {time}–{end}  («{text}»)",
        "card_when_unknown": "⚠️ не распознано («{text}») — задайте вручную",
        "status_pending": "⏳ ожидает",
        "status_accepted": "✅ принята",
        "status_rejected": "❌ отклонена",
        "btn_card_accept": "✅ Принять",
        "btn_card_reject": "❌ Отклонить",
        "btn_card_edit": "✏️ Изменить данные",
        "btn_card_edit_time": "⏰ Изменить время",
        "btn_card_edit_duration": "⏳ Изменить длительность",
        "btn_card_edit_people": "👥 Изменить кол-во человек",
        "card_edit_title": "✏️ Что изменить?",
        "card_ask_time": "Напишите новое время — например «завтра 18:00» или «25.07 19:30»:",
        "card_time_invalid": "Не понял время. Пример: «завтра 18:00» или «25.07 19:30».",
        "card_ask_duration": "Сколько часов? Введите число от 1 до 12:",
        "card_duration_invalid": "Введите целое число часов от 1 до 12.",
        "card_ask_people": "Сколько человек? Введите число:",
        "card_no_time": "Сначала задайте время: ✏️ Изменить данные → ⏰ Изменить время.",
        "card_conflict": (
            "⚠️ Это время уже занято:\n{rows}\n\nВсё равно принять?"
        ),
        "card_conflict_row": "{start}–{end} · {name} ({people} чел.)",
        "btn_conflict_yes": "⚠️ Всё равно принять",
        "card_accepted_toast": "Бронь принята.",
        "card_rejected_toast": "Бронь отклонена.",
        "card_gone": "Заявка не найдена.",
        # free times
        "free_title": "🕐 Свободное время",
        "free_hint": "Занятое время помечено ❌ — нажмите на него, чтобы увидеть бронь.",
        "free_hours_not_set": "Сначала укажите рабочее время в ⚙️ Настройках.",
        "free_day": "📅 {day}, {date}",
        "free_slot_free_toast": "Свободно",
        "free_slot_detail": "{time}–{end}\n{name} · {people} чел.",
        # stats
        "stats_overview": (
            "📊 Статистика\n\n"
            "Пользователей: {users}\n"
            "Заявок всего: {requests}\n"
            "   ✅ принято: {accepted}\n"
            "   ❌ отклонено: {rejected}\n"
            "   ⏳ ожидает: {pending}\n"
            "Принято на сегодня: {today}\n"
            "Всего человек: {people}\n"
            "Всего часов: {hours}"
        ),
        # settings
        "settings_title": (
            "⚙️ Настройки\n\n"
            "💰 Цены: {price}\n"
            "🕐 Рабочее время: {hours}\n"
            "📍 Локация: {location}\n"
            "🎁 Акций: {promos}\n"
            "✍️ Приём броней: {username}"
        ),
        "value_set": "заполнено ✅",
        "value_not_set": "не заполнено ❌",
        "btn_edit_price": "💰 Изменить цены",
        "btn_edit_hours": "🕐 Рабочее время",
        "btn_edit_location": "📍 Изменить локацию",
        "btn_edit_promos": "🎁 Акции",
        "btn_edit_username": "✍️ Приём броней",
        "ask_price": (
            "Отправьте прайс одним сообщением — как есть, так его и увидят клиенты.\n\n"
            "Текущий:\n{current}"
        ),
        "price_saved": "Цены сохранены.",
        "ask_open_hour": "Время открытия (например: 11, 11:00 или 11:30):",
        "ask_close_hour": "Время закрытия (например: 22 или 22:30):",
        "hour_invalid": "Введите время в виде 11, 11:00 или 11:30.",
        "hours_saved": "Рабочее время сохранено.",
        "ask_location": (
            "Отправьте локацию: геопозиция Telegram (📎 → Локация) "
            "или ссылка на Яндекс/Google Карты."
        ),
        "location_invalid": "Пришлите геопозицию Telegram или ссылку на карту (http…).",
        "location_saved": "Локация сохранена.",
        "ask_username": (
            "Кому писать за бронью? Пришлите username аккаунта — например "
            "@minidriftuz или https://t.me/minidriftuz.\n\nТекущий: {current}"
        ),
        "username_invalid": "Не похоже на username. Пример: @minidriftuz",
        "username_saved": "Сохранено: @{username}",
        "promos_admin_title": "🎁 Акции ({count})\n\nНажмите на акцию, чтобы удалить её.",
        "btn_add_promo": "➕ Добавить акцию",
        "btn_del_promo": "🗑 {text}",
        "ask_promo_text": "Опишите акцию одним сообщением:",
        "ask_promo_media": "Пришлите фото или видео к акции.\nЕсли не нужно — отправьте «-».",
        "promo_media_invalid": "Пришлите фото, видео или «-», чтобы пропустить.",
        "promo_saved": "Акция добавлена.",
        "promo_deleted": "Акция удалена.",
        # users
        "users_header": "👥 Пользователи: {total} (стр. {page}/{pages})",
        "users_empty": "Пока нет зарегистрированных пользователей.",
        "user_card": "{name}\n{phone} · {language} · с {joined}",
        # excel
        "xls_caption": "📗 История броней на {date}",
        "xls_sheet_overview": "Общее",
        "xls_sheet_customers": "Клиенты",
        "xls_sheet_bookings": "Брони",
        "xls_title": "Статистика на {date}",
        "xls_metric_users": "Пользователи",
        "xls_metric_requests": "Заявки (всего)",
        "xls_metric_accepted": "Принято",
        "xls_metric_rejected": "Отклонено",
        "xls_metric_pending": "Ожидает",
        "xls_metric_today": "Принято на сегодня",
        "xls_metric_people": "Всего человек",
        "xls_metric_hours": "Всего часов",
        "xls_h_name": "Имя",
        "xls_h_phone": "Телефон",
        "xls_h_language": "Язык",
        "xls_h_requests": "Заявки",
        "xls_h_accepted": "Принято",
        "xls_h_people": "Человек",
        "xls_h_hours": "Часы",
        "xls_h_first": "Первый раз",
        "xls_h_last": "Последняя бронь",
        "xls_h_date": "Дата",
        "xls_h_when": "Время",
        "xls_h_requested": "Запрос клиента",
        "xls_h_status": "Статус",
        "xls_h_customer": "Клиент",
        "xls_h_created": "Создано",
    },
    "uz": {
        # registration
        "choose_language": "Tilni tanlang:",
        "ask_full_name": "To'liq ismingizni kiriting (masalan, Anvar Anvarov):",
        "ask_phone": "Quyidagi tugma orqali telefon raqamingizni yuboring.",
        "share_phone_button": "📱 Raqamni yuborish",
        "phone_use_button": "Iltimos, raqamni yuborish uchun pastdagi tugmadan foydalaning.",
        "registered": "Tayyor! Xush kelibsiz, {name}.",
        # main menu
        "main_menu_title": (
            "Kelganingizda kutib qolmaslik uchun, oldindan bron qilib "
            "qo'yishni tavsiya etamiz 🏁"
        ),
        "btn_location": "📍 Lokatsiya",
        "btn_prices": "💰 Narxlar",
        "btn_promos": "🎁 Aksiyalar",
        "btn_book": "✍️ Bron qilish",
        "btn_language": "🌐 Til",
        "btn_admin": "🔧 Admin panel",
        "back": "⬅️ Orqaga",
        "today": "Bugun",
        "tomorrow": "Ertaga",
        # location
        "location_not_set": "Lokatsiya hali qo'shilmagan. Keyinroq qarang.",
        "location_link": "📍 Biz shu yerdamiz:\n{url}",
        # prices
        "prices_not_set": "Narxlar hali qo'shilmagan. Keyinroq qarang.",
        # promos
        "promos_empty": "Hozircha aksiyalar yo'q. Keyinroq qarang 🙂",
        "promos_title": "🎁 Bizning aksiyalar:",
        # booking request
        "booking_unavailable": "Hozircha bron qilish mumkin emas. Keyinroq qarang.",
        "ask_booking_when": (
            "Qaysi kun va soatga bron qilmoqchisiz?\n\n"
            "Bitta xabarda yozing — masalan: «ertaga soat 18:00» yoki «25-iyul, 19:30»."
        ),
        "booking_when_too_long": "Juda uzun. Qisqaroq yozing — faqat kun va vaqt.",
        "ask_booking_people": "Necha kishi keladi? Sonini kiriting:",
        "people_invalid": "Musbat butun son kiriting (masalan, 5).",
        "booking_link_intro": (
            "Tayyor! Tugmani bosing — admin bilan chat ochiladi, xabar allaqachon yozilgan.\n"
            "Faqat yuborish qoldi 👇\n\n{message}"
        ),
        "btn_open_dm": "✍️ Adminga yuborish",
        "booking_dm_template": (
            "Assalomu alaykum! Ismim {name}.\n"
            "{when} ga joy bron qilmoqchi edim, vaqti bormi?\n"
            "Biz {people} kishimiz.\n\n"
            "Kontakt: {phone}"
        ),
        # admin panel
        "not_authorized": "Bu buyruq faqat adminlar uchun.",
        "admin_panel_title": "🔧 Administrator paneli",
        "btn_admin_settings": "⚙️ Sozlamalar",
        "btn_admin_free": "🕐 Bo'sh vaqtlarni ko'rish",
        "btn_admin_stats": "📊 Statistika",
        "btn_admin_history": "📗 Bronlar tarixi (Excel)",
        "btn_admin_users": "👥 Foydalanuvchilar",
        # request card
        "card": (
            "🆕 Bron so'rovi — {status}\n\n"
            "Mijoz: {name}\n"
            "Telefon: {phone}\n"
            "Vaqt: {when}\n"
            "Kishi: {people}\n"
            "Taxminiy davomiylik: {hours} soat\n\n"
            "Bron qabul qilindimi?"
        ),
        "card_when": "{date} {time}–{end}  («{text}»)",
        "card_when_unknown": "⚠️ aniqlanmadi («{text}») — qo'lda kiriting",
        "status_pending": "⏳ kutilmoqda",
        "status_accepted": "✅ qabul qilindi",
        "status_rejected": "❌ rad etildi",
        "btn_card_accept": "✅ Qabul qilish",
        "btn_card_reject": "❌ Rad etish",
        "btn_card_edit": "✏️ Ma'lumotlarni tahrirlash",
        "btn_card_edit_time": "⏰ Vaqtni tahrirlash",
        "btn_card_edit_duration": "⏳ Davomiylikni tahrirlash",
        "btn_card_edit_people": "👥 Kishi sonini tahrirlash",
        "card_edit_title": "✏️ Nimani o'zgartiramiz?",
        "card_ask_time": "Yangi vaqtni yozing — masalan «ertaga 18:00» yoki «25.07 19:30»:",
        "card_time_invalid": "Vaqtni tushunmadim. Masalan: «ertaga 18:00» yoki «25.07 19:30».",
        "card_ask_duration": "Necha soat? 1 dan 12 gacha son kiriting:",
        "card_duration_invalid": "1 dan 12 gacha butun son kiriting.",
        "card_ask_people": "Necha kishi? Sonini kiriting:",
        "card_no_time": "Avval vaqtni kiriting: ✏️ Ma'lumotlarni tahrirlash → ⏰ Vaqtni tahrirlash.",
        "card_conflict": "⚠️ Bu vaqt allaqachon band:\n{rows}\n\nBaribir qabul qilinsinmi?",
        "card_conflict_row": "{start}–{end} · {name} ({people} kishi)",
        "btn_conflict_yes": "⚠️ Baribir qabul qilish",
        "card_accepted_toast": "Bron qabul qilindi.",
        "card_rejected_toast": "Bron rad etildi.",
        "card_gone": "So'rov topilmadi.",
        # free times
        "free_title": "🕐 Bo'sh vaqtlar",
        "free_hint": "Band vaqt ❌ bilan belgilangan — bronni ko'rish uchun bosing.",
        "free_hours_not_set": "Avval ⚙️ Sozlamalarda ish vaqtini kiriting.",
        "free_day": "📅 {day}, {date}",
        "free_slot_free_toast": "Bo'sh",
        "free_slot_detail": "{time}–{end}\n{name} · {people} kishi",
        # stats
        "stats_overview": (
            "📊 Statistika\n\n"
            "Foydalanuvchilar: {users}\n"
            "Jami so'rovlar: {requests}\n"
            "   ✅ qabul qilindi: {accepted}\n"
            "   ❌ rad etildi: {rejected}\n"
            "   ⏳ kutilmoqda: {pending}\n"
            "Bugunga qabul qilingan: {today}\n"
            "Jami kishilar: {people}\n"
            "Jami soatlar: {hours}"
        ),
        # settings
        "settings_title": (
            "⚙️ Sozlamalar\n\n"
            "💰 Narxlar: {price}\n"
            "🕐 Ish vaqti: {hours}\n"
            "📍 Lokatsiya: {location}\n"
            "🎁 Aksiyalar: {promos} ta\n"
            "✍️ Bron qabuli: {username}"
        ),
        "value_set": "kiritilgan ✅",
        "value_not_set": "kiritilmagan ❌",
        "btn_edit_price": "💰 Narxlarni o'zgartirish",
        "btn_edit_hours": "🕐 Ish vaqti",
        "btn_edit_location": "📍 Lokatsiyani o'zgartirish",
        "btn_edit_promos": "🎁 Aksiyalar",
        "btn_edit_username": "✍️ Bron qabuli",
        "ask_price": (
            "Narxlarni bitta xabarda yuboring — mijozlar aynan shu ko'rinishda ko'radi.\n\n"
            "Hozirgi:\n{current}"
        ),
        "price_saved": "Narxlar saqlandi.",
        "ask_open_hour": "Ochilish vaqti (masalan: 11, 11:00 yoki 11:30):",
        "ask_close_hour": "Yopilish vaqti (masalan: 22 yoki 22:30):",
        "hour_invalid": "Vaqtni 11, 11:00 yoki 11:30 shaklida kiriting.",
        "hours_saved": "Ish vaqti saqlandi.",
        "ask_location": (
            "Lokatsiyani yuboring: Telegram geolokatsiyasi (📎 → Lokatsiya) "
            "yoki Yandex/Google Xarita havolasi."
        ),
        "location_invalid": "Telegram geolokatsiyasi yoki xarita havolasini (http…) yuboring.",
        "location_saved": "Lokatsiya saqlandi.",
        "ask_username": (
            "Bron uchun kimga yozishsin? Akkaunt usernameni yuboring — masalan "
            "@minidriftuz yoki https://t.me/minidriftuz.\n\nHozirgi: {current}"
        ),
        "username_invalid": "Bu username emasga o'xshaydi. Masalan: @minidriftuz",
        "username_saved": "Saqlandi: @{username}",
        "promos_admin_title": "🎁 Aksiyalar ({count} ta)\n\nO'chirish uchun aksiyani bosing.",
        "btn_add_promo": "➕ Aksiya qo'shish",
        "btn_del_promo": "🗑 {text}",
        "ask_promo_text": "Aksiyani bitta xabarda tasvirlab bering:",
        "ask_promo_media": "Aksiya uchun rasm yoki video yuboring.\nKerak bo'lmasa — «-» yuboring.",
        "promo_media_invalid": "Rasm, video yoki o'tkazib yuborish uchun «-» yuboring.",
        "promo_saved": "Aksiya qo'shildi.",
        "promo_deleted": "Aksiya o'chirildi.",
        # users
        "users_header": "👥 Foydalanuvchilar: {total} ({page}/{pages}-sahifa)",
        "users_empty": "Hozircha ro'yxatdan o'tgan foydalanuvchilar yo'q.",
        "user_card": "{name}\n{phone} · {language} · {joined} dan beri",
        # excel
        "xls_caption": "📗 {date} holatiga bronlar tarixi",
        "xls_sheet_overview": "Umumiy",
        "xls_sheet_customers": "Mijozlar",
        "xls_sheet_bookings": "Bronlar",
        "xls_title": "{date} holatiga statistika",
        "xls_metric_users": "Foydalanuvchilar",
        "xls_metric_requests": "So'rovlar (jami)",
        "xls_metric_accepted": "Qabul qilingan",
        "xls_metric_rejected": "Rad etilgan",
        "xls_metric_pending": "Kutilmoqda",
        "xls_metric_today": "Bugunga qabul qilingan",
        "xls_metric_people": "Jami kishilar",
        "xls_metric_hours": "Jami soatlar",
        "xls_h_name": "Ism",
        "xls_h_phone": "Telefon",
        "xls_h_language": "Til",
        "xls_h_requests": "So'rovlar",
        "xls_h_accepted": "Qabul qilingan",
        "xls_h_people": "Kishilar",
        "xls_h_hours": "Soatlar",
        "xls_h_first": "Birinchi marta",
        "xls_h_last": "Oxirgi bron",
        "xls_h_date": "Sana",
        "xls_h_when": "Vaqt",
        "xls_h_requested": "Mijoz so'rovi",
        "xls_h_status": "Holat",
        "xls_h_customer": "Mijoz",
        "xls_h_created": "Yaratilgan",
    },
}


def t(key: str, lang: str, **kwargs) -> str:
    table = _STRINGS.get(lang, _STRINGS["ru"])
    template = table.get(key)
    if template is None:
        template = _STRINGS["ru"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
