import json
import sqlite3
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from config import *
import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

DEFAULT_MARKER_COLOR = "red"
MAX_RENDERED_CITIES = 200
MARKER_COLORS = {
    "red": "#d62828",
    "blue": "#1d4ed8",
    "green": "#2a9d8f",
    "orange": "#f77f00",
    "purple": "#7b2cbf",
    "black": "#222222",
    "pink": "#d946ef",
    "gold": "#e0a106",
}
WEATHER_CODE_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class DB_Map:
    def __init__(self, database):
        self.database = database

    def create_user_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS users_cities (
                    user_id INTEGER,
                    city_id INTEGER,
                    FOREIGN KEY(city_id) REFERENCES cities(id),
                    UNIQUE(user_id, city_id)
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    marker_color TEXT NOT NULL
                )"""
            )
            conn.commit()

    def add_city(self, user_id, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM cities WHERE city = ? COLLATE NOCASE",
                (city_name,),
            )
            city_data = cursor.fetchone()

            if not city_data:
                return 0

            city_id = city_data[0]
            cursor.execute(
                "SELECT 1 FROM users_cities WHERE user_id = ? AND city_id = ?",
                (user_id, city_id),
            )
            if cursor.fetchone():
                return 2

            conn.execute("INSERT INTO users_cities VALUES (?, ?)", (user_id, city_id))
            conn.commit()
            return 1

    def select_cities(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT cities.city
                FROM users_cities
                JOIN cities ON users_cities.city_id = cities.id
                WHERE users_cities.user_id = ?
                ORDER BY cities.city""",
                (user_id,),
            )
            return [row[0] for row in cursor.fetchall()]

    def get_coordinates(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT lat, lng
                FROM cities
                WHERE city = ? COLLATE NOCASE""",
                (city_name,),
            )
            return cursor.fetchone()

    def get_city_record(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT city, lat, lng, country, population
                FROM cities
                WHERE city = ? COLLATE NOCASE""",
                (city_name,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return {
            "city": row[0],
            "lat": row[1],
            "lng": row[2],
            "country": row[3],
            "population": self._parse_population(row[4]),
        }

    def get_available_colors(self):
        return list(MARKER_COLORS.keys())

    def set_marker_color(self, user_id, color_name):
        normalized_color = self.normalize_marker_color(color_name)
        if normalized_color is None:
            return False

        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute(
                """INSERT INTO user_settings (user_id, marker_color)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET marker_color = excluded.marker_color""",
                (user_id, normalized_color),
            )
            conn.commit()
        return True

    def get_marker_color(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT marker_color FROM user_settings WHERE user_id = ?",
                (user_id,),
            )
            row = cursor.fetchone()

        if row:
            return row[0]
        return DEFAULT_MARKER_COLOR

    def normalize_marker_color(self, color_name):
        if not color_name:
            return None

        normalized_color = color_name.strip().lower()
        if normalized_color in MARKER_COLORS:
            return normalized_color
        return None

    def find_country_name(self, country_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT country FROM cities WHERE country = ? COLLATE NOCASE LIMIT 1",
                (country_name,),
            )
            row = cursor.fetchone()

        if row:
            return row[0]
        return None

    def get_cities_by_country(self, country_name, limit=MAX_RENDERED_CITIES):
        matched_country = self.find_country_name(country_name)
        if matched_country is None:
            return None

        count_query = "SELECT COUNT(*) FROM cities WHERE country = ? COLLATE NOCASE"
        select_query = """
            SELECT city
            FROM cities
            WHERE country = ? COLLATE NOCASE
            ORDER BY
                CASE WHEN population GLOB '[0-9]*' THEN CAST(population AS INTEGER) ELSE -1 END DESC,
                city ASC
            LIMIT ?
        """

        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            total_count = cursor.execute(count_query, (matched_country,)).fetchone()[0]
            cities = [
                row[0]
                for row in cursor.execute(select_query, (matched_country, limit)).fetchall()
            ]

        return {
            "country": matched_country,
            "cities": cities,
            "total_count": total_count,
            "shown_count": len(cities),
        }

    def get_cities_by_population(
        self,
        min_population,
        max_population,
        country_name=None,
        limit=MAX_RENDERED_CITIES,
    ):
        if min_population < 0 or max_population < 0 or min_population > max_population:
            return None

        params = [min_population, max_population]
        where_parts = [
            "population GLOB '[0-9]*'",
            "CAST(population AS INTEGER) >= ?",
            "CAST(population AS INTEGER) <= ?",
        ]

        matched_country = None
        if country_name:
            matched_country = self.find_country_name(country_name)
            if matched_country is None:
                return None
            where_parts.append("country = ? COLLATE NOCASE")
            params.append(matched_country)

        where_clause = " AND ".join(where_parts)
        count_query = f"SELECT COUNT(*) FROM cities WHERE {where_clause}"
        select_query = f"""
            SELECT city
            FROM cities
            WHERE {where_clause}
            ORDER BY CAST(population AS INTEGER) DESC, city ASC
            LIMIT ?
        """

        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            total_count = cursor.execute(count_query, tuple(params)).fetchone()[0]
            cities = [
                row[0]
                for row in cursor.execute(select_query, tuple(params + [limit])).fetchall()
            ]

        return {
            "country": matched_country,
            "cities": cities,
            "total_count": total_count,
            "shown_count": len(cities),
            "min_population": min_population,
            "max_population": max_population,
        }

    def get_weather_for_city(self, city_name):
        city = self.get_city_record(city_name)
        if city is None:
            return None

        try:
            current_data = self._fetch_current_data(city["lat"], city["lng"])
        except URLError:
            return {"error": "weather_unavailable"}

        weather_code = current_data["current"].get("weather_code")
        return {
            "city": city["city"],
            "country": city["country"],
            "temperature": current_data["current"].get("temperature_2m"),
            "wind_speed": current_data["current"].get("wind_speed_10m"),
            "weather_code": weather_code,
            "weather_description": WEATHER_CODE_DESCRIPTIONS.get(weather_code, "Unknown"),
            "is_day": bool(current_data["current"].get("is_day", 0)),
        }

    def get_time_for_city(self, city_name):
        city = self.get_city_record(city_name)
        if city is None:
            return None

        try:
            current_data = self._fetch_current_data(city["lat"], city["lng"])
        except URLError:
            return {"error": "time_unavailable"}

        return {
            "city": city["city"],
            "country": city["country"],
            "local_time": current_data["current"].get("time"),
            "timezone": current_data.get("timezone"),
            "timezone_abbreviation": current_data.get("timezone_abbreviation"),
        }

    def create_graph(self, path, cities, marker_color=DEFAULT_MARKER_COLOR):
        city_data = []
        for city_name in cities:
            city = self.get_city_record(city_name)
            if city is not None:
                city_data.append(city)

        if not city_data:
            return False

        normalized_color = self.normalize_marker_color(marker_color)
        if normalized_color is None:
            normalized_color = DEFAULT_MARKER_COLOR
        marker_fill = MARKER_COLORS[normalized_color]

        longitudes = [city["lng"] for city in city_data]
        latitudes = [city["lat"] for city in city_data]
        extent = self._build_extent(longitudes, latitudes)

        fig, ax = plt.subplots(
            figsize=(10, 6),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.set_facecolor("#a9d6f5")
        ax.add_feature(cfeature.OCEAN, facecolor="#8ecae6", zorder=0)
        ax.add_feature(
            cfeature.LAND,
            facecolor="#d9ed92",
            edgecolor="#6c757d",
            zorder=1,
        )
        ax.add_feature(
            cfeature.LAKES,
            facecolor="#bde0fe",
            edgecolor="#5dade2",
            linewidth=0.4,
            zorder=2,
        )
        ax.add_feature(
            cfeature.RIVERS,
            edgecolor="#4ea8de",
            linewidth=0.5,
            zorder=2,
        )
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=3)
        ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6, zorder=3)
        ax.add_feature(
            cfeature.STATES,
            linestyle="--",
            linewidth=0.3,
            edgecolor="#8d99ae",
            zorder=3,
        )
        gridliner = ax.gridlines(
            draw_labels=True,
            linewidth=0.3,
            color="gray",
            alpha=0.5,
        )
        gridliner.top_labels = False
        gridliner.right_labels = False

        for city in city_data:
            ax.plot(
                city["lng"],
                city["lat"],
                marker="o",
                color=marker_fill,
                markeredgecolor="white",
                markeredgewidth=0.8,
                markersize=7,
                transform=ccrs.PlateCarree(),
                zorder=4,
            )
            ax.text(
                city["lng"] + 0.6,
                city["lat"] + 0.6,
                f"{city['city']}, {city['country']}",
                fontsize=8,
                transform=ccrs.PlateCarree(),
                bbox={
                    "facecolor": "white",
                    "edgecolor": "none",
                    "alpha": 0.7,
                    "pad": 1.5,
                },
                zorder=5,
            )

        if len(city_data) == 1:
            ax.set_title(f"Map for {city_data[0]['city']} ({normalized_color} marker)")
        else:
            ax.set_title(f"Cities on the map ({normalized_color} markers)")

        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True

    def create_grapf(self, path, cities):
        return self.create_graph(path, cities)

    def _build_extent(self, longitudes, latitudes):
        min_lng = min(longitudes)
        max_lng = max(longitudes)
        min_lat = min(latitudes)
        max_lat = max(latitudes)

        lng_span = max(max_lng - min_lng, 10)
        lat_span = max(max_lat - min_lat, 8)

        lng_padding = max(lng_span * 0.2, 5)
        lat_padding = max(lat_span * 0.2, 4)

        west = max(-180, min_lng - lng_padding)
        east = min(180, max_lng + lng_padding)
        south = max(-90, min_lat - lat_padding)
        north = min(90, max_lat + lat_padding)
        return [west, east, south, north]

    def _parse_population(self, value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _fetch_current_data(self, latitude, longitude):
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,weather_code,wind_speed_10m,is_day",
            "timezone": "auto",
        }
        url = "https://api.open-meteo.com/v1/forecast?" + urlencode(params)
        with urlopen(url, timeout=20) as response:
            return json.load(response)

    def draw_distance(self, city1, city2):
        pass


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    output_path = project_dir / "sample_map.png"

    manager = DB_Map(DATABASE)
    manager.create_user_table()
    manager.create_graph(output_path, ["Tokyo", "Delhi", "London"])
