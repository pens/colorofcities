# Copyright 2021-2 Seth Pendergrass. See LICENSE.
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
import textwrap

import geopandas as gpd
import geovoronoi as gv
import imageio
import matplotlib as mpl
import numpy as np
import osmnx as ox
import pyproj as pp
import shapely as sl
from shapely.geometry import MultiPolygon, Polygon
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
    land_unioned = sl.ops.unary_union(land_intersecting)
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
    land_geometry = MultiPolygon(
        [geom for geom in city_land.geoms if type(geom) is Polygon])
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


def process_points(city: str, land_geometry: MultiPolygon
                   ) -> tuple[np.ndarray, np.ndarray]:

    with open(f"metadata/{city}.json") as f:
        metadata = json.load(f)

    coords = np.ndarray((len(metadata), 2))
    colors = np.zeros((len(metadata), 3))

    for i, (pano_id, values) in enumerate(metadata.items()):
        coords[i] = [values["lat"], values["lon"]]
        colors[i] = convert_images_to_color(city, pano_id)

    # Convert from WGS 84 to Mercator Projection
    trans = pp.Transformer.from_crs(4326, 3857)
    coords_3857 = np.asarray(
        trans.transform(coords[:, 0], coords[:, 1], errcheck=True)
    ).T

    # Generating polys can fail if points lay outside bounds
    points = [p for p in gv.coords_to_points(
        coords_3857) if p.within(land_geometry)]
    coords_bounded = gv.points_to_coords(points)

    return coords_bounded, colors


def create_map(land_geometry: MultiPolygon, coords: np.ndarray,
               colors: np.ndarray):
    polys, pts = gv.voronoi_regions_from_coords(coords, land_geometry)

    x = float('inf')
    y = float('inf')
    w = -float('inf')
    h = -float('inf')
    for p in polys.values():
        x = min(x, p.bounds[0])
        y = min(y, p.bounds[1])
        w = max(w, p.bounds[2])
        h = max(h, p.bounds[3])
    w -= x
    h -= y

    # Scale dimensions s.t. larger = 1000.
    larger_dim = max(w, h)
    scale = 1000 / larger_dim

    # Latitudes increase from south to north, while SVG's y origin is in the
    # top left corner. Therefore, we need to mirror (scale by -1) the y values.
    # Post scaling, we shift x & y values to put top left at 0,0.
    x_t = scale * -x
    y_t = scale * (y + h)
    trans = [scale, 0, 0, -scale, x_t, y_t]

    for i, p in polys.items():
        polys[i] = sl.affinity.affine_transform(p, trans)

    with open(f"output/{city}.svg", "w") as f:
        f.write(textwrap.dedent(
            f"""\
            <?xml version="1.0" encoding="utf-8"?>
            <svg viewBox="0 0 {w * scale} {h * scale}" xmlns="http://www.w3.org/2000/svg">
            """))
        for i, p in polys.items():
            # HACK: Need shapely 1.8+ for opacity arg, but geovoronoi needs
            # shapely < 1.8. Instead, replace opacity="0.6" with "1.0"
            svg = p.svg(
                scale_factor=.5,
                fill_color=mpl.colors.to_hex(np.mean(colors[pts[i]], axis=0)))
            f.write(f"{svg}\n".replace('opacity="0.6"', 'opacity="1.0"'))
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
