from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
import os

class Command(BaseCommand):
    help = 'Validates the deployment environment for production readiness.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting AgroFedly Deployment Validation...\n")
        
        errors = 0
        warnings = 0

        # 1. Check DEBUG
        if settings.DEBUG:
            self.stdout.write(self.style.ERROR("[FAIL] DEBUG is True. Must be False in production."))
            errors += 1
        else:
            self.stdout.write(self.style.SUCCESS("[PASS] DEBUG is False."))

        # 2. Check Allowed Hosts
        if not settings.ALLOWED_HOSTS or settings.ALLOWED_HOSTS == ['*']:
            self.stdout.write(self.style.ERROR("[FAIL] ALLOWED_HOSTS is insecure or empty."))
            errors += 1
        else:
            self.stdout.write(self.style.SUCCESS("[PASS] ALLOWED_HOSTS configured."))

        # 3. Check Database Connection
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS("[PASS] Database connected."))
        except OperationalError:
            self.stdout.write(self.style.ERROR("[FAIL] Database connection failed."))
            errors += 1

        # 4. Check Secret Key
        if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 30 or 'django-insecure' in settings.SECRET_KEY:
            self.stdout.write(self.style.ERROR("[FAIL] SECRET_KEY is insecure or using default."))
            errors += 1
        else:
            self.stdout.write(self.style.SUCCESS("[PASS] SECRET_KEY is valid."))

        # 5. Missing Integrations/Environment vars
        required_envs = ['EMAIL_HOST_USER', 'WEATHER_API_KEY', 'REDIS_URL']
        for env in required_envs:
            if not os.environ.get(env):
                self.stdout.write(self.style.WARNING(f"[WARN] {env} is not set. Feature might be degraded."))
                warnings += 1
            else:
                self.stdout.write(self.style.SUCCESS(f"[PASS] {env} is configured."))

        self.stdout.write("\nValidation Complete.")
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"Deployment is NOT READY. Blockers: {errors}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"READY FOR PRODUCTION REVIEW (Warnings: {warnings})"))
