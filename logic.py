import sqlite3
from pathlib import Path

from config import *
import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt


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

    def create_graph(self, path, cities):
        city_data = []
        for city_name in cities:
            city = self.get_city_data(city_name)
            if city is not None:
                city_data.append(city)

        if not city_data:
            return False

        longitudes = [city[2] for city in city_data]
        latitudes = [city[1] for city in city_data]
        extent = self._build_extent(longitudes, latitudes)

        fig, ax = plt.subplots(
            figsize=(10, 6),
            subplot_kw={"projection": ccrs.PlateCarree()},
        )

        ax.set_extent(extent, crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.LAND, facecolor="#f3efe4")
        ax.add_feature(cfeature.OCEAN, facecolor="#cfe8ff")
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.BORDERS, linestyle=":", linewidth=0.6)
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
                color="#d62828",
                markersize=6,
                transform=ccrs.PlateCarree(),
            )
            ax.text(
                longitude + 0.6,
                latitude + 0.6,
                f"{city_name}, {country}",
                fontsize=8,
                transform=ccrs.PlateCarree(),
            )

        if len(city_data) == 1:
            ax.set_title(f"Map for {city_data[0][0]}")
        else:
            ax.set_title("Saved cities on the map")

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
