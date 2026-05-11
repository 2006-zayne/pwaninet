# HTTPS Development Setup for PWA Testing
## Using uvicorn/daphne with SSL certificates

### 1. Generate SSL Certificate

#### Option A: Using mkcert (Recommended - No browser warnings)
```bash
# Install mkcert
curl -JLO "https://dl.filippo.io/mkcert/latest?os=linux&arch=amd64"
chmod +x mkcert-v*-linux-amd64
sudo mv mkcert-v*-linux-amd64 /usr/local/bin/mkcert

# Create and install local CA
mkcert -install

# Generate certificate for localhost and local IP
mkcert localhost 127.0.0.1 192.168.1.100 10.0.0.100
```

#### Option B: Using OpenSSL (Self-signed - Browser warnings)
```bash
# Create certificates directory
mkdir -p ~/ssl-certs
cd ~/ssl-certs

# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout localhost.key \
  -out localhost.crt \
  -subj "/C=US/ST=State/L=City/O=Dev/CN=localhost"

# Get your local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ${LOCAL_IP}.key \
  -out ${LOCAL_IP}.crt \
  -subj "/C=US/ST=State/L=City/O=Dev/CN=${LOCAL_IP}"
```

### 2. Configure Django for HTTPS Development

Create `settings/local.py`:
```python
# settings/local.py
from .base import *

# Development HTTPS settings
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Allow cookies in development with HTTPS
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# Trust local headers (for proxy setups)
SECURE_PROXY_SSL_HEADER = ['HTTP_X_FORWARDED_PROTO']
```

### 3. uvicorn/daphne HTTPS Configuration

#### Method A: uvicorn with SSL
```bash
# Create start script: start_https_dev.sh
#!/bin/bash

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"

# Start uvicorn with SSL
uvicorn pwaninet.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile ~/ssl-certs/localhost.key \
  --ssl-certfile ~/ssl-certs/localhost.crt \
  --reload \
  --log-level debug
```

#### Method B: daphne with SSL
```bash
# Create start script: start_https_dev.sh
#!/bin/bash

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"

# Start daphne with SSL
daphne -b 0.0.0.0 -p 8000 \
  -e ssl:port=8000:certFile=~/ssl-certs/localhost.crt:keyFile=~/ssl-certs/localhost.key \
  pwaninet.asgi:application
```

#### Method C: Using mkcert certificates
```bash
#!/bin/bash

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')
echo "Local IP: $LOCAL_IP"

# Use mkcert-generated files
uvicorn pwaninet.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile ~/ssl-certs/localhost+2-key.pem \
  --ssl-certfile ~/ssl-certs/localhost+2.pem \
  --reload
```

### 4. Make Script Executable
```bash
chmod +x start_https_dev.sh
./start_https_dev.sh
```

### 5. Mobile Hotspot Setup for PWA Testing

#### Create Mobile Hotspot
```bash
# On Ubuntu/Linux
nm-connection-editor
# Create new Wi-Fi hotspot:
# - Name: "PWA-Test"
# - Password: "test12345"
# - Band: 2.4GHz

# Or using command line
sudo nmcli device wifi hotspot ifname wlan0 \
  ssid "PWA-Test" \
  password "test12345"
```

#### Connect Mobile Device
1. **Enable hotspot** on your development machine
2. **Connect mobile device** to "PWA-Test" network
3. **Find your IP**: `hostname -I` (e.g., 192.168.1.1)
4. **Access PWA**: `https://192.168.1.1:8000`

### 6. Trust Certificate on Mobile

#### For iOS (iPhone/iPad)
```bash
# Transfer certificate to mobile
# Method 1: Airdrop the .crt file
# Method 2: Email it to yourself
# Method 3: Serve via HTTP and download

# Install on iOS:
# Settings > General > VPN & Device Management > Install Profile
# Trust the certificate
```

#### For Android
```bash
# Transfer certificate to mobile
# Install via Settings > Security > Install from storage
# Or Settings > Security > Encryption & credentials > Install from storage
```

### 7. PWA Testing Checklist

#### Service Worker Testing
- [ ] Access via HTTPS on mobile
- [ ] Check "Add to Home Screen" prompt appears
- [ ] Install PWA from browser menu
- [ ] Test offline functionality
- [ ] Verify background sync works

#### Network Testing
- [ ] Test with mobile hotspot
- [ ] Test with different network conditions
- [ ] Verify offline cache works
- [ ] Test push notifications (if implemented)

### 8. Offline PWA Testing

#### Yes, it's possible with mobile hotspot!

**How it works:**
1. **Install PWA** while connected to hotspot
2. **Service Worker caches** all necessary files
3. **Disconnect hotspot** - PWA still works offline
4. **Test offline functionality** - cached pages load, offline page shows

**Testing steps:**
```bash
# 1. Start with hotspot connected
./start_https_dev.sh

# 2. On mobile: Access https://YOUR_IP:8000
# 3. Install PWA (Add to Home Screen)
# 4. Disconnect mobile from hotspot
# 5. Try opening PWA - should work offline!
```

### 9. Troubleshooting

#### Common Issues
```bash
# Certificate not trusted
# Solution: Use mkcert instead of OpenSSL

# Mobile can't connect
# Solution: Check firewall, ensure 0.0.0.0 binding

# PWA won't install
# Solution: Check manifest.json, service worker registration

# Offline not working
# Solution: Verify service worker cache strategy
```

#### Debug Commands
```bash
# Check if port is listening
sudo netstat -tlnp | grep :8000

# Test certificate
openssl s_client -connect localhost:8000

# Check mobile connection
ping 192.168.1.1 from mobile device
```

### 10. Development Workflow

```bash
# 1. Start HTTPS dev server
./start_https_dev.sh

# 2. Connect mobile to hotspot
# 3. Test PWA features:
#    - Installation
#    - Offline functionality
#    - Background sync
#    - Push notifications

# 4. Make changes to code
# 5. Server auto-reloads
# 6. Test on mobile again
```

## Quick Start Commands

```bash
# One-liner to get everything running
mkcert -install && \
mkcert localhost && \
uvicorn pwaninet.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile localhost-key.pem \
  --ssl-certfile localhost.pem \
  --reload
```

This setup gives you:
✅ HTTPS for PWA requirements
✅ Mobile testing capability  
✅ Offline PWA testing
✅ Real development workflow
✅ No browser warnings (with mkcert)
