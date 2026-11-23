<img src="pfp.png" alt="Versatile" width="250" height="250">

<p align="center">
  <h1 align="center">Versatile</h1>
  <p align="center">
    An open-source Discord bot for esports tournament management — scrims, slots, points tables, tickets, and more.
  </p>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11%2B-blue.svg" alt="Python"></a>
  <a href="https://github.com/Rapptz/discord.py"><img src="https://img.shields.io/badge/discord.py-2.3%2B-5865F2.svg" alt="discord.py"></a>
  <a href="https://github.com/ashish200729/vxbot"><img src="https://img.shields.io/badge/upstream-ashish200729%2Fvxbot-brightgreen.svg" alt="Upstream"></a>
</p>

> **Republished source.** This is a republication of [ashish200729/vxbot](https://github.com/ashish200729/vxbot), shared under the original MIT license. The original author is Ashish (Versatilex). Yadav is republishing it with full credit kept intact so more people can discover the project and its creator.

---

## Overview

**Versatile** is built for competitive gaming communities that run scrims, tournaments, and slot-based events on Discord. It automates the heavy lifting — registration, slot lists, drop locations, points tables, moderation, tickets, and premium subscriptions — so organizers can focus on running matches instead of managing spreadsheets.

Originally developed and open-sourced by **Versatilex** ([Ashish](https://github.com/ashish200729)). This repository is a republished copy of that source, shared by **Yadav** so everyone can know who built it. All original credit belongs to Ashish.

## Features

### Esports & Tournaments
- **Scrims** — slot management, reservations, bans, autoclean, and configurable timings
- **Tournaments** — registration, group stages, slot managers, and partner tournaments
- **Drop locations** — interactive map-based drop selection for Erangel, Miramar, Sanhok, and Rondo
- **IDP automation** — Gemini-powered OCR to extract room ID and password from screenshots
- **Points tables** — auto-generated leaderboard images
- **SS verification** — screenshot-based role verification
- **Tag check** — automated tag validation for registered teams

### Server Management
- **Tickets** — configurable support ticket system
- **Moderation** — role management, lockdown, and logging
- **Custom roles** — self-assignable role panels
- **Sticky messages** — persistent channel messages
- **Event logging** — audit trail for server activity

### Premium & Payments
- **Premium subscriptions** — guild and user premium tiers
- **PayU integration** — payment flow with hash-verified webhooks

### Optional Integrations
- **AI support chatbot** — Groq-powered Hinglish support for slot/registration queries
- **Music** — voice channel playback with YouTube and Spotify playlist support
- **WebSocket bridge** — real-time dashboard integration

## Tech Stack

| Layer | Technology |
|-------|------------|
| Bot framework | [discord.py](https://github.com/Rapptz/discord.py) / py-cord |
| Database | PostgreSQL + [Tortoise ORM](https://tortoise.github.io/) |
| Migrations | [Aerich](https://github.com/tortoise/aerich) |
| Payment server | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn |
| Image processing | Pillow |
| Config | python-dotenv |

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** database
- A [Discord application](https://discord.com/developers/applications) with a bot token
- *(Optional)* Groq API key for AI chatbot
- *(Optional)* Google Gemini API key for IDP OCR
- *(Optional)* Spotify credentials for playlist support
- *(Optional)* PayU merchant account for premium payments

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ashish200729/vxbot.git
cd vxbot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> If you are using Yadav's republished copy, replace the clone URL above with that repository's URL.

### 2. Configure environment

```bash
cp .env.example .env
cp src/config.example.py src/config.py
```

Edit `.env` with your credentials:

```env
DISCORD_TOKEN=your_discord_bot_token

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=vxbot
```

> Secrets are loaded from `.env` automatically. Never commit `.env` or `src/config.py`.

### 3. Set up the database

```bash
cd src
aerich init -t config.TORTOISE
aerich init-db
```

For schema changes after the initial setup:

```bash
aerich migrate
aerich upgrade
```

### 4. Run the bot

```bash
cd src
python bot.py
```

### 5. Run the payment server *(optional)*

```bash
cd src
uvicorn server.app:app --host 127.0.0.1 --port 8080
```

Set `FASTAPI_KEY` in `.env` to protect the `/getpremium` endpoint. Pass it as the `X-API-Key` header from trusted callers.

## Development

Auto-restart on file changes:

```bash
python scripts/watch.py
```

Windows shortcuts:

```bash
scripts\watch.bat       # CMD
scripts\watch.ps1       # PowerShell
```

## Project Structure

```
vxbot/
├── docs/
│   ├── setup.md          # Detailed setup guide
│   └── security.md       # Security checklist before going public
├── scripts/
│   └── watch.py          # Dev auto-restart utility
├── src/
│   ├── assets/maps/      # PUBG map images for drop locations
│   ├── cogs/             # Feature modules
│   │   ├── esports/      # Scrims, tournaments, slots, IDP
│   │   ├── tickets/      # Support ticket system
│   │   ├── mod/          # Moderation commands
│   │   ├── premium/      # Premium subscriptions
│   │   ├── events/       # Server event logging
│   │   ├── utility/      # General utilities
│   │   ├── ai-chatbot/   # Groq-powered support
│   │   └── ...
│   ├── core/             # Bot client, context, help system
│   ├── data/             # Fonts, images, runtime data
│   ├── models/           # Tortoise ORM models
│   ├── server/           # FastAPI payment server
│   ├── sockets/          # WebSocket integrations
│   ├── utils/            # Shared helpers
│   ├── bot.py            # Entry point
│   └── config.example.py # Config template (reads from .env)
├── .env.example
├── requirements.txt
└── LICENSE
```

## Configuration Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Discord bot token |
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_PORT` | Yes | PostgreSQL port |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DB` | Yes | Database name |
| `BOT_PREFIX` | No | Command prefix (default: `v`) |
| `FASTAPI_KEY` | No | Protects `/getpremium` via `X-API-Key` header |
| `GROQ_API_KEY` | No | Enables AI support chatbot |
| `GEMINI_API_KEY` | No | Enables IDP screenshot OCR |
| `SPOTIFY_CLIENT_ID` | No | Spotify playlist support |
| `SPOTIFY_CLIENT_SECRET` | No | Spotify playlist support |
| `PAYU_MERCHANT_KEY` | No | PayU payment integration |
| `PAYU_MERCHANT_SALT` | No | PayU payment integration |
| `DEV_IDS` | No | Comma-separated Discord user IDs for dev commands |

See [`.env.example`](.env.example) for the full list.

## Cog Modules

| Module | Description |
|--------|-------------|
| `cogs/esports` | Scrims, tournaments, slot management, drop locations, IDP |
| `cogs/tickets` | Support ticket creation and management |
| `cogs/mod` | Moderation tools and role management |
| `cogs/premium` | Premium subscription management |
| `cogs/events` | Server event logging and audit |
| `cogs/utility` | Embeds, reminders, and general utilities |
| `cogs/quomisc` | Bot info, setup, and custom bot appearance |
| `cogs/ai-chatbot` | AI-powered registration support |
| `cogs/customrole` | Self-assignable custom roles |
| `cogs/sticky` | Sticky message management |
| `cogs/reminder` | Scheduled reminders |

## Security

Before deploying or open-sourcing, read the [security guide](docs/security.md). It covers:

- Secret management with `.env`
- PayU webhook hash verification
- Rotating credentials exposed in Git history
- Pre-publish checklist

## Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to your fork and open a pull request

Please do not commit secrets, virtual environments, or database backups.

## License

This project is licensed under the [MIT License](LICENSE). The original copyright notice must remain in the `LICENSE` file.

## Credits

- **Original author:** [Versatilex (Ashish)](https://github.com/ashish200729)
- **Republished by:** Yadav, as a friend of Ashish, so everyone knows who built this

---

<p align="center">
  <sub>If Versatile helps your community, consider giving the original repo a star.</sub>
</p>
