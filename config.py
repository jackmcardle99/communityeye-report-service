from dotenv import load_dotenv
from pymongo import MongoClient
import os


load_dotenv()


# MongoDB config
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")
MONGO_COLLECTION_REPORTS = os.getenv("MONGO_COLLECTION_REPORTS")
MONGO_COLLECTION_AUTHORITIES = os.getenv("MONGO_COLLECTION_AUTHORITIES")
MONGO_COLLECTION_UPVOTES = os.getenv("MONGO_COLLECTION_UPVOTES")
CLIENT = MongoClient(MONGO_URI)
DB = CLIENT[MONGO_DB_NAME]


# Flask config
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
FLASK_DEBUG = os.getenv("FLASK_DEBUG")
FLASK_HOST = os.getenv("FLASK_HOST")
FLASK_PORT = int(os.getenv("FLASK_PORT"))

# Azure Blob Storage config
AZURE_STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")
AZURE_STORAGE_SAS = os.getenv("AZURE_STORAGE_SAS")
