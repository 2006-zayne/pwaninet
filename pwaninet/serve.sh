#!/bin/bash

# Pwaninet Server Script
mkcert -install && \
mkcert localhost && \
uvicorn pwaninet.asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --ssl-keyfile localhost-key.pem \
  --ssl-certfile localhost.pem \
  --reload