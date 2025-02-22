import os
from pymongo import MongoClient

# Connect to MongoDB using environment variables
client = MongoClient(os.getenv('MONGO_URI'))
db = client[os.getenv('MONGO_DB_NAME')]
secret_key = os.getenv('SECRET_KEY')
