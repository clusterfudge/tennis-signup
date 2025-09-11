"""
Basic HTTP Authentication middleware for Bottle web application.

Provides simple username/password authentication using environment variables
or default credentials.
"""

import os
import base64
from functools import wraps
from bottle import request, abort, response


def get_auth_credentials():
    """Get username and password from environment variables with defaults."""
    username = os.getenv('BASIC_AUTH_USERNAME', 'user')
    password = os.getenv('BASIC_AUTH_PASSWORD', 'pass')
    return username, password


def parse_basic_auth(auth_header):
    """Parse Basic Authentication header and return username, password tuple."""
    if not auth_header or not auth_header.startswith('Basic '):
        return None, None
    
    try:
        # Decode the base64 encoded credentials
        encoded_credentials = auth_header[6:]  # Remove 'Basic ' prefix
        decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
        username, password = decoded_credentials.split(':', 1)
        return username, password
    except (ValueError, UnicodeDecodeError):
        return None, None


def require_basic_auth(f):
    """
    Decorator that enforces Basic HTTP Authentication on routes.
    
    Usage:
        @get('/protected-route')
        @require_basic_auth
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.environ.get('HTTP_AUTHORIZATION')
        provided_username, provided_password = parse_basic_auth(auth_header)
        
        # Get expected credentials
        expected_username, expected_password = get_auth_credentials()
        
        # Check if credentials match
        if (provided_username == expected_username and 
            provided_password == expected_password):
            return f(*args, **kwargs)
        
        # Authentication failed - send 401 with WWW-Authenticate header
        response.status = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="Authentication Required"'
        return "Authentication required"
    
    return decorated


def basic_auth_plugin(callback):
    """
    Bottle plugin that applies Basic Authentication to all routes.
    
    Install with:
        from bottle import install
        install(basic_auth_plugin)
    """
    def wrapper(*args, **kwargs):
        auth_header = request.environ.get('HTTP_AUTHORIZATION')
        provided_username, provided_password = parse_basic_auth(auth_header)
        
        # Get expected credentials
        expected_username, expected_password = get_auth_credentials()
        
        # Check if credentials match
        if (provided_username == expected_username and 
            provided_password == expected_password):
            return callback(*args, **kwargs)
        
        # Authentication failed - send 401 with WWW-Authenticate header
        response.status = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="Authentication Required"'
        return "Authentication required"
    
    return wrapper