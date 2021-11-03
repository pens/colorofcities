# %%
import json
from geopandas.plotting import _plot_linestring_collection
from geovoronoi.plotting import plot_voronoi_polys, subplot_for_map
import imageio
from matplotlib import pyplot as plt
import numpy as np
import osmnx as ox
from pyproj import Transformer
import geopandas as gpd
import geovoronoi as gv
from shapely.geometry.multipolygon import MultiPolygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

points = None
with open('san_francisco_meta.json') as f:
    points = json.load(f)

coords = np.ndarray((len(points), 2))
colors = np.zeros((len(points), 3))

for i, (k, v) in enumerate(points.items()):
    coords[i] = [v['pano_lat'], v['pano_lon']]

    for th in [0, 90, 180, 270]:
        im = imageio.imread(f'san_francisco_images/{k}_{th}_0.jpg')
        colors[i] += im.mean(axis=(0, 1)) / 4 / 255

city = ox.geocode_to_gdf('San Francisco, CA').to_crs(epsg=3857).iloc[0].geometry
land = gpd.read_file('land-polygons-complete-3857').geometry

tree = STRtree(land)
query = tree.query(city)

union = unary_union(query)
final = union.intersection(city)

final_filtered = MultiPolygon([p for p in final if p.geom_type == 'Polygon'])

trans = Transformer.from_crs(4326, 3857)
coords_trans = np.asarray(trans.transform(coords[:, 0], coords[:, 1])).T

pts = [p for p in gv.coords_to_points(coords_trans) if p.within(final_filtered)]
coords_int = gv.points_to_coords(pts)
poly_shapes, pts, poly_to_pt_assignments = gv.voronoi_regions_from_coords(coords_int, final_filtered)

fig, ax = subplot_for_map()
plot_voronoi_polys(ax, poly_shapes, color=colors)
# %%
fig.savefig('sf.svg')
# %%
