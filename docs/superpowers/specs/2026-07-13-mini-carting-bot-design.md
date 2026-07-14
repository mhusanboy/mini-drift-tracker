# Mini Carting Booking Bot — Design

**Date:** 2026-07-13
**Status:** Approved (pending written-spec review)

A Telegram bot for a mini go-kart (carting) service in Tashkent. Customers
register, browse branches, and book an hourly slot. Admins get notified of new
bookings and can view per-customer analytics and manage branches.

## 1. Goals & scope

**In scope (v1):**

- User registration: language choice, full name, phone (via Share-contact).
- Booking flow: choose branch → choose day → choose free start time → enter
  number of people → confirm.
- Users can view and cancel their own upcoming bookings.
- Admin notifications on new booking and on cancellation.
- Admin stats: overview + per-user analytics for promotions.
- Admin branch management (add / edit / activate / deactivate) in-bot.
- Bilingual UI: Russian and Uzbek (Latin), chosen per user at first `/start`.

**Out of scope (v1):** payments, kart-level capacity (one group per slot),
web dashboard, DB migration tooling, multi-instance deployment.

## 2. Architecture & stack

- **aiogram 3.x** (async), Router-based modular handlers.
- **SQLAlchemy 2.0 async + aiosqlite** — SQLite file DB. Tables created on
  startup via `Base.metadata.create_all` (no Alembic — YAGNI for one service).
- **pydantic-settings** config from `.env`: `BOT_TOKEN`, `ADMIN_IDS`
  (comma-separated Telegram user IDs), `DB_PATH` (default `carting.db`).
- **FSM:** aiogram `MemoryStorage` for booking/admin wizards. An interrupted
  wizard resets on process restart — acceptable, flows are short.
- **i18n:** lightweight dict-based translator `t(key, lang, **kwargs)` with `ru`
  and `uz` locales in `locales.py`. No gettext tooling. The user's chosen
  language is stored on their record and injected via middleware.

### Key modeling decision — slots are computed, not stored

Each hourly slot holds exactly **one group** (the service has effectively one
kart/track resource per branch at a time; number of people is informational
only). Rather than materialize empty slot rows, availability is computed:

- A branch defines `open_hour` and `close_hour` (integers, 24h).
- For a given `(branch, date)`, the candidate start hours are
  `range(open_hour, close_hour)`.
- A confirmed `Booking` row **is** the occupancy. Free hours =
  candidate hours minus hours that already have a confirmed booking.
- A DB unique constraint on `(branch_id, date, start_hour)` for confirmed
  bookings prevents double-booking even under a race between listing and
  confirming.

## 3. Data model

**User**
| field | type | notes |
|-------|------|-------|
| `telegram_id` | int, PK | Telegram user id |
| `full_name` | str | as entered, e.g. "Anvar Anvarov" |
| `phone` | str | from shared contact |
| `language` | str | `ru` or `uz` |
| `created_at` | datetime | first seen |

**Branch**
| field | type | notes |
|-------|------|-------|
| `id` | int, PK | |
| `name` | str | |
| `address` | str | |
| `open_hour` | int | inclusive, 0–23 |
| `close_hour` | int | exclusive; last slot starts at `close_hour - 1` |
| `is_active` | bool | inactive branches hidden from users, history kept |
| `created_at` | datetime | |

**Booking**
| field | type | notes |
|-------|------|-------|
| `id` | int, PK | |
| `user_id` | int, FK → User.telegram_id | |
| `branch_id` | int, FK → Branch.id | |
| `date` | date | booking day |
| `start_hour` | int | 0–23 |
| `people_count` | int | informational, ≥ 1 |
| `status` | str | `confirmed` or `cancelled` |
| `created_at` | datetime | |

Constraint: **unique(`branch_id`, `date`, `start_hour`)** among `confirmed`
rows. (Implemented as a partial unique index, or by hard-deleting/among-status
logic — see plan.) Cancelled bookings free the hour for rebooking.

All stats are derived from these tables via queries — no analytics tables.

## 4. User booking flow (FSM)

