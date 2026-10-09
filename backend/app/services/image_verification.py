import os
import hashlib
import json
from io import BytesIO
from datetime import datetime
from PIL import Image, ExifTags
import imagehash
from sqlalchemy.orm import Session
from app.db.models import Report

def get_exif_data(image: Image.Image):
    exif_data = {}
    if hasattr(image, '_getexif') and image._getexif():
        for tag, value in image._getexif().items():
            decoded = ExifTags.TAGS.get(tag, tag)
            exif_data[decoded] = value
    return exif_data

def get_gps_info(exif_data):
    gps_info = {}
    if 'GPSInfo' in exif_data:
        for key in exif_data['GPSInfo'].keys():
            decode = ExifTags.GPSTAGS.get(key, key)
            gps_info[decode] = exif_data['GPSInfo'][key]
    return gps_info

def convert_to_degrees(value):
    d0 = value[0][0] / value[0][1] if isinstance(value[0], tuple) else float(value[0])
    d1 = value[1][0] / value[1][1] if isinstance(value[1], tuple) else float(value[1])
    d2 = value[2][0] / value[2][1] if isinstance(value[2], tuple) else float(value[2])
    return d0 + (d1 / 60.0) + (d2 / 3600.0)

def get_lat_lon(exif_data):
    gps_info = get_gps_info(exif_data)
    if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
        lat = convert_to_degrees(gps_info['GPSLatitude'])
        lon = convert_to_degrees(gps_info['GPSLongitude'])
        if gps_info.get('GPSLatitudeRef') != 'N': lat = 0 - lat
        if gps_info.get('GPSLongitudeRef') != 'E': lon = 0 - lon
        return lat, lon
    return None, None

def calculate_hashes(image_bytes: bytes, pil_img: Image.Image):
    sha256 = hashlib.sha256(image_bytes).hexdigest()
    p_hash = str(imagehash.phash(pil_img))
    return sha256, p_hash

def verify_image_evidence(db: Session, image_bytes: bytes, submitted_lat: float, submitted_lon: float):
    results = {
        "status": "UNKNOWN",
        "trust_score": 0.0,
        "completed_checks": [],
        "missing_evidence": [],
        "detected_conflicts": [],
        "explanation": [],
        "sha256_hash": None,
        "perceptual_hash": None,
        "corroboration": False
    }

    try:
        pil_img = Image.open(BytesIO(image_bytes))
        pil_img.verify() # verify it's an image
        pil_img = Image.open(BytesIO(image_bytes)) # reopen after verify
    except Exception as e:
        results["status"] = "REJECTED_INVALID_FORMAT"
        results["explanation"].append("File is not a valid image.")
        return results

    sha256, p_hash = calculate_hashes(image_bytes, pil_img)
    results["sha256_hash"] = sha256
    results["perceptual_hash"] = p_hash

    # Check database for exact duplicates
    exact_duplicate = db.query(Report).filter(Report.sha256_hash == sha256).first()
    if exact_duplicate:
        results["status"] = "REJECTED_DUPLICATE"
        results["detected_conflicts"].append(f"Exact duplicate of report #{exact_duplicate.id}")
        results["explanation"].append("This image has been submitted before.")
        return results

    results["completed_checks"].append("Format Validation")
    results["completed_checks"].append("Hash Generation")

    # Metadata extraction
    exif_data = get_exif_data(pil_img)
    timestamp = exif_data.get('DateTimeOriginal') or exif_data.get('DateTime')
    
    if timestamp:
        results["completed_checks"].append("EXIF Timestamp Found")
    else:
        results["missing_evidence"].append("No original timestamp in EXIF")
        results["explanation"].append("Cannot verify age precisely.")

    exif_lat, exif_lon = get_lat_lon(exif_data)
    location_match_score = 0.0
    if exif_lat and exif_lon:
        results["completed_checks"].append("EXIF GPS Found")
        # Very rough bounding box check
        lat_diff = abs(exif_lat - submitted_lat)
        lon_diff = abs(exif_lon - submitted_lon)
        if lat_diff < 0.01 and lon_diff < 0.01:
            location_match_score = 0.4
            results["explanation"].append("Image GPS matches reported location.")
        else:
            results["detected_conflicts"].append("GPS coordinates do not match submission.")
            location_match_score = -0.2
    else:
        results["missing_evidence"].append("No GPS coordinates in EXIF")
        results["explanation"].append("Location cannot be independently verified from image metadata.")
        location_match_score = 0.0

    # Trust Score calculation (arbitrary weighting)
    # Starts at 0.5 if it is a valid image without conflicts
    base_score = 0.5
    trust_score = base_score + location_match_score
    
    if "No original timestamp in EXIF" in results["missing_evidence"] and "No GPS coordinates in EXIF" in results["missing_evidence"]:
        results["explanation"].append("Lacking metadata. Relying on visual context and corroboration.")
        trust_score -= 0.1

    if trust_score < 0: trust_score = 0.0
    if trust_score > 1.0: trust_score = 1.0

    results["trust_score"] = round(trust_score, 2)
    
    if len(results["detected_conflicts"]) > 0:
        results["status"] = "PENDING_ADDITIONAL_EVIDENCE"
    else:
        results["status"] = "VERIFIED_PARTIAL" if trust_score < 0.8 else "VERIFIED"

    return results
