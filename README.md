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
  Language**. Book → **day → time → number of people → confirm** (no branch
  step). A slot spans `ceil(people / 6)` consecutive hours. `/mybookings` to
  view or cancel.
- **Admins** (Telegram IDs listed in `ADMIN_IDS`): after `/start` the main menu
  shows a **🔧 Admin panel** button (also `/admin`). All admin output is in the
  admin's own language. Admins get a DM on each new booking/cancellation.
  - **🔧 Service** (`/service`) — set/update the service: name → address →
    opening time → closing time → **location** (Telegram location/venue, or a
    Yandex/Google Maps link; `-` to skip). Times accept `11`, `11:00`, `11:30`;
    a half-hour opening pushes the first slot to the next full hour. Bookable
    hours are every hour between opening and closing.
  - **📅 Show bookings** — pick a day (next 7) to see that day's booked times
    with each customer's name and phone.
  - **🛌 Day-offs** — the next 7 days with a 🟢/🚫 toggle each; a 🚫 day is
    hidden from customers' day picker. Day-offs are ad-hoc (not a fixed weekly
    pattern) and don't affect already-made bookings.
  - **📊 Stats** — totals: users, bookings, today, total people, total hours.
    **👥 Users** — per-customer analytics for promotions.
  - **📊 Excel export** (panel button or `/export`) — an `.xlsx` with three
    sheets: **Overview**, **Customers**, **Bookings**. Localized to the admin.

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, booking, my-bookings,
  admin panel, service settings, bookings view, day-offs).
- `bot/services/` — tested business logic (slots + service + day-offs, stats,
  export, notifications).
- `bot/db/` — SQLAlchemy async models + engine. The single service is one row of
  the `branches` table; day-offs are rows in `day_offs`; slots are computed.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
