from pymongo import MongoClient


client = MongoClient("mongodb://127.0.0.1:27017")
db = client.communityeye_reports
secret_key = ''
UPLOAD_FOLDER = 'media/'