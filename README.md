# Mini Carting Booking Bot

Telegram bot for a Tashkent go-kart service (a **single service**, no branches).
Customers register once, then see the location, prices and current promotions —
and start a booking with one tap. The bot **records the request and notifies the
admin**, who accepts, rejects or corrects it; the details are settled in the
admin's DM.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit BOT_TOKEN and ADMIN_IDS
```

Get `BOT_TOKEN` from [@BotFather](https://t.me/BotFather). `ADMIN_IDS` is a
comma-separated list of Telegram user ids (get yours from @userinfobot) — these
are the accounts that get request cards and see the admin panel.

## Run

```bash
python -m bot.main
```

## Test

```bash
python -m pytest -v
```

## Customers

`/start` → language → name → phone. The menu then shows a standing nudge ("book
ahead so you don't wait") and: **📍 Lokatsiya**, **💰 Narxlar**, **🎁 Aksiyalar**,
**✍️ Bron qilish**, **🌐 Til**.

Bron qilish asks two questions — *which day and time* (typed freely) and *how
many people* — then hands back a button that opens the admin's DM with the
request already written. Customers get no accept/reject update in the bot; that
conversation happens in the DM.

## Admins

**🔧 Admin panel** (`/admin`), localized per admin:

- **⚙️ Sozlamalar** (`/service`) — prices (free text, shown verbatim), **working
  hours**, location (pin or maps link), aksiyalar (text + optional photo/video),
  and the username the Bron button opens.
- **🕐 Bo'sh vaqtlarni ko'rish** — free start times for today and tomorrow, with
  what's already booked underneath.
- **📊 Statistika** (`/stats`) — users, requests by status, people, hours.
- **📗 Bronlar tarixi** (`/export`) — Excel: overview, customers, every request.
- **👥 Foydalanuvchilar** (`/users`) — paged list of everyone registered.

### The request card

Every completed request is sent to each admin as a card:

```
🆕 Bron so'rovi — ⏳ kutilmoqda

Mijoz: Anvar Anvarov
Telefon: +998901234567
Vaqt: 17.07 18:00–19:00  («ertaga soat 18:00»)
Kishi: 5
Taxminiy davomiylik: 1 soat

Bron qabul qilindimi?
```

with **✅ Qabul qilish / ❌ Rad etish / ✏️ Ma'lumotlarni tahrirlash**. Editing
offers time, duration and headcount; each edit rewrites the same card rather
than sending a new message. The decision already taken is marked and stays
tappable, so it can be changed.

Rules worth knowing:

- **Only accepted bookings hold a time.** A pending request never blocks a slot.
- **Duration is `ceil(people / 6)` hours**, minimum 1. Editing the headcount
  recalculates it — *unless* you set the duration by hand, which pins it.
- **Accepting into a taken slot warns but does not refuse** — you may genuinely
  run two groups at once.
- The card shows the resolved time **and the customer's own words**, so a
  misreading is visible rather than silently wrong.

### Two things the bot cannot do

**It can't see the deep link being tapped.** A URL button fires no event, and the
DM goes to a personal account. So the admin is notified the moment the request is
complete — whether or not the customer ever sends the message.

**It can't always read the time.** "ertaga soat 18:00", "25-iyul 19:30",
"25.07 18:00", "завтра в 18:00" and a bare "18:00" all parse. Anything else
arrives flagged `⚠️ aniqlanmadi`, and Accept is refused until you set the time
via ✏️ → ⏰. A time with no day at all is read as today.

## One live screen

The chat is kept to a **single message**. Tapping a button rewrites the message
the button sits on; typing an answer deletes the prompt above it *and* your own
message, and the conversation continues in the new message. Confirmations are
folded into the top of the next screen, and anything sent alongside a screen —
the map pin, the aksiya photos — is cleared by the next navigation. Request cards
and the Excel file are deliberately exempt: they are records, not navigation.

Two limits, both cosmetic: Telegram won't let a bot delete anything **older than
48 hours**, and the registry of what's on screen is in-memory (like the FSM), so
a restart strands one screen.

## Architecture

- `bot/handlers/` — thin aiogram routers (registration, customer menu, admin
  panel, request cards, settings). `ui.py` owns the single-live-screen rules.
- `bot/services/` — the tested logic: `whenparse` (free text → a real date),
  `slots` (working hours, the 30-minute grid, overlap), `bookings`, `stats`,
  `export`, `promos`, `service`, `booking_link`, `notify`.
- `bot/db/` — SQLAlchemy async models + engine. `service` is one configured row;
  `promos` is one row per aksiya; requests live in **`booking_requests`** —
  *not* `bookings`, because older databases still carry an incompatible table by
  that name from the retired slot engine. `init_db` migrates in place and only
  ever adds, so those old tables linger harmlessly.
- `bot/locales.py` — ru/uz strings. `bot/keyboards/`, `bot/states.py`, `bot/middlewares/`.
