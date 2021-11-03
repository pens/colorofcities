# Color of Cities

This is an art project to represent the colors of the three cities I've lived in: Portland, Oregon; Seattle, Washington; and San Francisco, California.

I came up with the idea after a friend vising me in San Francisco pointed out how much more pastel the city felt as compared to Portland.
I didn't really have an end goal in mind, but instead just decided on a next step after the previous was finished.

This project collects boundary and point of interest (POI) information for each city from OpenStreetMap.
This is then used to collect Google Street View images.
These images determined the color of each POI.

## Script Flow

1. Collect points of interest from Open Street Map

    `get_osm_data.py`

2. Collect city bounds from Open Street Map

    `gen_osm_bounds.py`

3. Convert OSM data into points.

    `gen_points.py -> portland_points.json`

4. Collect Google Street View images.

    `get_streetviews.py`

5. Create maps.

    `create_maps.py`