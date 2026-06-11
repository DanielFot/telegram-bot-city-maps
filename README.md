# Telegram Bot With City Maps

This project contains a Telegram bot that works with a prepared SQLite database of cities from around the world. The bot can show one city on a map, save cities for each user, render saved cities on one image, filter cities by country and population, and show live weather and local time for a city.

## Features

- Show a requested city on a map with its marker and label
- Save cities to a personal user list
- Show all saved cities on one map
- Choose a personal marker color for map points
- Show cities from a specific country
- Show cities by population range
- Show cities by country and population range at the same time
- Show current weather for a city using the Open-Meteo API
- Show the local time for a city using the Open-Meteo API
- Shade land and ocean areas with different colors
- Draw lakes, rivers, coastlines, borders, and state lines

## Technologies

- Python 3.11
- SQLite
- PyTelegramBotAPI
- Matplotlib
- Cartopy
- Open-Meteo API

## Project Files

- `bot.py` - Telegram bot commands and message handlers
- `logic.py` - database work, user settings, filters, map generation, and API requests
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
- `/show_country <country>` - render cities from one country
- `/show_population <min> <max>` - render cities inside a population range
- `/show_country_population <country> | <min> | <max>` - render cities using both country and population
- `/show_weather <city name>` - show current weather in the city
- `/show_time <city name>` - show local time in the city
- `/remember_city <city name>` - save a city to the user list
- `/show_my_cities` - render all saved cities on one map

## Notes

- City and country names should be written in English.
- The provided database contains `population`, not real population density, so the density-related filter is implemented with population ranges.
- The bot creates the `users_cities` and `user_settings` tables automatically on startup.
- Map images are generated temporarily and removed after they are sent to Telegram.
- Available marker colors: `red`, `blue`, `green`, `orange`, `purple`, `black`, `pink`, `gold`.
