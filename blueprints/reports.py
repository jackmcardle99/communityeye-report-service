import json
from flask import Blueprint, app, jsonify, make_response, request
import globals
from bson import ObjectId
from utils import delete_image, upload_image
from werkzeug.utils import secure_filename
import os
import time
from turfpy.measurement import boolean_point_in_polygon
from geojson import Point, Feature, Polygon
from shapely.geometry import Point,  Polygon, MultiPolygon
from validations import validate_fields
from shapely.geometry import Point, Polygon, MultiPolygon
from geojson import Feature
from turfpy.measurement import boolean_point_in_polygon
from shapely.geometry import Point, Polygon, MultiPolygon
from geojson import Feature
from turfpy.measurement import boolean_point_in_polygon
from shapely.geometry import Point, Polygon, MultiPolygon
from geojson import Feature
from turfpy.measurement import boolean_point_in_polygon


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


# @reports_bp.route('/api/v1/reports', methods=['POST'])
# def create_report():
#     if 'image' not in request.files:
#         # add logging
#         return make_response(jsonify({'Bad Request': 'No image was provided'}), 400)     
      
#     image = request.files['image']        
#     image_data = upload_image(image)
#     authority = determine_report_authority(image_data["geolocation"]) 
#     new_report = {
#         "user_id": 1,
#         "description": request.form['Description'],
#         "category": request.form['Category'],
#         "geolocation": {
#             "type": "Feature",
#             "geometry": {
#                 "type": "Point",
#                 "coordinates": [image_data['geolocation']['Lat'], image_data['geolocation']['Lon']]
#             }           
#         },
#         "authority": authority, # should be determined prior via a helper function to find out which public body is responsible
#         "image": image_data,
#         "resolved": False,
#         "created_at": int(time.time())
#     }

#     new_report_id = reports.insert_one(new_report).inserted_id
#     url = "http://localhost:5000/api/v1/reports/" + str(new_report_id)
#     return make_response(jsonify({'url': url}), 200)
@reports_bp.route('/api/v1/reports', methods=['POST'])
def create_report():
    print(request.form)
    required_fields = ['description', 'category']
    missing_fields = validate_fields(required_fields, request)
    if missing_fields:
        # logger.warning("Missing fields in registration data: %s", missing_fields)
        return make_response(
            jsonify({'Unprocessable Entity': 'Missing fields in JSON data.', 'missing_fields': missing_fields}), 422)
    if 'image' not in request.files:
        return make_response(jsonify({'Bad Request': 'No image was provided'}), 422)

    image = request.files['image']
    image_data = upload_image(image)
    print(image_data["geolocation"])
    # Check if image_data is None or if geolocation is missing
    if image_data.get("geolocation") is None:
        delete_image(image_data['url'])
        return make_response(jsonify({'Bad Request': 'Geolocation could not be determined'}), 400)

    if not is_within_boundaries(image_data["geolocation"]):
        delete_image(image_data['url'])
        return make_response(jsonify({'Bad Request': 'Geolocation is outside Northern Ireland'}), 400)

    authority = determine_report_authority(image_data["geolocation"])
    new_report = {
        # "user_id": request.form['userId'],
        "user_id": 1,
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


# def determine_report_authority(geolocation):
#     authorities_data = get_local_authorities()    
#     authority_name = ""
#     point = Feature(geometry=Point([geolocation['Lon'], geolocation['Lat']]))        
#     for authority in authorities_data:                            
#         polygon = Feature(geometry=Polygon(authority['area']['coordinates']))        
#         if boolean_point_in_polygon(point, polygon):                            
#             return authority['authority_name']




# def determine_report_authority(geolocation):
#     authorities_data = get_local_authorities()    
#     point = Feature(geometry=Point([geolocation['Lon'], geolocation['Lat']]))

#     for authority in authorities_data:
#         coords = authority['area']['coordinates']

#         # print("Authority coordinates structure:", type(coords), "Length:", len(coords))

#         try:
#             if isinstance(coords[0][0][0], list):  # MultiPolygon case (extra nesting)
#                 polygons = [Polygon(poly[0]) for poly in coords]  # Extract outer rings
#                 polygon = Feature(geometry=MultiPolygon(polygons))
#             else:  # Regular Polygon case
#                 polygon = Feature(geometry=Polygon(coords))  # No need to access `[0]`
            
#             # Check if the point is inside the authority boundary
#             if boolean_point_in_polygon(point, polygon):
#                 return authority['authority_name']
        
#         except (IndexError, TypeError) as e:
#             print("Error creating Polygon/MultiPolygon:", e)
#             print("Problematic coordinates:", coords)  # Debugging

#     return None  # If no authority is found



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


    
    
# def is_within_boundaries(geolocation):
#     with open('data/geojsons/OSNI_Open_Data_-_Largescale_Boundaries_-_NI_Outline.geojson') as f:
#         geojson = json.load(f)

#     point = Point(geolocation['Lon'], geolocation['Lat'])
#     for feature in geojson['features']:
#         geometry = shape(feature['geometry'])

#         # Check if the geometry is a Polygon or MultiPolygon
#         if geometry.contains(point) or (geometry.geom_type == 'MultiPolygon' and any(poly.contains(point) for poly in geometry)):
#             return True
#     return False      




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
    

    
    