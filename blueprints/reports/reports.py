"""
File: reports.py
Author: Jack McArdle

This file is part of CommunityEye.

Email: mcardle-j9@ulster.ac.uk
B-No: B00733578
"""

import logging
from bson import ObjectId
from flask import Blueprint, jsonify, make_response, request, g
from config import (
    MONGO_COLLECTION_REPORTS,
    MONGO_COLLECTION_AUTHORITIES,
    MONGO_COLLECTION_UPVOTES,
    DB
)
from image_utils import delete_image, upload_image
import time
from report_utils import (
    is_within_boundaries,
    determine_report_authority,
    send_email,
)
from validations import validate_fields
from decorators import auth_required


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


reports_bp = Blueprint("reports_bp", __name__)
reports = DB[MONGO_COLLECTION_REPORTS]
authorities = DB[MONGO_COLLECTION_AUTHORITIES]
upvotes = DB[MONGO_COLLECTION_UPVOTES]


@reports_bp.route("/api/v1/reports", methods=["GET"])
@auth_required
def get_reports() -> make_response:
    """
    Retrieve all reports.

    Returns:
        make_response: JSON response containing all reports.
    """
    try:
        data = []
        for report in reports.find():
            report["_id"] = str(report["_id"])
            data.append(report)
        logger.info("Successfully retrieved all reports.")
        return make_response(jsonify(data), 200)
    except Exception as e:
        logger.error(f"Error retrieving reports: {e}")
        return make_response(
            jsonify({"Error": "Failed to retrieve reports"}), 500
        )


@reports_bp.route("/api/v1/reports", methods=["POST"])
@auth_required
def create_report() -> make_response:
    """
    Create a new report.

    Returns:
        make_response: JSON response with the URL of the created report or an error message.
    """
    required_fields = ["description", "category"]
    missing_fields = validate_fields(required_fields, request)
    if missing_fields:
        logger.warning(f"Missing fields in report data: {missing_fields}")
        return make_response(
            jsonify(
                {
                    "Unprocessable Entity": "Missing fields in JSON data.",
                    "missing_fields": missing_fields,
                }
            ),
            422,
        )

    if "image" not in request.files:
        logger.warning("No image provided in the report.")
        return make_response(
            jsonify({"Unprocessable Entity": "No image was provided"}), 422
        )

    image = request.files["image"]
    image_data = upload_image(image)

    if image_data.get("geolocation") is None:
        delete_image(image_data["image_name"])
        logger.warning("Geolocation could not be determined.")
        return make_response(
            jsonify({"Bad Request": "Geolocation could not be determined"}),
            400,
        )

    if not is_within_boundaries(image_data["geolocation"]):
        delete_image(image_data["image_name"])
        logger.warning("Geolocation is outside Northern Ireland.")
        return make_response(
            jsonify(
                {"Bad Request": "Geolocation is outside Northern Ireland"}
            ),
            400,
        )

    authority = determine_report_authority(
        image_data["geolocation"], request.form["category"]
    )
    new_report = {
        "user_id": int(request.form["userID"]),
        "description": request.form["description"],
        "category": request.form["category"],
        "geolocation": {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    image_data["geolocation"]["Lat"],
                    image_data["geolocation"]["Lon"],
                ],
            },
        },
        "authority": authority,
        "image": image_data,
        "resolved": False,
        "upvote_count": 0,
        "created_at": int(time.time()),
    }

    new_report_id = reports.insert_one(new_report).inserted_id
    url = f"http://localhost:5000/api/v1/reports/{str(new_report_id)}"

    send_email(
        authority_name=authority,
        report_id=str(new_report_id),
        description=request.form["description"],
        image_url=url,
    )

    logger.info(f"Report created successfully with ID: {new_report_id}")
    return make_response(jsonify({"url": url}), 201)


