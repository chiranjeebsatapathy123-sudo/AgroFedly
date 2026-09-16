# AgroFedly Deployment Guide

This guide details the steps required to deploy AgroFedly into a production environment. AgroFedly relies on ASGI (WebSockets), Redis, and PostgreSQL. It is **not** suitable for a standard WSGI-only environment (e.g. basic cPanel) or a purely serverless function environment (e.g. standard Vercel serverless) unless Channels is specifically configured.

## 1. System Requirements
- **Python**: 3.10+
- **Database**: PostgreSQL 13+
- **In-Memory Store**: Redis 6+ (Required for WebSockets / Channels)
- **Web Server / Reverse Proxy**: Nginx or Caddy
- **Application Server**: Daphne or Gunicorn (with Uvicorn workers)

## 2. Environment Variables
You must set the following environment variables in your production environment (`.env` or host config):

```env
# Core Django
DJANGO_SECRET_KEY=your-secure-random-string-here
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Database (Strictly PostgreSQL in production)
DATABASE_URL=postgres://user:password@host:port/dbname

# Redis (For WebSockets/Channels)
REDIS_URL=redis://host:port/0

# External APIs
WEATHER_API_KEY=your-openweathermap-api-key
OPENAI_API_KEY=your-openai-api-key
API_KEY=your-custom-internal-api-key
```

## 3. Installation & Preparation
1. **Clone the repository.**
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```
4. **Collect Static Files:**
   WhiteNoise is configured to serve static files in production.
   ```bash
   python manage.py collectstatic --noinput
   ```

## 4. Running the ASGI Server (Daphne)
Since AgroFedly uses WebSockets, you must use an ASGI server. Daphne is highly recommended.

```bash
# Start Daphne binding to port 8000
daphne -b 0.0.0.0 -p 8000 AgroFedly.asgi:application
```

Alternatively, use Gunicorn with Uvicorn workers:
```bash
gunicorn AgroFedly.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## 5. Nginx Reverse Proxy Configuration
You must configure your reverse proxy to forward both HTTP traffic and WebSocket Upgrade requests.

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    # HTTP requests
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket requests
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## 6. HTTPS & Security
AgroFedly is configured to enforce strict security in production when `DJANGO_DEBUG=0`.
Ensure you have a valid SSL certificate (e.g. Let's Encrypt).
The application will automatically set:
- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

## 7. Health Checks
Monitor the application uptime via the built-in health endpoint:
- `GET /health/`
Returns a 200 OK JSON response verifying Database, Redis, and ML Model connectivity.

## 8. Rollback & Backups
- **Database Backups:** Use `pg_dump` daily. Ensure backups are stored off-site.
- **Rollback:** If a deployment fails, revert the code using Git, run `pip install`, and restart the ASGI server. Do not reverse migrations automatically without manual review.
