#%%
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from IPython.display import display


# TODO
# Kmeans on all images per city (how does this work exactly?)
# compare w/ ground & sky
# 3d scatterplot per city
# scatterplot HSV
# how to load bounds from osm into map?

imgs = []

for h in [0, 90, 180, 270]:
    im = Image.open('portland_images/The Pod_{}_0.jpg'.format(h))
    imgs.append(np.asarray(im) / 255)

def show(img):
    tmp = (img * 255).astype(np.uint8)
    display(Image.fromarray(tmp))

pano = np.hstack(imgs)
show(pano)

# %%
# Sorting by HSV, per row
pano_hsv = mpl.colors.rgb_to_hsv(pano / 255)
show(pano_hsv)

pano_hsv_flat = np.ndarray(pano_hsv.shape[0:2])
for r in range(pano_hsv.shape[0]):
    for c in range(pano_hsv.shape[1]):
        (h, s, v) = pano_hsv[r, c]
        pano_hsv_flat[r, c] = v * 256 ** 3 + s * 256 ** 2 + h * 256

idxs = np.argsort(pano_hsv_flat, 1)

pano_sorted = np.take_along_axis(pano, idxs[..., np.newaxis], 1)
pano_hsv_sorted = np.take_along_axis(pano_hsv, idxs[..., np.newaxis], 1)

show(pano_sorted)
show(pano_hsv_sorted)

# %%
# Most common colors
pano_int = (pano * 255).astype(np.uint8).reshape(-1, pano.shape[2])

vals, cnts = np.unique(pano_int, return_counts=True, axis=0)
idxs2 = np.argsort(cnts)
colors_freq2 = np.array(vals[idxs2[-10:]])
plt.figure()
plt.imshow(colors_freq2[np.newaxis])

#%%
color_mean = np.mean(pano_int, axis=0)
plt.imshow(color_mean[np.newaxis, np.newaxis] / 255)

# %%
# 3D Scatterplot
f, ax = plt.subplots(subplot_kw={'projection': '3d'})
scales = cnts / np.max(cnts)
point_colors = vals / 255
ax.scatter(vals[:, 0], vals[:, 1], vals[:, 2], s=scales, c=point_colors)

# %%
# K-Means clustering
from sklearn.cluster import KMeans

pano_flat = pano.reshape(pano.shape[0] * pano.shape[1], pano.shape[2])

kmeans = KMeans(10).fit(pano_flat)

centers = kmeans.cluster_centers_
labels = kmeans.labels_

plt.imshow(centers[np.newaxis])
show(centers[labels].reshape(pano.shape))
#labels = kmeans.predict(pano_flat)

# %%
# Mean color of all cities
import glob

for city in ['portland', 'seattle', 'san_francisco']:
    files = glob.glob('{}_images/*.jpg'.format(city))

    colors = []

    for file in files:
        im = Image.open(file)
        imn = np.array(im)
        imn = imn.reshape(imn.shape[0] * imn.shape[1], imn.shape[2])
        colors.append(np.mean(imn, axis=0))

    colorsn = np.array(colors)
    color_mean = np.mean(colorsn, axis=0)[np.newaxis, np.newaxis] / 255

    plt.figure()
    plt.suptitle(city)
    plt.imshow(color_mean)

# %%
# Plot Portland on map
import cartopy.crs as ccrs

fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.PlateCarree(), frameon=False)
ax.coastlines()
ax.plot(-122.6750, 45.5051, 'rx', transform=ccrs.Geodetic())

# %%
# Plt mean colors of portland
import cartopy.crs as ccrs
import json

fig = plt.figure()
ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.PlateCarree(), frameon=False)
ax.coastlines()


points = None
with open('portland_meta.json') as f:
    points = json.load(f)

X = np.ndarray((len(points), 2))
Y = np.ndarray((len(points), 3))
idx = 0

for i, p in points.items():
    lon = p['pano_lon']
    lat = p['pano_lat']

    X[idx, 0] = lon
    X[idx, 1] = lat

    colors = []
    for j in [0, 90, 180, 270]:
        im = Image.open('portland_images/{}_{}_0.jpg'.format(i, j))
        imn = np.array(im)
        imn = imn.reshape(imn.shape[0] * imn.shape[1], imn.shape[2])
        colors.append(np.mean(imn, axis=0) / 255)

    color = np.mean(colors, axis=0)

    Y[idx] = color
    idx += 1

    ax.scatter(lon, lat, 100, color=color)

# %%
# Voronoi
from scipy.spatial import Voronoi, voronoi_plot_2d

vor = Voronoi(X)
fig = voronoi_plot_2d(vor)

# %%
# Which seasons?
points = None
with open('portland_meta.json') as f:
    points = json.load(f)

months = np.zeros((12))
for i, p in points.items():
    if p['pano_date'] is not None:
        date = p['pano_date']
        month = int(date.split('-')[1]) - 1
        months[month] += 1

f, ax = plt.subplots()
ax.bar(np.arange(1, 13), months)
# %%