@reports_bp.route("/api/v1/reports/user/<int:user_id>", methods=["GET"])
@auth_required
def get_reports_by_user(user_id: int) -> make_response:
    """
    Retrieve reports for a specific user.

    Args:
        user_id (int): The ID of the user.

    Returns:
        make_response: JSON response containing the user's reports.
    """
    try:
        data = []
        for report in reports.find({"user_id": user_id}):
            report["_id"] = str(report["_id"])
            data.append(report)
        logger.info(f"Successfully retrieved reports for user ID: {user_id}")
        return make_response(jsonify(data), 200)
    except Exception as e:
        logger.error(f"Error retrieving reports for user ID {user_id}: {e}")
        return make_response(
            jsonify({"Error": "Failed to retrieve reports for the user"}), 500
        )


@reports_bp.route("/api/v1/reports/<string:report_id>", methods=["DELETE"])
@auth_required
def delete_report(report_id: str) -> make_response:
    """
    Delete a report by its ID.

    Args:
        report_id (str): The ID of the report to delete.

    Returns:
        make_response: JSON response indicating success or failure.
    """
    try:
        report_object_id = ObjectId(report_id)
        report = reports.find_one({"_id": report_object_id})
        if not report:
            logger.warning(f"Report not found for ID: {report_id}")
            return make_response(
                jsonify({"Not Found": "Report not found"}), 404
            )

        image_name = report["image"]["image_name"]
        if delete_image(image_name):
            reports.delete_one({"_id": report_object_id})
            logger.info(f"Report deleted successfully with ID: {report_id}")
            return make_response(
                jsonify({"Success": "Report deleted successfully"}), 204
            )
        else:
            logger.error(
                f"Failed to delete image from Azure Blob Storage for report ID: {report_id}"
            )
            return make_response(
                jsonify(
                    {"Error": "Failed to delete image from Azure Blob Storage"}
                ),
                500,
            )
    except Exception as e:
        logger.error(f"Error deleting report with ID {report_id}: {e}")
        return make_response(jsonify({"Error": "Internal Server Error"}), 500)


@reports_bp.route(
    "/api/v1/reports/<string:report_id>/resolve", methods=["POST"])
def resolve_report(report_id: str) -> make_response:
    """
    Mark a report as resolved by its ID.

    Args:
        report_id (str): The ID of the report to resolve.

    Returns:
        make_response: JSON response indicating success or failure.
    """
    try:
        report_object_id = ObjectId(report_id)
        report = reports.find_one({"_id": report_object_id})
        if not report:
            logger.warning(f"Report not found for ID: {report_id}")
            return make_response(
                jsonify({"Not Found": "Report not found"}), 404
            )

        reports.update_one(
            {"_id": report_object_id}, {"$set": {"resolved": True}}
        )
        logger.info(f"Report marked as resolved with ID: {report_id}")
        return make_response(
            jsonify({"Success": "Report marked as resolved"}), 200
        )
    except Exception as e:
        logger.error(f"Error resolving report with ID {report_id}: {e}")
        return make_response(jsonify({"Error": "Internal server error"}), 500)


@reports_bp.route("/api/v1/reports/<report_id>/upvote", methods=["POST"])
@auth_required
def upvote_report(report_id) -> make_response:
    """
    Upvote a report.

    Args:
        report_id (str): The ID of the report to upvote.

    Returns:
        make_response: JSON response indicating success or failure.
    """
    user_id = g.user_id

    if upvotes.find_one({"user_id": user_id, "report_id": report_id}):
        return make_response(
            jsonify({"Conflict": "User has already upvoted this report"}),
            409,
        )

    upvotes.insert_one({
        "user_id": user_id,
        "report_id": report_id,
        "timestamp": int(time.time())
    })

    result = reports.update_one(
        {"_id": ObjectId(report_id)},
        {"$inc": {"upvote_count": 1}}
    )

    if result.modified_count == 1:
            logging.info(f"Successfully incremented upvote count for report ID: {report_id}")
            return make_response(
                jsonify({"Success": "Report upvoted successfully"}),
                200,
            )
    else:
        logging.error(f"Failed to increment upvote count for report ID: {report_id}")
        return make_response(
            jsonify({"Error": "Failed to update upvote count"}),
            500,
        )