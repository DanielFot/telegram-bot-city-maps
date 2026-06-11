import sqlite3
from pathlib import Path

from config import *
import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt

DEFAULT_MARKER_COLOR = "red"
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

    def get_city_data(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT city, lat, lng, country
                FROM cities
                WHERE city = ? COLLATE NOCASE""",
                (city_name,),
            )
            return cursor.fetchone()

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

    def create_graph(self, path, cities, marker_color=DEFAULT_MARKER_COLOR):
        city_data = []
        for city_name in cities:
            city = self.get_city_data(city_name)
            if city is not None:
                city_data.append(city)

        if not city_data:
            return False

        normalized_color = self.normalize_marker_color(marker_color)
        if normalized_color is None:
            normalized_color = DEFAULT_MARKER_COLOR
        marker_fill = MARKER_COLORS[normalized_color]

        longitudes = [city[2] for city in city_data]
        latitudes = [city[1] for city in city_data]
        extent = self._build_extent(longitudes, latitudes)

        fig, ax = plt.subplots(
            figsize=(10, 6),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.set_facecolor("#a9d6f5")
        ax.add_feature(cfeature.OCEAN, facecolor="#8ecae6", zorder=0)
        ax.add_feature(cfeature.LAND, facecolor="#d9ed92", edgecolor="#6c757d", zorder=1)
        ax.add_feature(cfeature.LAKES, facecolor="#bde0fe", edgecolor="#5dade2", linewidth=0.4, zorder=2)
        ax.add_feature(cfeature.RIVERS, edgecolor="#4ea8de", linewidth=0.5, zorder=2)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=3)
        ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6, zorder=3)
        ax.add_feature(cfeature.STATES, linestyle="--", linewidth=0.3, edgecolor="#8d99ae", zorder=3)
        gridliner = ax.gridlines(
            draw_labels=True,
            linewidth=0.3,
            color="gray",
            alpha=0.5,
        )
        gridliner.top_labels = False
        gridliner.right_labels = False

        for city_name, latitude, longitude, country in city_data:
            ax.plot(
                longitude,
                latitude,
                marker="o",
                color=marker_fill,
                markeredgecolor="white",
                markeredgewidth=0.8,
                markersize=7,
                transform=ccrs.PlateCarree(),
                zorder=4,
            )
            ax.text(
                longitude + 0.6,
                latitude + 0.6,
                f"{city_name}, {country}",
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
            ax.set_title(f"Map for {city_data[0][0]} ({normalized_color} marker)")
        else:
            ax.set_title(f"Saved cities on the map ({normalized_color} markers)")

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

    def draw_distance(self, city1, city2):
        pass


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    output_path = project_dir / "sample_map.png"

    manager = DB_Map(DATABASE)
    manager.create_user_table()
    manager.create_graph(output_path, ["Tokyo", "Delhi", "London"])
