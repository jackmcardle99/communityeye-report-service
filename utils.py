from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from pillow_heif import register_heif_opener
import os
import logging
import globals as g


def upload_image(image):
    # save upload
    image_name = image.filename
    image_path = image.save(os.path.join(g.UPLOAD_FOLDER, image_name))
    
    # if image type is heic then convert
    if image.content_type == 'image/heic':
        old_path = g.UPLOAD_FOLDER + image_name
        image_name = str(image_name).replace('HEIC', 'jpg')
        new_path = g.UPLOAD_FOLDER + image_name
        convert_image_heic(old_path, new_path, 100)
        image_path = new_path
    

    converted_image = Image.open(image_path)
    image_data = {
        "url": image_path,
        "image_name": image_name,
        "dimensions": converted_image.size,
        "geolocation": get_image_geolocation(image_path),
        "file_size": os.path.getsize(image_path)
    }
    
    return image_data
   

def get_image_geolocation(image_path):
    GPSINFO_TAG = next(
        tag for tag, name in TAGS.items() if name == "GPSInfo"
    )
    image = Image.open(image_path)
    exifdata = image.getexif()
    gpsinfo = exifdata.get_ifd(GPSINFO_TAG)
    
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
