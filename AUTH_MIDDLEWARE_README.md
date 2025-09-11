# Basic Auth HTTP Middleware

A simple HTTP Basic Authentication middleware for Bottle web applications.

## Features

- Simple username/password authentication using HTTP Basic Auth
- Environment variable configuration with sensible defaults
- Can be used as a decorator on individual routes or as a global plugin
- Proper HTTP 401 responses with WWW-Authenticate headers
- Comprehensive test coverage

## Installation

The middleware is implemented in `auth_middleware.py`. No additional dependencies are required beyond what's already in `requirements.txt`.

## Configuration

The middleware uses environment variables for configuration:

- `BASIC_AUTH_USERNAME`: Username for authentication (default: "user")
- `BASIC_AUTH_PASSWORD`: Password for authentication (default: "pass")

## Usage

### Method 1: Decorator on Individual Routes

Use the `@require_basic_auth` decorator to protect specific routes:

```python
from bottle import get
from auth_middleware import require_basic_auth

@get('/protected-route')
@require_basic_auth
def protected_route():
    return "This route requires authentication"

@get('/public-route')
def public_route():
    return "This route is public"
```

### Method 2: Global Plugin

Apply authentication to all routes using the plugin:

```python
from bottle import install
from auth_middleware import basic_auth_plugin

# This will protect ALL routes
install(basic_auth_plugin)
```

### Integration with Existing Application

To add authentication to the existing `web.py` application, you have several options:

#### Option A: Protect all routes globally
Add these lines to `web.py`:

```python
from bottle import install
from auth_middleware import basic_auth_plugin

# Add this line after imports
install(basic_auth_plugin)
```

#### Option B: Protect specific routes only
Add the decorator to specific routes in `web.py`:

```python
from auth_middleware import require_basic_auth

@get('/schedule')
@get('/schedule/<schedule_id>')
@require_basic_auth  # Add this decorator
def serve_schedule(schedule_id=None):
    # ... existing code
```

## Environment Setup

Set your credentials using environment variables:

```bash
export BASIC_AUTH_USERNAME="your_username"
export BASIC_AUTH_PASSWORD="your_secure_password"
```

Or create a `.env` file:

```
BASIC_AUTH_USERNAME=your_username
BASIC_AUTH_PASSWORD=your_secure_password
```

## Testing

Run the test suite:

```bash
python -m unittest test_auth_middleware.py -v
```

## Example

See `example_usage.py` for a complete working example that demonstrates both usage methods.

To run the example:

```bash
python example_usage.py
```

Then test the endpoints:

- `http://localhost:8080/public` - No authentication required
- `http://localhost:8080/protected` - Authentication required
- `http://localhost:8080/also-protected` - Authentication required

Default credentials are `user` / `pass`.

## Security Considerations

- This is basic HTTP authentication and credentials are base64 encoded (not encrypted)
- Always use HTTPS in production to protect credentials in transit
- Consider using more secure authentication methods for production applications
- The default credentials should always be changed in production