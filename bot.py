import tempfile
from pathlib import Path

import telebot

from config import *
from logic import *


bot = telebot.TeleBot(TOKEN)


def extract_city_name(message_text):
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def send_map(chat_id, cities, caption):
    project_dir = Path(__file__).resolve().parent
    with tempfile.NamedTemporaryFile(
        dir=project_dir,
        prefix=f"map_{chat_id}_",
        suffix=".png",
        delete=False,
    ) as temp_file:
        image_path = Path(temp_file.name)

    try:
        marker_color = manager.get_marker_color(chat_id)
        if not manager.create_graph(image_path, cities, marker_color=marker_color):
            return False

        with image_path.open("rb") as image_file:
            bot.send_photo(chat_id, image_file, caption=caption)
        return True
    finally:
        image_path.unlink(missing_ok=True)


@bot.message_handler(commands=["start"])
def handle_start(message):
    current_color = manager.get_marker_color(message.chat.id)
    bot.send_message(
        message.chat.id,
        "Hello. I can show cities on the map.\n"
        f"Your current marker color is {current_color}.\n"
        "Use /help to see the available commands.",
    )


@bot.message_handler(commands=["help"])
def handle_help(message):
    bot.send_message(
        message.chat.id,
        "Available commands:\n"
        "/start - start the bot\n"
        "/help - show all commands\n"
        "/show_colors - show available marker colors\n"
        "/set_marker_color <color> - choose your marker color\n"
        "/show_city <city name> - show one city on the map\n"
        "/remember_city <city name> - save a city to your list\n"
        "/show_my_cities - show all saved cities on one map",
    )


@bot.message_handler(commands=["show_colors"])
def handle_show_colors(message):
    colors = ", ".join(manager.get_available_colors())
    current_color = manager.get_marker_color(message.chat.id)
    bot.send_message(
        message.chat.id,
        f"Available marker colors: {colors}\nCurrent color: {current_color}",
    )


@bot.message_handler(commands=["set_marker_color"])
def handle_set_marker_color(message):
    color_name = extract_city_name(message.text)
    if not color_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /set_marker_color blue",
        )
        return

    if manager.set_marker_color(message.chat.id, color_name):
        bot.send_message(
            message.chat.id,
            f"Marker color changed to {color_name.strip().lower()}.",
        )
        return

    bot.send_message(
        message.chat.id,
        "Unknown color. Use /show_colors to see the available options.",
    )


@bot.message_handler(commands=["show_city"])
def handle_show_city(message):
    city_name = extract_city_name(message.text)
    if not city_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_city Tokyo",
        )
        return

    if not send_map(message.chat.id, [city_name], f"City on the map: {city_name}"):
        bot.send_message(
            message.chat.id,
            "I do not know this city. Make sure the name is written in English.",
        )


@bot.message_handler(commands=["remember_city"])
def handle_remember_city(message):
    user_id = message.chat.id
    city_name = extract_city_name(message.text)

    if not city_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /remember_city Tokyo",
        )
        return

    result = manager.add_city(user_id, city_name)
    if result == 1:
        bot.send_message(message.chat.id, f"City {city_name} was saved.")
    elif result == 2:
        bot.send_message(message.chat.id, f"City {city_name} is already in your list.")
    else:
        bot.send_message(
            message.chat.id,
            "I do not know this city. Make sure the name is written in English.",
        )


@bot.message_handler(commands=["show_my_cities"])
def handle_show_visited_cities(message):
    cities = manager.select_cities(message.chat.id)
    if not cities:
        bot.send_message(
            message.chat.id,
            "Your saved city list is empty. Use /remember_city <city name> first.",
        )
        return

    current_color = manager.get_marker_color(message.chat.id)
    caption = f"Your saved cities ({current_color} markers):\n" + ", ".join(cities)
    send_map(message.chat.id, cities, caption)


if __name__ == "__main__":
    manager = DB_Map(DATABASE)
    manager.create_user_table()
    bot.polling()
