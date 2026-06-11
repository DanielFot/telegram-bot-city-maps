import tempfile
from pathlib import Path

import telebot

from config import *
from logic import *


bot = telebot.TeleBot(TOKEN)


def extract_argument(message_text):
    parts = message_text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()


def parse_population_range(argument_text):
    parts = argument_text.split()
    if len(parts) != 2:
        return None

    try:
        min_population = int(parts[0])
        max_population = int(parts[1])
    except ValueError:
        return None

    return min_population, max_population


def parse_country_population(argument_text):
    parts = [part.strip() for part in argument_text.split("|")]
    if len(parts) != 3:
        return None

    try:
        min_population = int(parts[1])
        max_population = int(parts[2])
    except ValueError:
        return None

    return parts[0], min_population, max_population


def build_limit_note(selection_result):
    if selection_result["total_count"] > selection_result["shown_count"]:
        return (
            f"\nShowing the top {selection_result['shown_count']} cities "
            f"out of {selection_result['total_count']} matches."
        )
    return ""


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
        "Hello. I can show cities on the map, filter them by country and population, "
        "and show weather and local time.\n"
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
        "/show_country <country> - show cities from one country\n"
        "/show_population <min> <max> - show cities by population range\n"
        "/show_country_population <country> | <min> | <max> - combine country and population\n"
        "/show_weather <city name> - show current weather in the city\n"
        "/show_time <city name> - show local time in the city\n"
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
    color_name = extract_argument(message.text)
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
    city_name = extract_argument(message.text)
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


@bot.message_handler(commands=["show_country"])
def handle_show_country(message):
    country_name = extract_argument(message.text)
    if not country_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_country Japan",
        )
        return

    result = manager.get_cities_by_country(country_name)
    if result is None or not result["cities"]:
        bot.send_message(
            message.chat.id,
            "I could not find cities for this country. Make sure the country name is written in English.",
        )
        return

    caption = (
        f"Cities from {result['country']}."
        f"{build_limit_note(result)}"
    )
    send_map(message.chat.id, result["cities"], caption)


@bot.message_handler(commands=["show_population"])
def handle_show_population(message):
    argument_text = extract_argument(message.text)
    population_range = parse_population_range(argument_text)
    if population_range is None:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_population 1000000 5000000",
        )
        return

    result = manager.get_cities_by_population(population_range[0], population_range[1])
    if result is None or not result["cities"]:
        bot.send_message(
            message.chat.id,
            "No cities matched this population range.",
        )
        return

    caption = (
        f"Cities with population from {result['min_population']} to {result['max_population']}."
        f"{build_limit_note(result)}"
    )
    send_map(message.chat.id, result["cities"], caption)


@bot.message_handler(commands=["show_country_population"])
def handle_show_country_population(message):
    argument_text = extract_argument(message.text)
    parsed_data = parse_country_population(argument_text)
    if parsed_data is None:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_country_population India | 1000000 | 5000000",
        )
        return

    result = manager.get_cities_by_population(
        parsed_data[1],
        parsed_data[2],
        country_name=parsed_data[0],
    )
    if result is None or not result["cities"]:
        bot.send_message(
            message.chat.id,
            "No cities matched this country and population range.",
        )
        return

    caption = (
        f"Cities from {result['country']} with population from "
        f"{result['min_population']} to {result['max_population']}."
        f"{build_limit_note(result)}"
    )
    send_map(message.chat.id, result["cities"], caption)


@bot.message_handler(commands=["show_weather"])
def handle_show_weather(message):
    city_name = extract_argument(message.text)
    if not city_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_weather Tokyo",
        )
        return

    weather = manager.get_weather_for_city(city_name)
    if weather is None:
        bot.send_message(
            message.chat.id,
            "I do not know this city. Make sure the name is written in English.",
        )
        return

    if weather.get("error") == "weather_unavailable":
        bot.send_message(
            message.chat.id,
            "Weather service is unavailable right now. Try again later.",
        )
        return

    day_state = "day" if weather["is_day"] else "night"
    bot.send_message(
        message.chat.id,
        f"Weather in {weather['city']}, {weather['country']}:\n"
        f"Temperature: {weather['temperature']} °C\n"
        f"Conditions: {weather['weather_description']}\n"
        f"Wind speed: {weather['wind_speed']} km/h\n"
        f"Time of day: {day_state}",
    )


@bot.message_handler(commands=["show_time"])
def handle_show_time(message):
    city_name = extract_argument(message.text)
    if not city_name:
        bot.send_message(
            message.chat.id,
            "Write the command like this: /show_time Tokyo",
        )
        return

    time_info = manager.get_time_for_city(city_name)
    if time_info is None:
        bot.send_message(
            message.chat.id,
            "I do not know this city. Make sure the name is written in English.",
        )
        return

    if time_info.get("error") == "time_unavailable":
        bot.send_message(
            message.chat.id,
            "Time service is unavailable right now. Try again later.",
        )
        return

    bot.send_message(
        message.chat.id,
        f"Local time in {time_info['city']}, {time_info['country']}:\n"
        f"{time_info['local_time']} ({time_info['timezone_abbreviation']})\n"
        f"Timezone: {time_info['timezone']}",
    )


@bot.message_handler(commands=["remember_city"])
def handle_remember_city(message):
    user_id = message.chat.id
    city_name = extract_argument(message.text)

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
def handle_show_my_cities(message):
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
