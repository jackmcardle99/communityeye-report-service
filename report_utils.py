"""
File: report_utils.py
Author: Jack McArdle

This file is part of CommunityEye.

Email: mcardle-j9@ulster.ac.uk
B-No: B00733578
"""

import json
import logging
from typing import List, Dict, Optional
from geojson import Point, Polygon
from config import MONGO_COLLECTION_AUTHORITIES, DB
from shapely.geometry import Point, Polygon, MultiPolygon

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

authorities = DB[MONGO_COLLECTION_AUTHORITIES]


def is_within_boundaries(geolocation: Dict[str, float]) -> bool:
    """
    Check if a given geolocation is within the boundaries defined in a GeoJSON file.

    Parameters:
    - geolocation (Dict[str, float]): A dictionary containing 'Lon' and 'Lat' keys for longitude and latitude.

    Returns:
    - bool: True if the point is within any boundary, False otherwise.
    """
    try:
        with open(
            "data/geojsons/OSNI_Open_Data_-_Largescale_Boundaries_-_NI_Outline.geojson"
        ) as f:
            geojson = json.load(f)
    except Exception as e:
        logging.error(f"Error loading GeoJSON file: {e}")
        return False

    point = Point(geolocation["Lon"], geolocation["Lat"])
    logging.debug(f"Checking point: {point}")

    for feature in geojson["features"]:
        geometry = feature["geometry"]
        logging.debug(f"Checking feature type: {geometry['type']}")

        if geometry["type"] == "Polygon":
            polygon = Polygon(geometry["coordinates"][0])
            logging.debug(f"Polygon bounds: {polygon.bounds}")
            if polygon.contains(point) or point.within(polygon):
                logging.info("Point is within a Polygon.")
                return True

        elif geometry["type"] == "MultiPolygon":
            multipolygon = MultiPolygon(
                [Polygon(coords[0]) for coords in geometry["coordinates"]]
            )
            logging.debug(f"MultiPolygon bounds: {multipolygon.bounds}")
            if multipolygon.contains(point) or point.within(multipolygon):
                logging.info("Point is within a MultiPolygon.")
                return True

    logging.info("Point is not within any boundaries.")
    return False


def get_local_authorities() -> List[Dict]:
    """
    Retrieve all local authorities from the database.

    Returns:
    - List[Dict]: A list of dictionaries containing authority data.
    """
    authorities_data = []
    try:
        for authority in authorities.find():
            authority["_id"] = str(authority["_id"])
            authorities_data.append(authority)
    except Exception as e:
        logging.error(f"Error retrieving authorities: {e}")
    return authorities_data


def determine_report_authority(
    geolocation: Dict[str, float], category: str
) -> Optional[str]:
    """
    Determine the relevant authority for a given report based on geolocation and category.

    Parameters:
    - geolocation (Dict[str, float]): A dictionary containing 'Lon' and 'Lat' keys for longitude and latitude.
    - category (str): The category of the report.

    Returns:
    - Optional[str]: The name of the relevant authority, or None if no authority is found.
    """
    authorities_data = get_local_authorities()
    point = Point([geolocation["Lon"], geolocation["Lat"]])

    infrastructure_categories = {
        "Potholes",
        "Street lighting fault",
        "Obstructions",
        "Spillages",
        "Ironworks",
        "Traffic lights",
        "Crash barrier and guard-rail",
        "Signs or road markings",
    }

    council_categories = {
        "Street cleaning issue",
        "Missed bin collection",
        "Abandoned vehicle",
        "Dangerous structure or vacant building",
        "Pavement issue",
    }

    if category in infrastructure_categories:
        relevant_authority_type = "Department for Infrastructure"
    elif category in council_categories:
        relevant_authority_type = "Council"
    else:
        logging.warning(f"Category not recognized: {category}")
        return None

    filtered_authorities = [
        authority
        for authority in authorities_data
        if authority["authority_type"] == relevant_authority_type
    ]

    for authority in filtered_authorities:
        coords = authority["area"]["coordinates"]

        if authority["area"]["type"] == "MultiPolygon":
            polygons = [Polygon(poly[0]) for poly in coords]
        else:
            polygons = [Polygon(coords[0])]

        for polygon in polygons:
            if point.within(polygon):
                logging.info(f"Authority found: {authority['authority_name']}")
                return authority["authority_name"]

    logging.info("No relevant authority found.")
    return None


def send_email(
    authority_name: str, report_id: str, description: str, image_url: str
) -> None:
    """
    Simulate sending an email to the relevant authority.

    Parameters:
    - authority_name (str): The name of the authority to send the email to.
    - report_id (str): The ID of the report.
    - description (str): The description of the report.
    - image_url (str): The URL of the image associated with the report.
    """
    try:
        authority = authorities.find_one({"authority_name": authority_name})
        if not authority or "email_address" not in authority:
            logging.error(
                f"Email address not found for authority: {authority_name}"
            )
            return

        email_address = authority["email_address"]

        subject = "New Report Assigned"
        body = f"Report ID: {report_id}\nDescription: {description}\nImage URL: {image_url}"
        logging.info(f"Sending email to: {email_address}")
        logging.info(f"Subject: {subject}")
        logging.info(f"Body: {body}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
