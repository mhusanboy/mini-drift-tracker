# Mini Carting Booking Bot

Telegram bot for a Tashkent go-kart service: customers register and book hourly
slots; admins get notified and view analytics + manage branches.

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

- **Users:** `/start` → pick language → name → share phone → main menu →
  Book a slot (branch → day → time → people → confirm). `/mybookings` to view
  or cancel.
- **Admins:** get a DM on each new booking/cancellation. `/stats` for an
  overview, `/users` for per-customer analytics, `/branches` to add/edit or
  activate/deactivate branches.

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, booking, my-bookings, admin).
- `bot/services/` — tested business logic (slots, stats, notifications).
- `bot/db/` — SQLAlchemy async models + engine; slots are computed, not stored.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
