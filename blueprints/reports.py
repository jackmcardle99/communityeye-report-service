from flask import Blueprint, app, jsonify, make_response, request
import globals
from bson import ObjectId
from utils import upload_image, determine_local_authority
from werkzeug.utils import secure_filename
import os
import time


reports_bp = Blueprint('reports_bp', __name__)
reports = globals.db.reports


@reports_bp.route('/api/v1/reports', methods=['POST'])
def create_report():
    if 'image' not in request.files:
        # add logging
        return make_response(jsonify({'Bad Request': 'No image was provided'}), 400)        
    image = request.files['image']        
    image_data = upload_image(image)
    authority = determine_local_authority(image_data["geolocation"])
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


def get_local_authorities(geolocation):
    print("do stuff")
    new

    
    