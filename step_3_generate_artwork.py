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
import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from geovoronoi import coords_to_points, points_to_coords, voronoi_regions_from_coords
from geovoronoi.plotting import plot_voronoi_polys, subplot_for_map
from pyproj import Transformer
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree


def generate_city_shape(name: str) -> MultiPolygon:
    # Load all landmasses into structure optimized for intersection lookup
    # Make sure you've downloaded this file
    # TODO should have cached this but whatever
    land_polygons = gpd.read_file("land-polygons-complete-3857")
    tree = STRtree(land_polygons.geometry)

    # Download city boundaries from OSM
    city = ox.geocode_to_gdf(f"{name}")
    area = city.to_crs(epsg=3857)
    area_shape = area.iloc[0].geometry

    # Intersect city boundaries with landmasses, to remove water
    intersecting_land = tree.query(area_shape)
    union = unary_union(intersecting_land)
    intersection = union.intersection(area_shape)

    # Voronoi creation fails with non-polygons
    land_geometry = MultiPolygon([geom for geom in intersection.geoms if type(geom) is Polygon])
    return land_geometry


def convert_images_to_color(city: str, pano_id: str) -> np.ndarray:
    images = []
    for th in [0, 90, 180, 270]:
        images.append(imageio.imread(f"panos/{city}/{pano_id}_{th}.jpg"))

    # Determine color of voronoi poly
    color = np.zeros(3)
    for image in images:
        color += image.mean(axis=(0, 1)) / 4 / 255

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


if __name__ == "__main__":
    with open("cities.json") as f:
        cities = json.load(f)

    os.makedirs("output", exist_ok=True)

    for city, values in cities.items():
        print(f"Generating voronoi for {city}")
        land_geometry = generate_city_shape(values["name"])
        coords, colors = process_points(city, land_geometry)

        polys = voronoi_regions_from_coords(coords, land_geometry)[0]

        fig, ax = subplot_for_map()
        plot_voronoi_polys(ax, polys, color=colors)
        plt.savefig(f"output/{city}.svg", transparent=True)
