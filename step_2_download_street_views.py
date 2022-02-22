# Copyright 2021-2 Seth Pendergrass. See LICENSE.
#
# Given the processed output of step_1_get_points_of_interest.py, pull down the
# Street View images at each location and save them.
#
# WARNING: This requires a Google Cloud account and will incur costs when
# downloading. You'll need to set your API key and secret below.

import base64
import hashlib
import hmac
import json
import os
import time
from io import BytesIO

import requests
from PIL import Image


def send_request(url: str, params: dict) -> requests.Response:
    api_key = "API_KEY"
    secret = "SECRET"
    assert api_key != "API_KEY", "API Key and Secret required."

    params["key"] = api_key

    request = requests.Request("GET", url, params=params).prepare()

    dec_key = base64.urlsafe_b64decode(secret)
    sig = hmac.new(dec_key, str.encode(request.path_url), hashlib.sha1)
    enc_sig = base64.urlsafe_b64encode(sig.digest())
    request.prepare_url(url, params={**params, "signature": enc_sig})

    response = requests.Session().send(request)
    assert response.status_code == 200, "Request failed"
    return response


if __name__ == "__main__":
    cities = {}
    with open("cities.json") as f:
        cities = json.load(f)

    for city, values in cities.items():
        print(f"Downloading panos for {city}")

        with open(f"points_of_interest/{city}.json") as f:
            points = json.load(f)

        # Collect metadata (free)
        panos = {}
        for id, values in points.items():
            # Returned lat/lon is of street view, may not match input
            metadata = send_request(
                "https://maps.googleapis.com/maps/api/streetview/metadata",
                {"location": f'{values["lat"]},{values["lon"]}'},
            ).json()

            if metadata["status"] != "OK":
                print(f'Couldn\'t find {values["name"]}')
                continue

            print(f'Found {values["name"]}: {metadata["pano_id"]}')

            # Dedups street views via overwrite
            panos[metadata["pano_id"]] = {
                "osm_id": id,
                "name": values["name"],
                "lat": metadata["location"]["lat"],
                "lon": metadata["location"]["lng"],
            }

        os.makedirs("metadata", exist_ok=True)
        with open(f"metadata/{city}.json", "w") as f:
            json.dump(panos, f)

        # Collect panoramas ($)
        os.makedirs(f"panos/{city}", exist_ok=True)
        for id, values in panos.items():
            print(f'Downloading {id} ({values["name"]})')

            # Get all 4 sides of cube map, skipping top / bottom
            for heading in [0, 90, 180, 270]:
                # 640x640 is max size
                # TODO if doing this again, I'd add "source": "outdoor" to
                # filter out indoor shots
                result = send_request(
                    "https://maps.googleapis.com/maps/api/streetview",
                    {"pano": id, "size": "640x640", "heading": heading},
                )

                im = Image.open(BytesIO(result.content))
                im.save(f"panos/{city}/{id}_{heading}.jpg")

                # Rate limiting
                time.sleep(1 / 50)
