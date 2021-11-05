# Copyright 2021 Seth Pendergrass. See LICENSE.
#
# This script pulls points of interest from OpenStreetMap via the Overpass API.
# The returned data is simplified to name, latitude and longitude and written
# out. The cities queried over can be set in cities.json.

import json
import os

import overpy
from numpy import ndarray


def node_to_coord(node: overpy.Node) -> ndarray:
    return [float(node.lat), float(node.lon)]


def way_to_coord(way: overpy.Way) -> ndarray:
    coord = np.zeros(2)

    for node in way.nodes:
        coord += node_to_coord(node)

    return coord / len(way.nodes)


def relation_to_coord(relation: overpy.Relation) -> ndarray:
    coord = np.zeros(2)

    for member in relation.members:
        coord += to_coord(member.resolve())

    return coord / len(relation.members)


def to_coord(element: overpy.Element) -> ndarray:
    if type(element) is overpy.Relation:
        return relation_to_coord(element)
    elif type(element) is overpy.Way:
        return way_to_coord(element)
    elif type(element) is overpy.Node:
        return node_to_coord(element)
    else:
        raise TypeError("Unhandled element type")


if __name__ == "__main__":
    os.makedirs("points_of_interest", exist_ok=True)
    cities = {}
    with open("cities.json") as f:
        cities = json.load(f)

    api = overpy.Overpass(max_retry_count=5)

    for city, values in cities.items():
        print(f'Querying {city}')

        # This queries for a number of locations that could be considered reflective
        # of the color of a city.
        query_points_of_interest = """
            [out:json];
            (
                node[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});
                way[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});
                relation[tourism~"aquarium|artwork|attraction|gallery|museum|viewpoint"](area:{0});

                node[leisure~"garden|nature_reserve|park|stadium"](area:{0});
                way[leisure~"garden|nature_reserve|park|stadium"](area:{0});
                relation[leisure~"garden|nature_reserve|park|stadium"](area:{0});
            );
            (._;>;);
            out;
        """

        result = api.query(query_points_of_interest.format(values["area"]))

        points_of_interest = {}

        for elements in [result.nodes, result.ways, result.relations]:
            for element in elements:
                if "name" in element.tags:
                    coord = to_coord(element)
                    points_of_interest[element.id] = {
                        "name": element.tags["name"],
                        "lat": coord[0],
                        "lon": coord[1],
                    }

        with open(f"points_of_interest/{city}.json", "w") as f:
            json.dump(points_of_interest, f)
