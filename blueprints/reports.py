from flask import Blueprint, app, jsonify, make_response, request
import globals
from bson import ObjectId
from utils import upload_image
from werkzeug.utils import secure_filename
import os
import time
from turfpy.measurement import boolean_point_in_polygon
from geojson import Point, Feature, Polygon


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
    if 'image' not in request.files:
        # add logging
        return make_response(jsonify({'Bad Request': 'No image was provided'}), 400)     
      
    image = request.files['image']        
    image_data = upload_image(image)
    authority = determine_report_authority(image_data["geolocation"]) 
    new_report = {
        "user_id": 1,
        "description": request.form['Description'],
        "category": request.form['Category'],
        "geolocation": {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [image_data['geolocation']['Lat'], image_data['geolocation']['Lon']]
            }           
        },
        "authority": authority, # should be determined prior via a helper function to find out which public body is responsible
        "image": image_data,
        "resolved": False,
        "created_at": int(time.time())
    }

    new_report_id = reports.insert_one(new_report).inserted_id
    url = "http://localhost:5000/api/v1/reports/" + str(new_report_id)
    return make_response(jsonify({'url': url}), 200)


def determine_report_authority(geolocation):
    authorities_data = get_local_authorities()    
    authority_name = ""
    point = Feature(geometry=Point([geolocation['Lon'], geolocation['Lat']]))        
    for authority in authorities_data:                            
        polygon = Feature(geometry=Polygon(authority['area']['coordinates']))        
        if boolean_point_in_polygon(point, polygon):                            
            return authority['authority_name']
    
    
         
        
def get_local_authorities():
    authorities_data = []
    for authority in authorities.find():
        authority['_id'] = str(authority['_id'])
        authorities_data.append(authority) 
    return authorities_data
    

    
    