# Mini Carting Booking Bot

Telegram bot for a Tashkent go-kart service (a **single service**, no branches):
customers register and book hourly slots; admins get notified, configure the
service, manage day-offs, and view bookings + analytics.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit BOT_TOKEN and ADMIN_IDS
```

Get `BOT_TOKEN` from [@BotFather](https://t.me/BotFather). `ADMIN_IDS` is a
comma-separated list of Telegram user ids (get yours from @userinfobot).

## Run

```bash
python -m bot.main
```

## Test

```bash
python -m pytest -v
```

## Usage

- **Users:** `/start` → pick language → name → share phone. The bot then shows
  the **service location** (map pin or link) and a menu: **Book / My bookings /
  Language**. Book → **day (today or tomorrow) → time → number of people →
  confirm**. Start times are on **:00 and :30** (picker shows :00 in the left
  column, :30 in the right). Customers see only their start time; a booking
  quietly reserves `ceil(people / 6)` hours behind the scenes. `/mybookings` to
  view or cancel. A booking disappears from *My bookings* once it has finished.
  - ~**1 hour before** a booking the bot asks "are you coming?" — **Yes** keeps
    it; **No** cancels it and frees the slot (admin is notified).
  - After a booking the admin marked as **attended**, the bot asks the customer
    to **rate 1–5 ⭐**.
- **Admins** (Telegram IDs in `ADMIN_IDS`): main menu shows **🔧 Admin panel**
  (also `/admin`), localized to the admin. DM on each new booking/cancellation.
  - **⚙️ Settings** (`/service`) — set/update the service: name → address →
    opening → closing → **location** (Telegram location/venue, or a Yandex/Google
    Maps link; `-` to skip). Times accept `11`, `11:00`, `11:30`.
  - **📅 Show bookings** — pick **today or tomorrow** to see that day's booked
    times (with the full `HH:MM–HH:MM` span) and each customer's name/phone, and
    mark **✅ Came / ❌ No-show**. Finished bookings drop off automatically.
  - **🛌 Day-offs** — today + tomorrow, each a 🟢/🚫 toggle; a 🚫 day is hidden
    from customers. Ad-hoc; doesn't affect already-made bookings.
  - **📊 Stats** / **👥 Users** / **📊 Excel export** (`/export`) — as before.

A background scheduler (inside the bot process) sends the reminders and rating
requests every minute.

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, booking, my-bookings,
  admin panel, service settings, bookings view, day-offs).
- `bot/services/` — tested business logic (slots + service + day-offs, stats,
  export, notifications).
- `bot/db/` — SQLAlchemy async models + engine. The single service is one row of
  the `branches` table; day-offs are rows in `day_offs`; slots are computed.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