```
/start
 └─ new user?
      → choose language (ru / uz)         [inline]
      → ask full name                     [text]
      → ask phone                         [Share-contact button ONLY]
      → save user → main menu
    returning user → main menu

Main menu: [ Book a slot ] [ My bookings ] [ Language ]

Book a slot:
 └─ choose branch      [inline, active branches]
  → choose day         [inline, next 7 days incl. today]
  → choose start time  [inline, only FREE hours for that branch+day]
  → enter № of people  [text, validated positive int]
  → confirm            [inline: Confirm / Cancel — shows full summary]
  → create booking → notify admins → success message
```

**Phone entry:** only the Telegram "Share contact" reply-keyboard button is
accepted. Typed text at that step is rejected with a reminder to use the button.

**Edge cases:**
- Slot taken between listing and confirm → unique-constraint violation caught →
  friendly "that time was just taken, choose another" → back to time list.
- No free hours for the chosen day → message + back to day selection.
- Past hours on *today* are filtered out of the free list.

## 5. My bookings (user)

- `/mybookings` (and main-menu button) lists the user's **upcoming** confirmed
  bookings (date/time ≥ now), each with a **Cancel** inline button.
- Cancelling sets `status = cancelled`, frees the slot, and **notifies admins**
  of the cancellation.
- Past bookings are not shown (kept for stats).

## 6. Admin side

Admins = Telegram user ids in `ADMIN_IDS`. Admin commands are ignored (or
answered with "not authorized") for non-admins.

- **New-booking notification:** on confirm, DM every admin with branch, date,
  time, people count, and customer full name + phone.
- **Cancellation notification:** on user cancel, DM every admin with the freed
  booking details.
- **`/stats`** — overview: total users, total bookings (confirmed), bookings
  today, and confirmed-booking count per branch.
- **`/users`** — paginated per-user analytics: full name, phone, total
  bookings, total people brought, first seen, last booking date, favorite
  branch (most-booked).
- **Branch management `/branches`:** list branches with inline buttons:
  - **Add** (FSM: name → address → open hour → close hour).
  - **Edit** (re-run the same fields).
  - **Activate / Deactivate** toggle.

## 7. Project structure

```
bot/
  main.py             # entrypoint + dispatcher wiring
  config.py           # pydantic-settings
  db/
    base.py           # async engine + session factory, create_all
    models.py         # User, Branch, Booking
  handlers/
    start.py          # registration + language + main menu
    booking.py        # booking wizard
    mybookings.py     # list/cancel own bookings
    admin.py          # /stats, /users
    admin_branches.py # /branches management
  keyboards/
    common.py         # main menu, language, back
    booking.py        # branch/day/time/confirm keyboards
    admin.py          # branch mgmt keyboards, pagination
  services/
    slots.py          # availability computation, booking create/cancel
    stats.py          # analytics queries
  states.py           # FSM state groups
  locales.py          # ru/uz strings + t()
  middlewares/
    user.py           # load-or-inject User + language into handler data
.env.example
requirements.txt
README.md
tests/
  test_slots.py
  test_stats.py
```

## 8. Error handling

- Global aiogram error handler logs exceptions and shows a generic friendly
  message rather than crashing the update.
- Double-booking guarded at the DB layer (unique constraint), not just by
  pre-check, to close the race window.
- Input validation: people count must be a positive integer; invalid input
  re-prompts without leaving the state.
- Non-admins invoking admin commands get a polite refusal.

## 9. Testing (TDD)

Focus on the pure logic layer that has no Telegram I/O:

- **`test_slots.py`**: free-hour computation across open/close ranges;
  exclusion of already-booked hours; exclusion of past hours for today;
  double-booking rejection via the unique constraint; cancel frees the hour.
- **`test_stats.py`**: per-user aggregates (totals, people brought), first
  seen / last booking, favorite-branch selection, per-branch counts.

Handlers are thin and delegate to services, so service-level tests cover the
meaningful behavior. Tests run against an in-memory / temp-file SQLite DB.

## 10. Open questions / assumptions

- Slots are hourly and on the hour (no half-hour granularity) — assumed.
- "Next 7 days including today" for the day picker — assumed, easily tuned.
- One admin notification per admin id (DM), no admin group — per decision.
- No user-facing booking edit (only cancel + rebook) — v1 simplification.
