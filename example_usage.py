#!/usr/bin/env python3
"""
Example usage of the basic auth middleware with Bottle.

This demonstrates different ways to use the authentication middleware:
1. As a decorator on individual routes
2. As a plugin applied globally to all routes
"""

from bottle import Bottle, get, run, install
from auth_middleware import require_basic_auth, basic_auth_plugin


# Method 1: Using decorator on individual routes
app = Bottle()

@app.get('/public')
def public_route():
    """Public route that doesn't require authentication."""
    return "This is a public route - no authentication required"

@app.get('/protected')
@require_basic_auth
def protected_route():
    """Protected route that requires authentication."""
    return "This is a protected route - authentication required"

@app.get('/also-protected')
@require_basic_auth
def another_protected_route():
    """Another protected route."""
    return "This is also protected"


# Method 2: Using as a global plugin (uncomment to use)
# This will apply authentication to ALL routes
# install(basic_auth_plugin)

@app.get('/logout')
def logout():
    """Logout route to clear session cookie."""
    from auth_middleware import logout_route
    return logout_route()


if __name__ == '__main__':
    print("Starting example server...")
    print("Try these URLs:")
    print("  - http://localhost:8080/public (no auth needed)")
    print("  - http://localhost:8080/protected (auth needed)")
    print("  - http://localhost:8080/also-protected (auth needed)")
    print("  - http://localhost:8080/logout (clear session)")
    print()
    print("Default credentials: user / pass")
    print("Set BASIC_AUTH_USERNAME and BASIC_AUTH_PASSWORD env vars to customize")
    print()
    print("Cookie session management:")
    print("After first authentication, a session cookie is set for 24 hours")
    print("Generate secure cookie secret: openssl rand -base64 32")
    print("Set: export AUTH_COOKIE_SECRET=\"your-generated-secret\"")
    run(app, host='localhost', port=8080, debug=True)