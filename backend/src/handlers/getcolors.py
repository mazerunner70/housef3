import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime

from utils.http import create_response
from utils.auth import get_user_from_event

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_colors() -> List[Dict[str, Any]]:
    """Return a list of color objects with metadata."""
    return [
        {
            "name": "Cerulean",
            "hex": "#007BA7",
            "category": "blue"
        },
        {
            "name": "Crimson",
            "hex": "#DC143C",
            "category": "red"
        },
        {
            "name": "Sage",
            "hex": "#BCB88A",
            "category": "green"
        },
        {
            "name": "Amber",
            "hex": "#FFBF00",
            "category": "yellow"
        }
    ]

def getcolors(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler for getting colors.
    
    Args:
        event (Dict[str, Any]): API Gateway Lambda Proxy Input Format
        context (Any): Lambda Context runtime methods and attributes

    Returns:
        Dict[str, Any]: API Gateway Lambda Proxy Output Format
    """
    logger.info(f"starting getcolors handler")
    try:
        # Get user from event
        logger.info(f"Event structure: {json.dumps(event)}")
        logger.info(f"Request context: {json.dumps(event.get('requestContext', {}))}")
        logger.info(f"Authorizer: {json.dumps(event.get('requestContext', {}).get('authorizer', {}))}")
        user = get_user_from_event(event)
        logger.info(f"User result: {json.dumps(user) if user else 'None'}")
        if not user:
            return create_response(401, {"message": "Unauthorized"})

        # Return mock colors for now
        colors = [
            {"name": "Red", "hex": "#FF0000"},
            {"name": "Green", "hex": "#00FF00"},
            {"name": "Blue", "hex": "#0000FF"},
            {"name": "Yellow", "hex": "#FFFF00"},
            {"name": "Purple", "hex": "#800080"},
            {"name": "Orange", "hex": "#FFA500"},
            {"name": "Pink", "hex": "#FFC0CB"},
            {"name": "Brown", "hex": "#A52A2A"},
            {"name": "Gray", "hex": "#808080"},
            {"name": "Black", "hex": "#000000"}
        ]

        return create_response(200, {
            "colors": colors,
            "metadata": {
                "totalColors": len(colors)
            },
            "user": user
        })

    except Exception as e:
        logger.error(f"Error in getcolors handler: {str(e)}")
        return create_response(500, {"message": "Internal server error"})

# Make getcolors the default export
handler = getcolors 