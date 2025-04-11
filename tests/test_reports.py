import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from blueprints.reports.reports import reports_bp
import jwt
from config import FLASK_SECRET_KEY, MONGO_COLLECTION_REPORTS, MONGO_COLLECTION_UPVOTES
import io
import datetime
from bson import ObjectId

# Mock JWT token
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
                "coordinates": [
                    54.560192,
                    -5.988161
                ],
                "type": "Point"
            },
            "type": "Feature"
        },
    'user_id': MOCK_USER_ID,
    "image": {
            "dimensions": [
                4032,
                3024
            ],
            "file_size": 4353,
            "geolocation": {
                "Lat": 54.560192,
                "Lon": -5.988161
            },
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

    @patch('blueprints.reports.reports.DB')
    @patch('blueprints.reports.reports.upload_image')
    def test_create_report_success(self, mock_upload_image, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.insert_one.return_value.inserted_id = MOCK_REPORT_ID

        # Mock image upload
        mock_upload_image.return_value = {"geolocation": {"Lat": 54.6, "Lon": -5.9}, "image_name": "test_image"}

        # Create a mock image file
        mock_image = io.BytesIO(b"fake image bytes")
        mock_image.filename = 'test_image.jpg'

        # Include the mock image in the request data
        data = {
            'description': 'Sample Report',
            'category': 'Potholes',
            'userID': '123',
            'image': (mock_image, 'test_image.jpg')
        }

        response = self.client.post('/api/v1/reports', data=data, headers={'x-access-token': MOCK_JWT_TOKEN}, content_type='multipart/form-data')
        self.assertEqual(response.status_code, 201)
        self.assertIn('url', response.json)

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        mock_collection.find.return_value = iter([MOCK_REPORT_DATA])

        response = self.client.get('/api/v1/reports', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertIn('description', response.json[0])

    @patch('blueprints.reports.reports.DB')
    def test_get_reports_by_user_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        # Mock the response to return a list containing the mock report data
        mock_collection.find.return_value = [MOCK_REPORT_DATA]  # List of reports

        # Make the request
        response = self.client.get(f'/api/v1/reports/user/{MOCK_USER_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})

        # Assert correct response
        self.assertEqual(response.status_code, 200)

    @patch('blueprints.reports.reports.DB')
    @patch('blueprints.reports.reports.delete_image')  # Mock delete image function
    def test_delete_report_success(self, mock_delete_image, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        # Mock finding the report
        mock_collection.find_one.return_value = MOCK_REPORT_DATA  # Simulate the report exists

        # Mock successful deletion
        mock_collection.delete_one.return_value.deleted_count = 1  # Simulate deletion success
        mock_delete_image.return_value = True  # Simulate successful image deletion

        # Perform the delete request
        response = self.client.delete(f'/api/v1/reports/{MOCK_REPORT_ID}', headers={'x-access-token': MOCK_JWT_TOKEN})

        # Assert the response
        self.assertEqual(response.status_code, 204)  # Expect successful deletion


    @patch('blueprints.reports.reports.DB')
    def test_resolve_report_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_REPORTS] = mock_collection
        # Mock the report data
        mock_collection.find_one.return_value = MOCK_REPORT_DATA

        # Simulate resolving the report
        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/resolve', headers={'x-access-token': MOCK_JWT_TOKEN})

        # Assert successful resolution
        self.assertEqual(response.status_code, 200)
        self.assertIn('Success', response.json)  # Check if the success message is returned

    @patch('blueprints.reports.reports.DB')
    def test_upvote_report_success(self, mock_db):
        mock_collection = MagicMock()
        mock_db[MONGO_COLLECTION_UPVOTES] = mock_collection
        mock_collection.find_one.return_value = MOCK_REPORT_DATA
        mock_db[MONGO_COLLECTION_UPVOTES] = MagicMock()
        mock_db[MONGO_COLLECTION_UPVOTES].find_one.return_value = None
        mock_db[MONGO_COLLECTION_UPVOTES].insert_one.return_value = MagicMock()

        response = self.client.post(f'/api/v1/reports/{MOCK_REPORT_ID}/upvote', headers={'x-access-token': MOCK_JWT_TOKEN})
        self.assertEqual(response.status_code, 200)
        self.assertIn('Success', response.json)

if __name__ == '__main__':
    unittest.main()
