# Telegram Bot With City Maps

This project contains a Telegram bot that works with a prepared SQLite database of cities from around the world. The bot can show one city on a map, save cities for each user, render all saved cities on one image, and let each user choose the marker color used on the map.

## Features

- Show a requested city on a map with its marker and label
- Save cities to a personal user list
- Show all saved cities on one map
- Let each user choose a marker color for map points
- Shade land and ocean areas with different colors
- Draw extra geographical features such as lakes, rivers, coastlines, borders, and state lines
- Use a prepared SQLite database with city coordinates

## Technologies

- Python 3.11
- SQLite
- PyTelegramBotAPI
- Matplotlib
- Cartopy

## Project Files

- `bot.py` - Telegram bot commands and message handlers
- `logic.py` - database work, user settings, and map generation
- `config.py` - bot token and database file name
- `database.db` - prepared city database

## Setup

1. Clone the repository.
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Open `config.py` and add your bot token:

```python
DATABASE = "database.db"
TOKEN = "your_telegram_bot_token"
```

4. Start the bot:

```bash
python bot.py
```

## Commands

- `/start` - show the welcome message
- `/help` - show the list of commands
- `/show_colors` - show the available marker colors
- `/set_marker_color <color>` - choose the marker color for your maps
- `/show_city <city name>` - render one city on the map
- `/remember_city <city name>` - save a city to the user list
- `/show_my_cities` - render all saved cities on one map

## Notes

- City names should be written in English.
- The bot creates the `users_cities` and `user_settings` tables automatically on startup.
- Map images are generated temporarily and removed after they are sent to Telegram.
- Available marker colors: `red`, `blue`, `green`, `orange`, `purple`, `black`, `pink`, `gold`.
