from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import os
import logging
import io
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import globals as g
from dotenv import load_dotenv

load_dotenv() 
# Initialize Azure Blob Storage client
account = os.getenv('AZURE_STORAGE_ACCOUNT')
sas_token = os.getenv('AZURE_STORAGE_SAS')
container_name = os.getenv('AZURE_STORAGE_CONTAINER')
blob_service_client = BlobServiceClient(account_url=f"https://{account}.blob.core.windows.net/", credential=sas_token)
container_client = blob_service_client.get_container_client(container_name)

def upload_image(image):
    image_name = image.filename

    # Convert HEIC to JPEG if necessary
    if image.content_type == 'image/heic':
        image_name = image_name.replace('.heic', '.jpg')
        image = convert_image_heic(image)

    # Open the image using PIL
    try:
        converted_image = Image.open(image)
        converted_image.load()
    except Exception as e:
        return {"error": str(e)}, 500

    # Upload the image to Azure Blob Storage
    blob_client = container_client.get_blob_client(image_name)
    image.seek(0)  # Ensure the file pointer is at the beginning
    blob_client.upload_blob(image, overwrite=True)

    # Get image metadata
    image_data = {
        "url": blob_client.url,
        "image_name": image_name,
        "dimensions": converted_image.size,
        "geolocation": get_image_geolocation(image),
        "file_size": image.tell()  # Get the size of the image in bytes
    }

    return image_data

# def delete_image(image_name):
#     """Delete the image from Azure Blob Storage."""
#     try:
#         blob_client = container_client.get_blob_client(image_name)
#         if blob_client.exists():
#             blob_client.delete_blob()
#             print(f"Image {image_name} deleted successfully from Azure Blob Storage.")
#         else:
#             print(f"Image {image_name} not found in Azure Blob Storage.")
#     except Exception as e:
#         print(f"Error deleting image from Azure Blob Storage: {e}")
def delete_image(image_name):
    """Delete the image from Azure Blob Storage and return success status."""
    try:
        blob_client = container_client.get_blob_client(image_name)
        if blob_client.exists():
            blob_client.delete_blob()
            print(f"Image {image_name} deleted successfully from Azure Blob Storage.")
            return True
        else:
            print(f"Image {image_name} not found in Azure Blob Storage.")
            return False
    except Exception as e:
        print(f"Error deleting image from Azure Blob Storage: {e}")
        return False

def get_image_geolocation(image):
    GPSINFO_TAG = next(tag for tag, name in TAGS.items() if name == "GPSInfo")
    image.seek(0)  # Ensure the file pointer is at the beginning
    image = Image.open(image)
    exifdata = image.getexif()
    if not exifdata:
        return None

    gpsinfo = exifdata.get_ifd(GPSINFO_TAG)
    if not gpsinfo:
        return None

    return {
        'Lat': decimal_coords(gpsinfo[2], gpsinfo[1]),
        'Lon': decimal_coords(gpsinfo[4], gpsinfo[3])
    }

def decimal_coords(coords, ref):
    decimal_degrees = float(coords[0]) + float(coords[1]) / 60 + float(coords[2]) / 3600
    if ref == "S" or ref =='W' :
        decimal_degrees = -1 * decimal_degrees
    return round(decimal_degrees, 6)

def convert_image_heic(heic_image):
    register_heif_opener()
    try:
        image = Image.open(heic_image)
        exif_data = image.info.get("exif")
        jpg_image = io.BytesIO()
        image.save(jpg_image, "JPEG", quality=100, exif=exif_data)
        jpg_image.seek(0)  # Ensure the file pointer is at the beginning
        return jpg_image
    except (UnidentifiedImageError, FileNotFoundError, OSError) as e:
        logging.error("Error converting HEIC image: %s", e)
        return None
