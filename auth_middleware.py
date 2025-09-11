"""
Basic HTTP Authentication middleware for Bottle web application.

Provides simple username/password authentication using environment variables
or default credentials, with cookie-based session management to avoid
repeated authentication prompts.
"""

import os
import base64
import hmac
import hashlib
import time
import logging
from functools import wraps
from bottle import request, abort, response


def get_auth_credentials():
    """Get username and password from environment variables with defaults."""
    username = os.getenv('BASIC_AUTH_USERNAME', 'user')
    password = os.getenv('BASIC_AUTH_PASSWORD', 'pass')
    return username, password


def get_cookie_secret():
    """Get cookie signing secret from environment variable."""
    secret = os.getenv('AUTH_COOKIE_SECRET')
    if not secret:
        logging.warning(
            "AUTH_COOKIE_SECRET environment variable not set! "
            "Using insecure default. Generate a secure secret with:\n"
            "  openssl rand -base64 32\n"
            "Then set: export AUTH_COOKIE_SECRET=\"your-generated-secret\""
        )
        return "insecure-default-change-in-production"
    return secret


def create_auth_token(username, secret):
    """Create a signed authentication token."""
    timestamp = str(int(time.time()))
    # Create payload: username:timestamp
    payload = f"{username}:{timestamp}"
    # Create HMAC signature
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    # Return base64 encoded token
    token = f"{payload}:{signature}"
    return base64.b64encode(token.encode('utf-8')).decode('utf-8')


def verify_auth_token(token, secret, max_age_seconds=86400):  # 24 hours default
    """Verify a signed authentication token."""
    try:
        # Decode base64 token
        decoded = base64.b64decode(token.encode('utf-8')).decode('utf-8')
        parts = decoded.split(':')
        if len(parts) != 3:
            return None
        
        username, timestamp, signature = parts
        
        # Check token age
        token_time = int(timestamp)
        if time.time() - token_time > max_age_seconds:
            return None
        
        # Verify signature
        payload = f"{username}:{timestamp}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(signature, expected_signature):
            return username
        
    except (ValueError, TypeError, UnicodeDecodeError):
        pass
    
    return None


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
    Decorator that enforces Basic HTTP Authentication on routes with cookie session support.
    
    Usage:
        @get('/protected-route')
        @require_basic_auth
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = get_cookie_secret()
        
        # Check for valid session cookie first
        auth_cookie = request.get_cookie('auth_session')
        if auth_cookie:
            username = verify_auth_token(auth_cookie, secret)
            if username:
                # Valid session, proceed
                return f(*args, **kwargs)
        
        # No valid session, check Basic auth
        auth_header = request.environ.get('HTTP_AUTHORIZATION')
        provided_username, provided_password = parse_basic_auth(auth_header)
        
        # Get expected credentials
        expected_username, expected_password = get_auth_credentials()
        
        # Check if credentials match
        if (provided_username == expected_username and 
            provided_password == expected_password):
            # Create and set session cookie
            token = create_auth_token(provided_username, secret)
            response.set_cookie(
                'auth_session', 
                token, 
                max_age=86400,  # 24 hours
                httponly=True,
                secure=False,  # Set to True when using HTTPS
                path='/'
            )
            return f(*args, **kwargs)
        
        # Authentication failed - send 401 with WWW-Authenticate header
        response.status = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="Authentication Required"'
        return "Authentication required"
    
    return decorated


def basic_auth_plugin(callback):
    """
    Bottle plugin that applies Basic Authentication with cookie sessions to all routes.
    
    Install with:
        from bottle import install
        install(basic_auth_plugin)
    """
    def wrapper(*args, **kwargs):
        secret = get_cookie_secret()
        
        # Check for valid session cookie first
        auth_cookie = request.get_cookie('auth_session')
        if auth_cookie:
            username = verify_auth_token(auth_cookie, secret)
            if username:
                # Valid session, proceed
                return callback(*args, **kwargs)
        
        # No valid session, check Basic auth
        auth_header = request.environ.get('HTTP_AUTHORIZATION')
        provided_username, provided_password = parse_basic_auth(auth_header)
        
        # Get expected credentials
        expected_username, expected_password = get_auth_credentials()
        
        # Check if credentials match
        if (provided_username == expected_username and 
            provided_password == expected_password):
            # Create and set session cookie
            token = create_auth_token(provided_username, secret)
            response.set_cookie(
                'auth_session', 
                token, 
                max_age=86400,  # 24 hours
                httponly=True,
                secure=False,  # Set to True when using HTTPS
                path='/'
            )
            return callback(*args, **kwargs)
        
        # Authentication failed - send 401 with WWW-Authenticate header
        response.status = 401
        response.headers['WWW-Authenticate'] = 'Basic realm="Authentication Required"'
        return "Authentication required"
    
    return wrapper


def logout_route():
    """
    Route handler for logging out - clears the session cookie.
    
    Usage:
        @get('/logout')
        def logout():
            return logout_route()
    """
    response.delete_cookie('auth_session', path='/')
    return "Logged out successfully. <a href='/'>Return to main page</a>"