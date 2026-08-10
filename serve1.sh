cd projects 
source venv/bin/activate
cd pwaninet
docker compose up -d db redis
uvicorn pwaninet.asgi:application --host 0.0.0.0 --port 8000