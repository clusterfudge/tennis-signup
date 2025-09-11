# Basic Auth HTTP Middleware

A simple HTTP Basic Authentication middleware for Bottle web applications with cookie-based session management.

## Features

- Simple username/password authentication using HTTP Basic Auth
- Cookie-based session management to avoid repeated authentication prompts
- Environment variable configuration with sensible defaults
- Can be used as a decorator on individual routes or as a global plugin
- Proper HTTP 401 responses with WWW-Authenticate headers
- Secure token-based sessions with HMAC signature verification
- Configurable session expiration (default: 24 hours)
- Logout functionality to clear sessions
- Comprehensive test coverage

## Installation

The middleware is implemented in `auth_middleware.py`. No additional dependencies are required beyond what's already in `requirements.txt`.

## Configuration

The middleware uses environment variables for configuration:

- `BASIC_AUTH_USERNAME`: Username for authentication (default: "user")
- `BASIC_AUTH_PASSWORD`: Password for authentication (default: "pass")
- `AUTH_COOKIE_SECRET`: Secret key for signing session cookies (required for production)

### Generating a Secure Cookie Secret

For production use, generate a secure secret key:

```bash
openssl rand -base64 32
```

Then set it as an environment variable:

```bash
export AUTH_COOKIE_SECRET="your-generated-32-char-secret"
```

**Important**: If `AUTH_COOKIE_SECRET` is not set, the middleware will use an insecure default and log a warning with instructions.

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

### Adding Logout Functionality

The middleware includes a logout route helper:

```python
from auth_middleware import logout_route

@get('/logout')
def logout():
    return logout_route()
```

This clears the session cookie and redirects users to re-authenticate on their next request.

## Environment Setup

Set your credentials and cookie secret using environment variables:

```bash
# Authentication credentials
export BASIC_AUTH_USERNAME="your_username"
export BASIC_AUTH_PASSWORD="your_secure_password"

# Generate and set cookie secret
export AUTH_COOKIE_SECRET="$(openssl rand -base64 32)"
```

Or create a `.env` file:

```
BASIC_AUTH_USERNAME=your_username
BASIC_AUTH_PASSWORD=your_secure_password
AUTH_COOKIE_SECRET=your_generated_secret_key_here
```

## Session Management

After successful authentication, the middleware sets a secure session cookie that:

- Expires after 24 hours (configurable)
- Is HTTP-only (not accessible via JavaScript)
- Contains a signed token with username and timestamp
- Uses HMAC-SHA256 for signature verification
- Automatically renews on each successful authentication

Users won't be prompted for credentials again until the cookie expires or they visit `/logout`.

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
- `http://localhost:8080/protected` - Authentication required (first time only)
- `http://localhost:8080/also-protected` - Authentication required (first time only)
- `http://localhost:8080/logout` - Clears session cookie

Default credentials are `user` / `pass`.

After first authentication, subsequent requests use the session cookie automatically.

## Security Considerations

- Basic HTTP authentication credentials are base64 encoded (not encrypted)
- Always use HTTPS in production to protect credentials and cookies in transit
- Session cookies use HMAC-SHA256 signatures for integrity verification
- Cookies are set as HTTP-only to prevent XSS attacks
- Set `secure=True` on cookies when using HTTPS (modify `auth_middleware.py`)
- Generate a strong secret key using `openssl rand -base64 32`
- The default credentials should always be changed in production
- Session cookies expire after 24 hours by default
- Consider using more robust authentication for highly sensitive applications

### Production Checklist

1. ✅ Set strong `BASIC_AUTH_USERNAME` and `BASIC_AUTH_PASSWORD`
2. ✅ Generate secure `AUTH_COOKIE_SECRET` using OpenSSL
3. ✅ Use HTTPS in production
4. ✅ Set `secure=True` for cookies in HTTPS environments
5. ✅ Consider shorter session timeouts for sensitive applications
6. ✅ Monitor authentication logs for suspicious activity