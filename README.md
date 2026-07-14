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
- **Admins** (Telegram IDs listed in `ADMIN_IDS`): after `/start` the main menu
  shows a **🔧 Admin panel** button (also reachable via `/admin`), with
  **Branches / Stats / Users**. Admin commands also appear in Telegram's `/`
  menu. Admins get a DM on each new booking/cancellation.
  - **Add a location:** open the panel → **Branches** (or `/branches`) →
    **➕ Add branch** → enter name → address → opening time → closing time →
    **send the branch location** (a Telegram location/venue, or a Yandex/Google
    Maps link; send `-` to skip). Opening/closing accept `11`, `11:00`, `11:30`.
    Customers see the branch's location (a map pin or the link) when they pick it.
  - **Booking times are automatic:** every hour between the branch's opening and
    closing hour becomes a bookable slot (e.g. open 10, close 22 → 10:00…21:00).
    A customer's slot spans `ceil(people / 6)` consecutive hours.
  - `/stats` — totals + per-branch counts. `/users` — per-customer analytics.
  - **📊 Excel export** (panel button or `/export`) — sends an `.xlsx` workbook
    with three sheets: **Overview** (totals + per-branch breakdown),
    **Customers** (per-user analytics for promotions), and **Bookings** (every
    booking, including cancellations). Sheet names and headers are in the
    admin's language.
  - Edit, activate/deactivate, or **delete** a branch from the same **Branches**
    view. Delete asks for confirmation and keeps the branch's past bookings as
    history (they still appear in stats and the Excel export).

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, booking, my-bookings, admin).
- `bot/services/` — tested business logic (slots, stats, notifications).
- `bot/db/` — SQLAlchemy async models + engine; slots are computed, not stored.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
