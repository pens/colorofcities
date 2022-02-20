# Copyright 2021 Seth Pendergrass. See LICENSE.
#
# Using metadata & panoramas pulled down from Google Street View in step 2,
# this generates a voronoi diagram for each city. One point & panorama
# corresponds to one poly in the diagram--unless out of bounds. City bounds
# are pulled down from OSM and water is clipped out to leave only actual land.
#
# NOTE: you'll need to download land-polygons-complete-3857/ from
# https://osmdata.openstreetmap.de/data/land-polygons.html

import json
import os

import geopandas as gpd
import imageio
from matplotlib.colors import to_hex
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from geovoronoi import coords_to_points, points_to_coords, voronoi_regions_from_coords
from geovoronoi.plotting import plot_voronoi_polys, subplot_for_map
from pyproj import Transformer
from shapely.affinity import scale, affine_transform
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree


def load_land_polys() -> STRtree:
    # Load all landmasses into structure optimized for intersection lookup
    # Make sure you've downloaded this file
    land_polygons = gpd.read_file("land-polygons-complete-3857")
    return STRtree(land_polygons.geometry)


def generate_city_shape(values: dict, land: STRtree) -> MultiPolygon:
    # Download city boundaries from OSM
    city = ox.geocode_to_gdf(f"{values['name']}")
    city_3857 = city.to_crs(epsg=3857)
    city_bounds = city_3857.iloc[0].geometry

    # Intersect city boundaries with landmasses, to remove oceans
    land_intersecting = land.query(city_bounds)
    land_unioned = unary_union(land_intersecting)
    city_excluding_ocean = land_unioned.intersection(city_bounds)

    # Download lakes, rivers, etc from OSM
    # HACK tags were missing for Portage Bay (Seattle), so I used water
    # This ends up included water I didn't want, like wastewater ponds
    water = ox.geometries_from_place(values["name"], {
        "water": ["lake", "river"],
        "natural": ["coastline", "strait", "bay", "canal", "water"]
    })
    water_3857 = water.to_crs(epsg=3857)
    water_unioned = water_3857.unary_union
    city_land = city_excluding_ocean.difference(water_unioned)

    # Voronoi creation fails with non-polygons
    land_geometry = MultiPolygon([geom for geom in city_land.geoms if type(geom) is Polygon])
    return land_geometry


def convert_images_to_color(city: str, pano_id: str) -> np.ndarray:
    images = []
    for th in [0, 90, 180, 270]:
        images.append(imageio.imread(f"panos/{city}/{pano_id}_{th}.jpg"))

    # Determine color of voronoi poly
    color = np.zeros(3)
    for image in images:
        color += image[160:480, :].mean(axis=(0, 1)) / 4 / 255

    return color


def process_points(
    city: str, land_geometry: MultiPolygon
) -> tuple[np.ndarray, np.ndarray]:

    with open(f"metadata/{city}.json") as f:
        metadata = json.load(f)

    coords = np.ndarray((len(metadata), 2))
    colors = np.zeros((len(metadata), 3))

    for i, (pano_id, values) in enumerate(metadata.items()):
        coords[i] = [values["lat"], values["lon"]]
        colors[i] = convert_images_to_color(city, pano_id)

    # Convert from WGS 84 to Mercator Projection
    trans = Transformer.from_crs(4326, 3857)
    coords_3857 = np.asarray(
        trans.transform(coords[:, 0], coords[:, 1], errcheck=True)
    ).T

    # Generating polys can fail if points lay outside bounds
    points = [p for p in coords_to_points(coords_3857) if p.within(land_geometry)]
    coords_bounded = points_to_coords(points)

    return coords_bounded, colors


def create_map(land_geometry: MultiPolygon, coords: np.ndarray, colors: np.ndarray):
    polys, pts = voronoi_regions_from_coords(coords, land_geometry)

    bounds = np.ndarray((len(polys), 4))
    for i in polys:
        bounds[i] = polys[i].bounds
    x = min(bounds[:, 0])
    y = min(bounds[:, 1])
    w = max(bounds[:, 2]) - x
    h = max(bounds[:, 3]) - y

    c = (x + w / 2, y + h / 2, 0)
    x_s = 1000 / w
    y_s = 1000 / w
    x_t = -x * x_s
    y_t = (y + h) * y_s
    trans = [x_s, 0, 0, -y_s, x_t, y_t]

    h_scaled = h * y_s
    w_scaled = w * x_s

    polys_adjusted = []
    for i in polys:
        polys_adjusted.append(affine_transform(polys[i], trans))

    with open(f"output/{city}.svg", "w") as f:
        f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
<svg version="1.1" viewBox="0 0 {w_scaled} {h_scaled}" xmlns="http://www.w3.org/2000/svg">""")
        for i in polys:
            f.write(f"{polys_adjusted[i].svg(scale_factor=.5, fill_color=to_hex(np.mean(colors[pts[i]], axis=0)))}\n")
        f.write("</svg>")


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)

    with open("cities.json") as f:
        cities = json.load(f)

    print("Loading land polygons")
    land = load_land_polys()

    for city, values in cities.items():
        print(f"Generating voronoi for {city}")
        land_geometry = generate_city_shape(values, land)
        coords, colors = process_points(city, land_geometry)

        create_map(land_geometry, coords, colors)