import json
from flask import Blueprint, jsonify, make_response, request
import globals
from bson import ObjectId
from utils import delete_image, upload_image
import time
from turfpy.measurement import boolean_point_in_polygon
from geojson import Point, Feature, Polygon
from validations import validate_fields
from shapely.geometry import Point, Polygon, MultiPolygon
from geojson import Feature

reports_bp = Blueprint('reports_bp', __name__)
reports = globals.db.reports
authorities = globals.db.authorities


@reports_bp.route('/api/v1/reports', methods=['GET'])
def get_reports():
    data = []
    for report in reports.find():
        report['_id'] = str(report['_id'])
        data.append(report)
    return make_response(jsonify(data))


@reports_bp.route('/api/v1/reports', methods=['POST'])
def create_report():
    required_fields = ['description', 'category']
    missing_fields = validate_fields(required_fields, request)
    if missing_fields:
        # logger.warning("Missing fields in registration data: %s", missing_fields)
        return make_response(
            jsonify({'Unprocessable Entity': 'Missing fields in JSON data.', 'missing_fields': missing_fields}), 422)
    if 'image' not in request.files:
        return make_response(jsonify({'Unprocessable Entity': 'No image was provided'}), 422)

    image = request.files['image']
    image_data = upload_image(image)
    # Check if image_data is None or if geolocation is missing
    if image_data.get("geolocation") is None:
        delete_image(image_data['url'])
        return make_response(jsonify({'Bad Request': 'Geolocation could not be determined'}), 400)

    if not is_within_boundaries(image_data["geolocation"]):
        delete_image(image_data['url'])
        return make_response(jsonify({'Bad Request': 'Geolocation is outside Northern Ireland'}), 400)

    authority = determine_report_authority(image_data["geolocation"])
    new_report = {
        "user_id": int(request.form['userID']),
        "description": request.form['description'],
        "category": request.form['category'],
        "geolocation": {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [image_data['geolocation']['Lat'], image_data['geolocation']['Lon']]
            }
        },
        "authority": authority,
        "image": image_data,
        "resolved": False,
        "created_at": int(time.time())
    }

    new_report_id = reports.insert_one(new_report).inserted_id
    url = "http://localhost:5000/api/v1/reports/" + str(new_report_id)
    return make_response(jsonify({'url': url}), 200)


def determine_report_authority(geolocation):
    authorities_data = get_local_authorities()
    point = Feature(geometry=Point([geolocation['Lon'], geolocation['Lat']]))

    for authority in authorities_data:
        coords = authority['area']['coordinates']
        
        # If it's a MultiPolygon, extract the first set of coordinates
        if authority['area']['type'] == 'MultiPolygon':
            polygons = [Polygon(poly[0]) for poly in coords]  # Extract outer rings
        else:  # Regular Polygon
            polygons = [Polygon(coords[0])]  # FIXED: Extract the first set of coordinates

        for polygon in polygons:
            if boolean_point_in_polygon(point, Feature(geometry=polygon)):
                return authority['authority_name']

    return None


def is_within_boundaries(geolocation):
    with open('data/geojsons/OSNI_Open_Data_-_Largescale_Boundaries_-_NI_Outline.geojson') as f:
        geojson = json.load(f)

    point = Point(geolocation['Lon'], geolocation['Lat'])
    print(f"Checking point: {point}")

    for feature in geojson['features']:
        geometry = feature['geometry']
        print(f"Checking feature type: {geometry['type']}")

        if geometry['type'] == 'Polygon':
            polygon = Polygon(geometry['coordinates'][0])
            print(f"Polygon bounds: {polygon.bounds}")  # Debugging
            if polygon.contains(point) or point.within(polygon):  
                print("Point is within a Polygon.")
                return True

        elif geometry['type'] == 'MultiPolygon':
            multipolygon = MultiPolygon([Polygon(coords[0]) for coords in geometry['coordinates']])
            print(f"MultiPolygon bounds: {multipolygon.bounds}")  # Debugging
            if multipolygon.contains(point) or point.within(multipolygon):
                print("Point is within a MultiPolygon.")
                return True

    print("Point is not within any boundaries.")
    return False

        
def get_local_authorities():
    authorities_data = []
    for authority in authorities.find():
        authority['_id'] = str(authority['_id'])
        authorities_data.append(authority) 
    return authorities_data
    

    
    