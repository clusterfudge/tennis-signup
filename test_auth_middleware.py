#!/usr/bin/env python3
"""
Tests for the basic auth middleware.
"""

import os
import base64
import time
import unittest
from unittest.mock import patch, Mock
from auth_middleware import (
    get_auth_credentials,
    parse_basic_auth,
    require_basic_auth,
    basic_auth_plugin,
    get_cookie_secret,
    create_auth_token,
    verify_auth_token,
    logout_route
)


class TestAuthMiddleware(unittest.TestCase):
    
    def test_get_auth_credentials_defaults(self):
        """Test that default credentials are returned when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            username, password = get_auth_credentials()
            self.assertEqual(username, 'user')
            self.assertEqual(password, 'pass')
    
    def test_get_auth_credentials_from_env(self):
        """Test that credentials are read from environment variables."""
        with patch.dict(os.environ, {
            'BASIC_AUTH_USERNAME': 'testuser',
            'BASIC_AUTH_PASSWORD': 'testpass'
        }):
            username, password = get_auth_credentials()
            self.assertEqual(username, 'testuser')
            self.assertEqual(password, 'testpass')
    
    def test_parse_basic_auth_valid(self):
        """Test parsing valid Basic auth header."""
        # Create a valid Basic auth header
        credentials = base64.b64encode(b'testuser:testpass').decode('ascii')
        auth_header = f'Basic {credentials}'
        
        username, password = parse_basic_auth(auth_header)
        self.assertEqual(username, 'testuser')
        self.assertEqual(password, 'testpass')
    
    def test_parse_basic_auth_invalid_format(self):
        """Test parsing invalid auth header formats."""
        # No auth header
        username, password = parse_basic_auth(None)
        self.assertIsNone(username)
        self.assertIsNone(password)
        
        # Wrong scheme
        username, password = parse_basic_auth('Bearer token123')
        self.assertIsNone(username)
        self.assertIsNone(password)
        
        # Invalid base64
        username, password = parse_basic_auth('Basic invalid_base64!')
        self.assertIsNone(username)
        self.assertIsNone(password)
    
    def test_parse_basic_auth_no_colon(self):
        """Test parsing auth header with no colon separator."""
        credentials = base64.b64encode(b'testusernocolon').decode('ascii')
        auth_header = f'Basic {credentials}'
        
        username, password = parse_basic_auth(auth_header)
        self.assertIsNone(username)
        self.assertIsNone(password)
    
    def test_parse_basic_auth_password_with_colon(self):
        """Test parsing auth header where password contains colon."""
        credentials = base64.b64encode(b'testuser:pass:with:colons').decode('ascii')
        auth_header = f'Basic {credentials}'
        
        username, password = parse_basic_auth(auth_header)
        self.assertEqual(username, 'testuser')
        self.assertEqual(password, 'pass:with:colons')


class TestCookieAuth(unittest.TestCase):
    
    def test_get_cookie_secret_default(self):
        """Test that a default secret is returned when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('auth_middleware.logging.warning') as mock_warning:
                secret = get_cookie_secret()
                self.assertEqual(secret, 'insecure-default-change-in-production')
                mock_warning.assert_called_once()
    
    def test_get_cookie_secret_from_env(self):
        """Test that secret is read from environment variable."""
        with patch.dict(os.environ, {'AUTH_COOKIE_SECRET': 'test-secret-123'}):
            secret = get_cookie_secret()
            self.assertEqual(secret, 'test-secret-123')
    
    def test_create_and_verify_auth_token(self):
        """Test creating and verifying auth tokens."""
        secret = 'test-secret'
        username = 'testuser'
        
        token = create_auth_token(username, secret)
        self.assertIsInstance(token, str)
        
        # Verify the token
        verified_username = verify_auth_token(token, secret)
        self.assertEqual(verified_username, username)
    
    def test_verify_auth_token_wrong_secret(self):
        """Test that token verification fails with wrong secret."""
        token = create_auth_token('testuser', 'secret1')
        result = verify_auth_token(token, 'secret2')
        self.assertIsNone(result)
    
    def test_verify_auth_token_expired(self):
        """Test that expired tokens are rejected."""
        secret = 'test-secret'
        username = 'testuser'
        
        token = create_auth_token(username, secret)
        
        # Verify with very short max_age
        result = verify_auth_token(token, secret, max_age_seconds=0)
        self.assertIsNone(result)
    
    def test_verify_auth_token_invalid_format(self):
        """Test that malformed tokens are rejected."""
        secret = 'test-secret'
        
        # Invalid base64
        result = verify_auth_token('invalid_token!', secret)
        self.assertIsNone(result)
        
        # Valid base64 but wrong format
        invalid_token = base64.b64encode(b'invalid:format').decode('utf-8')
        result = verify_auth_token(invalid_token, secret)
        self.assertIsNone(result)


