# AgroFedly Production Readiness

This document outlines the required production setup, security configuration, and operational procedures for AgroFedly.

## 1. Architecture

The production architecture consists of:
- **Reverse Proxy**: Nginx or Traefik (terminates SSL, handles static files)
- **ASGI Server**: Daphne (runs Django and Channels for WebSockets)
- **Database**: PostgreSQL 15+
- **Message Broker & Cache**: Redis 7+
- **Background Workers**: Celery

## 2. Environment Variables

Your `.env` file must contain these variables in production:
- `DJANGO_SECRET_KEY`: A strong, randomly generated string.
- `DJANGO_DEBUG`: Must be set to `0`.
- `DJANGO_ALLOWED_HOSTS`: Comma-separated list of your production domains.
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of secure origins (e.g. `https://agrofedly.com`).
- `DATABASE_URL`: Connection string for PostgreSQL.
- `REDIS_URL`: Connection string for Redis.
- `CELERY_BROKER_URL` & `CELERY_RESULT_BACKEND`: Connection strings for Celery (typically Redis).
- `API_KEY`: A secret key for authenticating internal / server-to-server API calls.

## 3. Database Management

- **Migrations**: Always run `python manage.py migrate` after deploying a new version.
- **Backups**: Use `pg_dump` to create reliable database backups.
  ```bash
  pg_dump -U agro_user -d agrofedly -F c -f /backups/agrofedly_$(date +%Y%m%d).dump
  ```
- **Restores**:
  ```bash
  pg_restore -U agro_user -d agrofedly -1 /backups/agrofedly_BACKUP_FILE.dump
  ```

## 4. Static and Media Files

- Run `python manage.py collectstatic --noinput` during the build phase.
- Static files are served efficiently by WhiteNoise.
- For Media files (user uploads), ensure the `media/` directory is mounted to a persistent volume, or configure an external storage backend like AWS S3 using `django-storages`.

## 5. Security

- All connections should be over HTTPS (`SECURE_SSL_REDIRECT=True` is enforced when `DEBUG=0`).
- APIs are secured via an `API_KEY`.
- Organization isolation is strictly enforced via Django middleware and query filters.

## 6. Health Checks & Monitoring

AgroFedly provides standard endpoints for orchestration platforms (like Kubernetes or Docker Swarm):
- `/liveness/`: Checks if the web process is running.
- `/readiness/`: Checks if the database and Redis are reachable.

## 7. Deployment Sequence

1. Define `.env` with production secrets.
2. Build the Docker image.
3. Apply migrations: `python manage.py migrate`.
4. Collect static files: `python manage.py collectstatic --noinput`.
5. Start Redis and PostgreSQL.
6. Start Celery Worker: `celery -A AgroFedly worker -l info`.
7. Start Daphne: `daphne -b 0.0.0.0 -p 8000 AgroFedly.asgi:application`.

## 8. Rollback Procedure

If a deployment fails:
1. Revert the Docker image or source code to the previous commit.
2. If migrations were applied, you must reverse them **before** reverting the code, using `python manage.py migrate <app_name> <previous_migration_name>`.
3. Restart the Daphne and Celery services.

## Known Limitations

- Machine Learning features fall back to heuristic models if `ml/demand_bundle.pkl` is not present or if `joblib` fails.
- The default SQLite database is intentionally disabled in production (`DEBUG=0`) to prevent data corruption under concurrent load.
