# %%
# Voronoi Maps
import imageio
import json
import matplotlib.pyplot as plt
import numpy as np

for n in [('portland', 'Portland, OR'), ('seattle', 'Seattle, WA'), ('san_francisco', 'San Francisco, CA')]:
    points = None
    with open(f'{n[0]}_meta.json') as f:
        points = json.load(f)

    coords = np.ndarray((len(points), 2))
    colors = np.zeros((len(points), 3))

    for i, (k, v) in enumerate(points.items()):
        coords[i] = [v['pano_lat'], v['pano_lon']]

        for th in [0, 90, 180, 270]:
            im = imageio.imread(f'{n[0]}_images/{k}_{th}_0.jpg')
            colors[i] += im.mean(axis=(0, 1)) / 4 / 255

    import osmnx as ox
    city = ox.geocode_to_gdf(f'{n[1]}')
    area = city.to_crs(epsg=3857)
    area_shape = area.iloc[0].geometry

    import geopandas as gpd

    land = gpd.read_file('land-polygons-complete-3857')

    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    tree = STRtree(land.geometry)
    query = tree.query(area_shape)

    union = unary_union(query)
    intersection = union.intersection(area_shape)

    from geovoronoi import voronoi_regions_from_coords, coords_to_points, points_to_coords
    from geovoronoi.plotting import subplot_for_map, plot_voronoi_polys

    from pyproj import Transformer

    trans = Transformer.from_crs(4326, 3857)
    coords_mercator = np.asarray(trans.transform(coords[:, 0], coords[:, 1], errcheck=True)).T

    pts = [p for p in coords_to_points(coords_mercator) if p.within(intersection)]
    coords_clipped = points_to_coords(pts)
    poly_shapes, pts, poly_to_pt_assignments = voronoi_regions_from_coords(coords_clipped, intersection)

    fig, ax = subplot_for_map()
    plot_voronoi_polys(ax, poly_shapes, color=colors)
# %%
