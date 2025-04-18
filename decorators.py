"""
File: decorators.py
Author: Jack McArdle

This file is part of CommunityEye.

Email: mcardle-j9@ulster.ac.uk
B-No: B00733578
"""

import logging
import requests
from functools import wraps
from flask import request, jsonify, make_response, g
from typing import Callable, Any
import jwt
from config import FLASK_SECRET_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = "http://localhost:5001/api/v1/validate-token"


def auth_required(func: Callable) -> Callable:
    """
    Decorator to enforce authentication for Flask routes by validating a JWT token.

    This decorator checks for the presence and validity of a JWT token in the request headers
    by making a request to an external auth service. If the token is missing or invalid, it
    returns an unauthorized response.

    Args:
        func (Callable): The Flask route function to be decorated.

    Returns:
        Callable: The decorated function with authentication checks.
    """
    @wraps(func)
    def auth_required_wrapper(*args: Any, **kwargs: Any) -> Any:
        token = request.headers.get("x-access-token")
        if not token:
            logger.warning("Unauthorized access attempt: Token is missing.")
            return make_response(
                jsonify({"Unauthorized": "Token is missing."}), 401
            )
       
        if not token:
            logger.warning("Unauthorized access attempt: Token is missing.")
            return make_response(
                jsonify({"Unauthorized": "Token is missing."}), 401
            )
        
        try:
            data = jwt.decode(token, FLASK_SECRET_KEY, algorithms=["HS256"])
            g.user_id = data["user_id"]
        except jwt.InvalidTokenError as e:
            logger.warning(
                f"Unauthorized access attempt: Invalid token. Error: {str(e)}"
            )
            return make_response(
                jsonify({"Unauthorized": "Token is invalid."}), 401
            )

        try:
            response = requests.post(
                AUTH_SERVICE_URL, json={"token": token}, timeout=5
            )
            response.raise_for_status() 
        except requests.RequestException as e:
            logger.error(f"Error validating token: {str(e)}")
            return make_response(
                jsonify({"Unauthorized": "Error validating token."}), 500
            )

        if response.status_code != 200:
            logger.warning(
                f"Unauthorized access attempt: {response.json().get('message', 'Unknown error')}"
            )
            return make_response(
                jsonify(response.json()), response.status_code
            )
        
        
        return func(*args, **kwargs)

    return auth_required_wrapper
