#!/usr/bin/env python3
"""
Tests for the basic auth middleware.
"""

import os
import base64
import unittest
from unittest.mock import patch, Mock
from auth_middleware import (
    get_auth_credentials,
    parse_basic_auth,
    require_basic_auth,
    basic_auth_plugin
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


class TestAuthDecorator(unittest.TestCase):
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_auth_credentials')
    def test_require_basic_auth_success(self, mock_get_creds, mock_response, mock_request):
        """Test successful authentication with decorator."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        credentials = base64.b64encode(b'user:pass').decode('ascii')
        mock_request.environ = {'HTTP_AUTHORIZATION': f'Basic {credentials}'}
        
        # Create a test function with the decorator
        @require_basic_auth
        def test_route():
            return "success"
        
        result = test_route()
        self.assertEqual(result, "success")
    
    @patch('auth_middleware.request')
    @patch('auth_middleware.response')
    @patch('auth_middleware.get_auth_credentials')
    def test_require_basic_auth_failure(self, mock_get_creds, mock_response, mock_request):
        """Test failed authentication with decorator."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        credentials = base64.b64encode(b'wrong:credentials').decode('ascii')
        mock_request.environ = {'HTTP_AUTHORIZATION': f'Basic {credentials}'}
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
    def test_require_basic_auth_no_header(self, mock_get_creds, mock_response, mock_request):
        """Test authentication failure when no auth header provided."""
        # Set up mocks
        mock_get_creds.return_value = ('user', 'pass')
        mock_request.environ = {}  # No HTTP_AUTHORIZATION header
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


if __name__ == '__main__':
    unittest.main()