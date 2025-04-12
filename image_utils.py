"""
File: image_utils.py
Author: Jack McArdle

This file is part of CommunityEye.

Email: mcardle-j9@ulster.ac.uk
B-No: B00733578
"""

import logging
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import io
from azure.storage.blob import BlobServiceClient
import config
from typing import Dict, Optional, Tuple, Union


logging.basicConfig(level=logging.INFO)


blob_service_client = BlobServiceClient(
    account_url=f"https://{config.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net/",
    credential=config.AZURE_STORAGE_SAS,
)
container_client = blob_service_client.get_container_client(
    config.AZURE_STORAGE_CONTAINER
)


def upload_image(
    image,
) -> Union[
    Dict[str, Union[str, Tuple[int, int], Optional[Dict[str, float]], int]],
    Tuple[Dict[str, str], int],
]:
    """
    Upload an image to Azure Blob Storage.

    Args:
        image: The image file to be uploaded.

    Returns:
        Union[Dict[str, Union[str, Tuple[int, int], Optional[Dict[str, float]], int]], Tuple[Dict[str, str], int]]:
        A dictionary containing image metadata including URL, name, dimensions, geolocation, and file size,
        or a tuple with an error message and status code.
    """
    image_name = image.filename

    # convert HEIC to JPEG if necessary, iphones capture HEIC images which can cause issues
    if image.content_type == "image/heic":
        logging.info("Converting HEIC image to JPEG.")
        image_name = image_name.replace(".heic", ".jpg")
        image = convert_image_heic(image)

    try:
        converted_image = Image.open(image)
        converted_image.load()
    except Exception as e:
        logging.error(f"Error opening image: {e}")
        return {"error": str(e)}, 500

    blob_client = container_client.get_blob_client(image_name)
    image.seek(0)
    blob_client.upload_blob(image, overwrite=True)
    logging.info(
        f"Image {image_name} uploaded successfully to Azure Blob Storage."
    )

    image_data = {
        "url": blob_client.url,
        "image_name": image_name,
        "dimensions": converted_image.size,
        "geolocation": get_image_geolocation(image),
        "file_size": image.tell(),
    }

    return image_data


def delete_image(image_name: str) -> bool:
    """
    Delete an image from Azure Blob Storage.

    Args:
        image_name (str): The name of the image to be deleted.

    Returns:
        bool: True if the image was deleted successfully, False otherwise.
    """
    try:
        blob_client = container_client.get_blob_client(image_name)
        if blob_client.exists():
            blob_client.delete_blob()
            logging.info(
                f"Image {image_name} deleted successfully from Azure Blob Storage."
            )
            return True
        else:
            logging.warning(
                f"Image {image_name} not found in Azure Blob Storage."
            )
            return False
    except Exception as e:
        logging.error(f"Error deleting image from Azure Blob Storage: {e}")
        return False


def get_image_geolocation(image) -> Optional[Dict[str, float]]:
    """
    Extract geolocation data from an image's EXIF metadata.

    Args:
        image: The image file from which to extract geolocation data.

    Returns:
        Optional[Dict[str, float]]: A dictionary containing latitude and longitude if available, otherwise None.
    """
    GPSINFO_TAG = next(tag for tag, name in TAGS.items() if name == "GPSInfo")
    image.seek(0)
    image = Image.open(image)
    exifdata = image.getexif()
    if not exifdata:
        logging.warning("No EXIF data found in the image.")
        return None

    gpsinfo = exifdata.get_ifd(GPSINFO_TAG)
    if not gpsinfo:
        logging.warning("No GPS info found in the EXIF data.")
        return None

    return {
        "Lat": decimal_coords(gpsinfo[2], gpsinfo[1]),
        "Lon": decimal_coords(gpsinfo[4], gpsinfo[3]),
    }


def decimal_coords(coords: Tuple[float, float, float], ref: str) -> float:
    """
    Convert GPS coordinates from degrees, minutes, seconds format to decimal degrees.

    Args:
        coords (Tuple[float, float, float]): A tuple containing the GPS coordinates in (degrees, minutes, seconds) format.
        ref (str): The reference direction ('N', 'S', 'E', 'W').

    Returns:
        float: The GPS coordinates in decimal degrees.
    """
    decimal_degrees = (
        float(coords[0]) + float(coords[1]) / 60 + float(coords[2]) / 3600
    )
    if ref == "S" or ref == "W":
        decimal_degrees = -1 * decimal_degrees
    return round(decimal_degrees, 6)


def convert_image_heic(heic_image) -> Optional[io.BytesIO]:
    """
    Convert a HEIC image to JPEG format.

    Args:
        heic_image: The HEIC image file to be converted.

    Returns:
        Optional[io.BytesIO]: The converted JPEG image as a byte stream, or None if conversion fails.
    """
    register_heif_opener()
    try:
        image = Image.open(heic_image)
        exif_data = image.info.get("exif")
        jpg_image = io.BytesIO()
        image.save(jpg_image, "JPEG", quality=100, exif=exif_data)
        jpg_image.seek(0)
        return jpg_image
    except (UnidentifiedImageError, FileNotFoundError, OSError) as e:
        logging.error(f"Error converting HEIC image: {e}")
        return None
