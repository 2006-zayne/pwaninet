import secrets
import hashlib
from django.conf import settings


def generate_device_id():
    """
    Generate a unique device ID using cryptographically secure random bytes.
    This ID will be stored in the browser's localStorage.
    """
    return secrets.token_urlsafe(32)


def get_or_create_device_id(request):
    """
    Get device ID from request headers or generate a new one.
    The device ID should be sent in the X-Device-ID header by the frontend.
    """
    device_id = request.headers.get('X-Device-ID')
    if not device_id:
        # If no device ID in headers, generate one (should be set by frontend)
        device_id = generate_device_id()
    return device_id


def hash_device_id(device_id):
    """
    Hash the device ID before storing in database for security.
    This prevents the raw device ID from being exposed if the database is compromised.
    """
    salt = settings.SECRET_KEY.encode()
    return hashlib.sha256(device_id.encode() + salt).hexdigest()


def is_valid_device_id(device_id):
    """
    Validate that a device ID is properly formatted.
    """
    if not device_id or len(device_id) < 20:
        return False
    return True
