from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from feedly.models import UserProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Securely provisions a Super Admin account for AgroFedly 2.0 platform.'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the super admin')
        parser.add_argument('email', type=str, help='Email for the super admin')
        parser.add_argument('password', type=str, help='Password for the super admin')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists.'))
            return
            
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Email "{email}" is already in use.'))
            return

        # Create Django Superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            
            # Ensure UserProfile exists with correct role and status
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.role = 'SUPER_ADMIN'
            profile.account_status = 'ACTIVE'
            profile.onboarding_completed = True
            profile.onboarding_step = 3
            profile.save()
            
            self.stdout.write(self.style.SUCCESS(f'Successfully provisioned Super Admin "{username}".'))
            self.stdout.write(self.style.SUCCESS(f'You can now login at /login/ using these credentials.'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating Super Admin: {str(e)}'))
