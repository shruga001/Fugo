# Fugo

A feature-rich Discord bot built with `discord.py`, featuring an economy system, leveling, games, server management, and more.

## Features

- **Economy System** — Balance management, daily bonuses, betting, and a treasury system per guild.
- **Leveling & XP** — Earn XP by sending messages, level up to unlock rank titles.
- **Games** — Blackjack, Rock-Paper-Scissors, Truth or Dare (TND), and UNO.
- **Market** — Buy and sell roles using in-bot currency, with subscription management.
- **Guild Management** — Configurable staff roles, allowed channels, co-owners, and per-guild setup.
- **Leaderboards** — Balance and message-count leaderboards per guild.
- **Monster Events** — Periodic monster drop events in designated channels.
- **Polls** — Create and manage polls within your server.

## Architecture

### Backend 2.0

Fugo was originally built with a monolithic backend where all functions lived in a single file and data was stored in flat JSON files. As the database grew, response times increased due to inefficient data loading — every operation loaded entire files even when only a few fields were needed.

The **Backend 2.0** restructured the codebase into modular, purpose-specific files:

```
app.py          — Main entry point and command definitions
fns.py          — Core utility functions and data access layer
listen.py       — Event listeners (on_message, on_ready, etc.)
guild_setup.py  — Guild configuration and setup flow
levels.py       — Leveling and rank management
market.py       — Market and subscription system
game.py         — Game-related commands
blackj.py       — Blackjack game logic
rps.py          — Rock-Paper-Scissors game
tnd.py          — Truth or Dare game
uno.py          — UNO card game
decor.py        — Custom decorators
user_setup.py   — User registration and daily bonuses
```

Data is stored in small, targeted files rather than monolithic ones. For example, guild leaderboards use a pre-indexed file so the leaderboard command only loads the top entries instead of iterating through every user.

### Current Migration: PostgreSQL + Supabase

Fugo is migrating from JSON file storage to **PostgreSQL** hosted on **Supabase**, accessed via `asyncpg`. This provides:

- **Atomic transactions** — No more partial writes or file corruption.
- **Concurrent access safety** — Multiple operations can run simultaneously.
- **Scalability** — SQL queries are efficient even with thousands of guilds and users.
- **Data integrity** — Constraints, foreign keys, and typed columns prevent invalid data.

The migration plan is detailed in [`implementation_plan.md`](implementation_plan.md).

#### Database Tables

| Table | Purpose |
|-------|---------|
| `guilds` | Per-guild configuration (roles, channels, treasury) |
| `users` | Global user metadata (last login) |
| `guild_members` | Per-user per-guild data (balance, XP, rank, message count) |
| `market_items` | Guild market listings |
| `subscriptions` | User subscriptions to market items |
| `guild_ranks` | Per-guild rank titles by level |
| `global_levels` | Global XP thresholds for each level |

Static assets (emoji mappings, help documentation, TND content, UNO deck) remain as JSON files.

## Commands

Prefix: `ft!`

| Command | Description |
|---------|-------------|
| `ft!reg` | Register a new user |
| `ft!bal` | Check your balance |
| `ft!daily` | Claim your daily bonus |
| `ft!bet <amount>` | Place a bet |
| `ft!lottery <amount>` | Enter the lottery |
| `ft!level` | Check your level and XP |
| `ft!rank` | View the leaderboard |
| `ft!buy <item>` | Buy an item from the market |
| `ft!cancle <item>` | Cancel a subscription |
| `ft!subs` | View your subscriptions |

Slash commands are also available for guild setup and management.

## Setup

### Prerequisites

- Python 3.10+
- A Discord bot token
- (Optional) A Supabase project for PostgreSQL

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/shruga001/Fugo.git
   cd Fugo
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```
   token=your_discord_bot_token
   app_id=your_discord_app_id
   DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
   ```

4. Run the bot:
   ```bash
   python app.py
   ```

### Database Migration

If setting up with PostgreSQL for the first time:

```bash
python migrate.py
```

This creates all required tables and imports existing JSON data.

## Project Structure

```
├── app.py                  # Main bot entry point
├── fns.py                  # Core functions and data layer
├── listen.py               # Event listeners
├── guild_setup.py          # Guild configuration
├── levels.py               # Leveling system
├── market.py               # Market and subscriptions
├── game.py                 # Game commands
├── blackj.py               # Blackjack
├── rps.py                  # Rock-Paper-Scissors
├── tnd.py                  # Truth or Dare
├── uno.py                  # UNO
├── decor.py                # Custom decorators
├── user_setup.py           # User registration
├── db.py                   # Database connection manager
├── migrate.py              # Migration script
├── schema.sql              # Database schema reference
├── implementation_plan.md  # Migration implementation plan
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── emojis/                 # Emoji mappings
├── guilds_data/            # Guild-specific data (JSON)
│   ├── help/               # Help documentation
│   └── {guild_id}/         # Per-guild data files
├── users_data/             # User data (JSON)
├── TND/                    # Truth or Dare content
└── uno/                    # UNO game data
```

## License

This project is private and not licensed for public use or distribution.