from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import os
import logging
import globals as g

def upload_image(image):
    
    # Save the uploaded image
    image_name = image.filename
    image_path = os.path.join(g.UPLOAD_FOLDER, image_name)  # Construct the full file path
    image.save(image_path)  # Save the image to the disk
    
    # If the image is HEIC, convert it
    if image.content_type == 'image/heic':
        old_path = image_path  # The path where the HEIC image is saved
        image_name = str(image_name).replace('HEIC', 'jpg')  # Change extension to jpg
        new_path = os.path.join(g.UPLOAD_FOLDER, image_name)  # New file path for the converted image
        convert_image_heic(old_path, new_path, 100)  # Convert to jpg
        image_path = new_path  # Update the image path to the new jpg file

    # Open the image using PIL
    try:
        converted_image = Image.open(image_path)  # Open the image from the saved path
        converted_image.load()  # Ensure the image is loaded into memory
    except Exception as e:
        return {"error": str(e)}, 500  # Return an error if the image can't be opened

    # Get image metadata
    image_data = {
        "url": image_path,
        "image_name": image_name,
        "dimensions": converted_image.size,  # Width and height
        "geolocation": get_image_geolocation(image_path),  # Custom function to get image geolocation
        "file_size": os.path.getsize(image_path)  # File size in bytes
    }
    
    return image_data  # Return the image data as a response

def delete_image(image_path):
    """Helper function to delete the image from the server."""
    try:
        if os.path.exists(image_path):
            os.remove(image_path)  # Delete the file
            print(f"Image {image_path} deleted successfully.")
        else:
            print(f"Image {image_path} not found.")
    except Exception as e:
        print(f"Error deleting image: {e}")

   

# def get_image_geolocation(image_path):
#     GPSINFO_TAG = next(
#         tag for tag, name in TAGS.items() if name == "GPSInfo"
#     )
#     image = Image.open(image_path)
#     exifdata = image.getexif()
#     gpsinfo = exifdata.get_ifd(GPSINFO_TAG)
    
#     return {
#         'Lat': decimal_coords(gpsinfo[2], gpsinfo[1]),
#         'Lon': decimal_coords(gpsinfo[4], gpsinfo[3])
#     }
def get_image_geolocation(image_path):
    GPSINFO_TAG = next(tag for tag, name in TAGS.items() if name == "GPSInfo")
    image = Image.open(image_path)
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


# iPhone creates heic images, so they need to be converted first
def convert_image_heic(heic_path, jpg_path, output_quality) -> tuple:
    register_heif_opener()
    try:
        with Image.open(heic_path) as image:
            # Automatically handle and preserve EXIF metadata
            exif_data = image.info.get("exif")
            image.save(jpg_path, "JPEG", quality=output_quality, exif=exif_data)
            # Preserve the original access and modification timestamps
            heic_stat = os.stat(heic_path)
            os.utime(jpg_path, (heic_stat.st_atime, heic_stat.st_mtime))
            return heic_path, True  # Successful conversion
    except (UnidentifiedImageError, FileNotFoundError, OSError) as e:
        logging.error("Error converting '%s': %s", heic_path, e)
        return heic_path, False  # Failed conversion