class TestAuthDecorator(unittest.TestCase):
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_auth_credentials')
    @patch('auth_middleware.get_cookie_secret')
    def test_require_basic_auth_success(self, mock_get_secret, mock_get_creds, mock_response, mock_request):
        """Test successful authentication with decorator."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        mock_get_secret.return_value = 'test-secret'
        credentials = base64.b64encode(b'user:pass').decode('ascii')
        mock_request.environ = {'HTTP_AUTHORIZATION': f'Basic {credentials}'}
        mock_request.get_cookie.return_value = None  # No existing cookie
        mock_response.set_cookie = Mock()
        
        # Create a test function with the decorator
        @require_basic_auth
        def test_route():
            return "success"
        
        result = test_route()
        self.assertEqual(result, "success")
        # Verify cookie was set
        mock_response.set_cookie.assert_called_once()
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_auth_credentials')
    @patch('auth_middleware.get_cookie_secret')
    def test_require_basic_auth_failure(self, mock_get_secret, mock_get_creds, mock_response, mock_request):
        """Test failed authentication with decorator."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        mock_get_secret.return_value = 'test-secret'
        credentials = base64.b64encode(b'wrong:credentials').decode('ascii')
        mock_request.environ = {'HTTP_AUTHORIZATION': f'Basic {credentials}'}
        mock_request.get_cookie.return_value = None  # No existing cookie
        mock_response.headers = {}
        
        # Create a test function with the decorator
        @require_basic_auth
        def test_route():
            return "success"
        
        result = test_route()
        
        # Check that 401 status was set
        self.assertEqual(mock_response.status, 401)
        self.assertEqual(mock_response.headers['WWW-Authenticate'], 'Basic realm="Authentication Required"')
        self.assertEqual(result, "Authentication required")
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_auth_credentials')
    @patch('auth_middleware.get_cookie_secret')
    def test_require_basic_auth_no_header(self, mock_get_secret, mock_get_creds, mock_response, mock_request):
        """Test authentication failure when no auth header provided."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        mock_get_secret.return_value = 'test-secret'
        mock_request.environ = {}  # No HTTP_AUTHORIZATION header
        mock_request.get_cookie.return_value = None  # No existing cookie
        mock_response.headers = {}
        
        # Create a test function with the decorator
        @require_basic_auth
        def test_route():
            return "success"
        
        result = test_route()
        
        # Check that 401 status was set
        self.assertEqual(mock_response.status, 401)
        self.assertEqual(mock_response.headers['WWW-Authenticate'], 'Basic realm="Authentication Required"')
        self.assertEqual(result, "Authentication required")
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_cookie_secret')
    @patch('auth_middleware.verify_auth_token')
    def test_require_basic_auth_valid_cookie(self, mock_verify, mock_get_secret, mock_response, mock_request):
        """Test successful authentication with valid cookie."""
        # Set up mocks
        mock_get_secret.return_value = 'test-secret'
        mock_verify.return_value = 'user'  # Valid token returns username
        mock_request.get_cookie.return_value = 'valid-token'
        mock_request.environ = {}  # No HTTP_AUTHORIZATION header needed
        
        # Create a test function with the decorator
        @require_basic_auth
        def test_route():
            return "success"
        
        result = test_route()
        self.assertEqual(result, "success")
        # Verify token was checked
        mock_verify.assert_called_once_with('valid-token', 'test-secret')


class TestLogout(unittest.TestCase):
    
    @patch('auth_middleware.response')
    def test_logout_route(self, mock_response):
        """Test logout functionality."""
        mock_response.delete_cookie = Mock()
        
        result = logout_route()
        
        # Check that cookie was deleted
        mock_response.delete_cookie.assert_called_once_with('auth_session', path='/')
        self.assertIn("Logged out successfully", result)


if __name__ == '__main__':
    unittest.main()