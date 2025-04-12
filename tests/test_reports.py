"""
File: test_reports.py
Author: Jack McArdle

This file is part of CommunityEye.

Email: mcardle-j9@ulster.ac.uk
B-No: B00733578
"""

import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from blueprints.reports.reports import reports_bp
import jwt
from config import FLASK_SECRET_KEY, MONGO_COLLECTION_REPORTS, MONGO_COLLECTION_UPVOTES
import io
import datetime
from bson import ObjectId

MOCK_USER_ID = 999
MOCK_JWT_TOKEN = jwt.encode({'user_id': MOCK_USER_ID}, FLASK_SECRET_KEY, algorithm='HS256')

MOCK_REPORT_ID = ObjectId('60b8d2a4b8d2a4bad2a4b8d2')
MOCK_REPORT_DATA = {
    '_id': MOCK_REPORT_ID,
    'authority': 'Department for Infrastructure - Eastern Division',
    'category': 'Sample Category',
    "created_at": datetime.datetime.now(),
    'description': 'Sample Report',
    'geolocation': {
        "geometry": {
            "coordinates": [54.560192, -5.988161],
            "type": "Point"
        },
        "type": "Feature"
    },
    'user_id': MOCK_USER_ID,
    "image": {
        "dimensions": [4032, 3024],
        "file_size": 4353,
        "geolocation": {"Lat": 54.560192, "Lon": -5.988161},
        "image_name": "test_img.jpg",
        "url": "www.test.com/test_image"
    },
    'resolved': False,
    'upvote_count': 0
}

class ReportsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(reports_bp)
        self.client = self.app.test_client()

    # /api/v1/reports [GET]
    @patch('blueprints.reports.reports.DB')
    def test_get_reports_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.find.return_value = iter([MOCK_REPORT_DATA])

        response = self.client.get('/api/v1/reports', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertIn('description', response.json[0])

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_failure(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find.side_effect = Exception("DB Error")
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.get('/api/v1/reports', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 500)

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_empty(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find.return_value = iter([])
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.get('/api/v1/reports', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

    # /api/v1/reports [POST]
    @patch('blueprints.reports.reports.DB')
    @patch('blueprints.reports.reports.upload_image')
    def test_create_report_success(self, mock_upload_image, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.insert_one.return_value.inserted_id = MOCK_REPORT_ID

        mock_upload_image.return_value = {"geolocation": {"Lat": 54.6, "Lon": -5.9}, "image_name": "test_image"}

        mock_image = io.BytesIO(b"fake image bytes")
        mock_image.filename = 'test_image.jpg'

        data = {
            'description': 'Sample Report',
            'category': 'Potholes',
            'userID': '123',
            'image': (mock_image, 'test_image.jpg')
        }

        response = self.client.post('/api/v1/reports', data=data, headers={'x-access-token': MOCK_JWT_TOKEN}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 201)
        self.assertIn('url', response.json)

    def test_create_report_missing_fields(self):
        data = {
            'category': 'Potholes',
            'userID': '123'
        }
        response = self.client.post('/api/v1/reports', data=data, headers={'x-access-token': MOCK_JWT_TOKEN}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 422)

    @patch('blueprints.reports.reports.upload_image')
    def test_create_report_out_of_bounds(self, mock_upload_image):
        mock_upload_image.return_value = {"geolocation": {"Lat": 0, "Lon": 0}, "image_name": "bad_image"}
        mock_image = io.BytesIO(b"fake image")
        mock_image.filename = 'test.jpg'

        data = {
            'description': 'Sample Report',
            'category': 'Potholes',
            'userID': '123',
            'image': (mock_image, 'test.jpg')
        }

        with patch('blueprints.reports.reports.is_within_boundaries', return_value=False):
            response = self.client.post('/api/v1/reports', data=data, headers={'x-access-token': MOCK_JWT_TOKEN}, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 400)

    # /api/v1/reports/user/<id> [GET]
    @patch('blueprints.reports.reports.DB')
    def test_get_reports_by_user_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.find.return_value = [MOCK_REPORT_DATA]
        response = self.client.get(f'/api/v1/reports/user/{MOCK_USER_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_by_user_failure(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find.side_effect = Exception("DB error")
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        response = self.client.get(f'/api/v1/reports/user/{MOCK_USER_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 500)

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_by_user_empty(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find.return_value = []
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        response = self.client.get(f'/api/v1/reports/user/{MOCK_USER_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, [])

# /api/v1/reports/<report_id> [DELETE]
    @patch('blueprints.reports.reports.DB')
    @patch('blueprints.reports.reports.delete_image')
    def test_delete_report_success(self, mock_delete_image, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.find_one.return_value = MOCK_REPORT_DATA
        mock_delete_image.return_value = True
        mock_collection.delete_one.return_value.deleted_count = 1

        response = self.client.delete(f'/api/v1/reports/{MOCK_REPORT_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 204)

    @patch('blueprints.reports.reports.DB')
    def test_delete_report_not_found(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.delete(f'/api/v1/reports/{MOCK_REPORT_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 404)

    @patch('blueprints.reports.reports.DB')
    @patch('blueprints.reports.reports.delete_image')
    def test_delete_report_image_delete_failure(self, mock_delete_image, mock_db):
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = MOCK_REPORT_DATA
        mock_delete_image.return_value = False
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.delete(f'/api/v1/reports/{MOCK_REPORT_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 500)

    # /api/v1/reports/<report_id>/resolve [POST]
    @patch('blueprints.reports.reports.DB')
    def test_resolve_report_success(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = MOCK_REPORT_DATA
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/resolve', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Success', response.json)

    @patch('blueprints.reports.reports.DB')
    def test_resolve_report_not_found(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find_one.return_value = None
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/resolve', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 404)

    @patch('blueprints.reports.reports.DB')
    def test_resolve_report_db_error(self, mock_db):
        mock_collection = MagicMock()
        mock_collection.find_one.side_effect = Exception("DB error")
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/resolve', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 500)

    # /api/v1/reports/<report_id>/upvote [POST]
    @patch('blueprints.reports.reports.DB')
    def test_upvote_report_success(self, mock_db):
        mock_upvotes = MagicMock()
        mock_reports = MagicMock()
        mock_upvotes.find_one.return_value = None
        mock_upvotes.insert_one.return_value = MagicMock()
        mock_reports.update_one.return_value.modified_count = 1

        mock_db[MONGO_COLLECTION_UPVOTES] = mock_upvotes
        mock_db[MONGO_COLLECTION_REPORTS] = mock_reports

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/upvote', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Success', response.json)

    @patch('blueprints.reports.reports.DB')
    def test_upvote_report_conflict(self, mock_db):
        mock_upvotes = MagicMock()
        mock_upvotes.find_one.return_value = True
        mock_db[MONGO_COLLECTION_UPVOTES] = mock_upvotes

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/upvote', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 409)

    @patch('blueprints.reports.reports.DB')
    def test_upvote_report_update_failure(self, mock_db):
        mock_upvotes = MagicMock()
        mock_reports = MagicMock()
        mock_upvotes.find_one.return_value = None
        mock_upvotes.insert_one.return_value = MagicMock()
        mock_reports.update_one.return_value.modified_count = 0

        mock_db[MONGO_COLLECTION_UPVOTES] = mock_upvotes
        mock_db[MONGO_COLLECTION_REPORTS] = mock_reports

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/upvote', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 500)
