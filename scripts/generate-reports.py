import json
import time
import random
import string
from pymongo import MongoClient
from shapely.geometry import Point, Polygon, MultiPolygon

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['communityeye_reports']
reports = db['reports']
authorities = db['authorities']  # Assuming authorities data is stored in this collection

# Constants
IMAGE_URL_BASE = "https://communityeyeblob.blob.core.windows.net/reportimagestore/"
USER_ID = 1

def is_within_boundaries(geolocation):
    with open('data/geojsons/OSNI_Open_Data_-_Largescale_Boundaries_-_NI_Outline.geojson') as f:
        geojson = json.load(f)

    point = Point(geolocation['Lon'], geolocation['Lat'])

    for feature in geojson['features']:
        geometry = feature['geometry']

        if geometry['type'] == 'Polygon':
            polygon = Polygon(geometry['coordinates'][0])
            if polygon.contains(point) or point.within(polygon):
                return True

        elif geometry['type'] == 'MultiPolygon':
            multipolygon = MultiPolygon([Polygon(coords[0]) for coords in geometry['coordinates']])
            if multipolygon.contains(point) or point.within(multipolygon):
                return True

    return False

def create_report(description, category, geolocation):
    if not is_within_boundaries(geolocation):
        print("Geolocation is outside Northern Ireland")
        return

    authority = determine_report_authority(geolocation, category)
    if not authority:
        print("No relevant authority found for the given category and location")
        return

    image_info = generate_image_info(geolocation)

    new_report = {
        "user_id": USER_ID,
        "description": description,
        "category": category,
        "geolocation": {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [geolocation['Lat'], geolocation['Lon']]
            }
        },
        "authority": authority,
        "image": image_info,
        "resolved": False,
        "created_at": int(time.time())
    }

    new_report_id = reports.insert_one(new_report).inserted_id
    print(f"Report created with ID: {new_report_id}")

def determine_report_authority(geolocation, category):
    authorities_data = get_local_authorities()
    point = Point([geolocation['Lon'], geolocation['Lat']])

    # Define the categories each authority type handles
    infrastructure_categories = {
        "Potholes", "Street lighting fault", "Obstructions",
        "Spillages", "Ironworks", "Traffic lights",
        "Crash barrier and guard-rail", "Signs or road markings"
    }

    council_categories = {
        "Street cleaning issue", "Missed bin collection",
        "Abandoned vehicle", "Dangerous structure or vacant building",
        "Pavement issue"
    }

    # Determine the relevant authority type based on the category
    if category in infrastructure_categories:
        relevant_authority_type = "Department for Infrastructure"
    elif category in council_categories:
        relevant_authority_type = "Council"
    else:
        print("Category not recognized")
        return None

    # Filter authorities by the relevant type
    filtered_authorities = [
        authority for authority in authorities_data
        if authority['authority_type'] == relevant_authority_type
    ]

    # Check if the point is within any of the filtered authorities' areas
    for authority in filtered_authorities:
        coords = authority['area']['coordinates']
        print(f"Checking authority: {authority['authority_name']}")  # Debug

        # If it's a MultiPolygon, extract the first set of coordinates
        if authority['area']['type'] == 'MultiPolygon':
            polygons = [Polygon(poly[0]) for poly in coords]  # Extract outer rings
        else:  # Regular Polygon
            polygons = [Polygon(coords[0])]  # Extract the first set of coordinates

        for polygon in polygons:
            if point.within(polygon):
                print(f"Authority found: {authority['authority_name']}")  # Debug
                return authority['authority_name']

    print("No authority found for the given location")  # Debug
    return None

def get_local_authorities():
    authorities_data = []
    for authority in authorities.find():
        authority['_id'] = str(authority['_id'])
        authorities_data.append(authority)
    return authorities_data

def generate_random_geolocation():
    # Define the bounding box for Northern Ireland
    min_lat, max_lat = 54.0, 55.5
    min_lon, max_lon = -8.2, -5.4

    while True:
        lat = random.uniform(min_lat, max_lat)
        lon = random.uniform(min_lon, max_lon)
        geolocation = {"Lat": lat, "Lon": lon}

        if is_within_boundaries(geolocation):
            return geolocation

def generate_image_info(geolocation):
    dimensions = [4032, 3024]
    file_size = random.randint(1000, 5000)  # Random file size between 1KB and 5KB
    image_name = ''.join(random.choices(string.ascii_letters + string.digits, k=36)) + ".jpg"
    image_url = IMAGE_URL_BASE + image_name

    return {
        "dimensions": dimensions,
        "file_size": file_size,
        "geolocation": {"Lat": geolocation['Lat'], "Lon": geolocation['Lon']},  # Corrected format
        "image_name": image_name,
        "url": image_url
    }

def generate_reports(num_reports):
    categories = [
        "Potholes", "Street lighting fault", "Obstructions",
        "Spillages", "Ironworks", "Traffic lights",
        "Crash barrier and guard-rail", "Signs or road markings",
        "Street cleaning issue", "Missed bin collection",
        "Abandoned vehicle", "Dangerous structure or vacant building",
        "Pavement issue"
    ]

    for _ in range(num_reports):
        description = "Random report description"
        category = random.choice(categories)
        geolocation = generate_random_geolocation()
        create_report(description, category, geolocation)

# Example usage
num_reports_to_generate = 1000  # Specify the number of reports to generate
generate_reports(num_reports_to_generate)
