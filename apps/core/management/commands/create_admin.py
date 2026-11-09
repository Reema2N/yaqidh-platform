import getpass

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.core.models import Users


class Command(BaseCommand):
    help = 'Create the first administrator account for the Yaqidh platform.'

    def add_arguments(self, parser):
        parser.add_argument('--email', required=True)
        parser.add_argument('--name', default='System Admin')
        parser.add_argument('--phone', default='0500000000')
        parser.add_argument('--password', help='If omitted, you will be prompted.')

    def handle(self, *args, **options):
        email = options['email'].strip()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError('Invalid email address.')

        if Users.objects.filter(email=email).exists():
            raise CommandError(f'A user with email {email} already exists.')

        password = options['password']
        if not password:
            password = getpass.getpass('Password: ')
            if password != getpass.getpass('Password (again): '):
                raise CommandError('Passwords do not match.')

        if len(password) < 8:
            raise CommandError('Password must be at least 8 characters.')

        Users.objects.create(
            full_name=options['name'],
            email=email,
            password=make_password(password),
            phone=options['phone'],
            role='admin',
            status='active',
            must_change_password=False,
            phone_verified=True,
            created=timezone.now(),
        )
        self.stdout.write(self.style.SUCCESS(f'Admin account created for {email}.'))
