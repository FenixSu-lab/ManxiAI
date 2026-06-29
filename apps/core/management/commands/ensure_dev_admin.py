"""Create or update a local administrator account for diagnostics."""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Ensure a known admin account exists for local troubleshooting."""

    help = 'Create or update a superuser account for local diagnostics.'

    DEFAULT_EMAIL = 'admin@example.com'
    DEFAULT_USERNAME = 'admin'
    DEFAULT_PASSWORD = 'Admin123!'

    def add_arguments(self, parser):
        """Register admin account options."""
        parser.add_argument('--email', default=self.DEFAULT_EMAIL, help='Admin email address.')
        parser.add_argument('--username', default=self.DEFAULT_USERNAME, help='Admin username.')
        parser.add_argument('--password', default='', help='Admin password. Required outside DEBUG mode.')
        parser.add_argument(
            '--allow-default-password',
            action='store_true',
            help='Allow the built-in development password outside DEBUG mode.',
        )

    def handle(self, *args, **options):
        """Create or update the requested administrator and issue a DRF token."""
        email = options['email'].strip().lower()
        username = options['username'].strip()
        password = options['password'] or self.DEFAULT_PASSWORD
        self._validate_inputs(email, username, password, options['allow_default_password'])

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(email=email, defaults={'username': username})
        user.username = username
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        token, _ = Token.objects.get_or_create(user=user)
        logger.info(
            'dev_admin_ensured user_id=%s email=%s created=%s is_staff=%s is_superuser=%s',
            user.id,
            user.email,
            created,
            user.is_staff,
            user.is_superuser,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Admin ready. created={created} email={user.email} username={user.username} '
                f'is_staff={user.is_staff} is_superuser={user.is_superuser} token_prefix={token.key[:8]}'
            )
        )

    def _validate_inputs(
        self,
        email: str,
        username: str,
        password: str,
        allow_default_password: bool,
    ) -> None:
        """Validate admin bootstrap inputs before writing to the database."""
        if not email:
            raise CommandError('Admin email cannot be empty.')
        if not username:
            raise CommandError('Admin username cannot be empty.')
        if not settings.DEBUG and password == self.DEFAULT_PASSWORD and not allow_default_password:
            raise CommandError('Refusing to use the default development password when DEBUG=False.')
