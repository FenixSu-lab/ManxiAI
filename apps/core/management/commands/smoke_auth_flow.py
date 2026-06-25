"""Smoke test the token authentication flow used by the SPA frontend."""

import logging
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.test.utils import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Verify registration, login, current-user lookup, and token revocation."""

    help = 'Smoke test SPA token auth without CSRF cookies or session authentication.'

    def add_arguments(self, parser):
        """Register command-line options."""
        parser.add_argument(
            '--origin',
            default='http://localhost:3000',
            help='Frontend Origin header to use for CSRF/CORS validation.',
        )
        parser.add_argument(
            '--keep',
            action='store_true',
            help='Keep the generated smoke-test user for inspection.',
        )

    def handle(self, *args, **options):
        """Run the token auth smoke flow and clean up generated rows."""
        origin = options['origin']
        keep = options['keep']
        suffix = uuid.uuid4().hex[:12]
        email = f'auth-smoke-{suffix}@example.com'
        username = f'auth-smoke-{suffix}'
        password = 'AuthSmokePass123!'

        client = APIClient(enforce_csrf_checks=True)
        logger.info('auth_smoke_start email=%s origin=%s keep=%s', email, origin, keep)

        with override_settings(
            ALLOWED_HOSTS=list({'testserver', *self._current_allowed_hosts()}),
            CSRF_TRUSTED_ORIGINS=list({origin, *self._current_csrf_origins()}),
        ):
            user_id = None
            try:
                self._register_user(client, origin, email, username, password)
                user = get_user_model().objects.get(email=email)
                user_id = user.id

                token = self._login(client, origin, email, password)
                self._read_current_user(client, token, email)
                self._logout(client, token)
                self._assert_token_revoked(client, token)

                self.stdout.write(self.style.SUCCESS(f'Auth smoke OK. email={email} origin={origin}'))
                logger.info('auth_smoke_success user_id=%s email=%s origin=%s', user_id, email, origin)
            finally:
                if user_id and not keep:
                    self._cleanup_user_rows(user_id)
                    logger.info('auth_smoke_cleanup user_id=%s email=%s', user_id, email)

    @staticmethod
    def _current_csrf_origins():
        """Return configured CSRF trusted origins without importing settings at module load time."""
        from django.conf import settings

        return getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])

    @staticmethod
    def _current_allowed_hosts():
        """Return configured allowed hosts without importing settings at module load time."""
        from django.conf import settings

        return getattr(settings, 'ALLOWED_HOSTS', [])

    def _register_user(self, client: APIClient, origin: str, email: str, username: str, password: str) -> None:
        """Register a new local account without sending a CSRF token."""
        response = client.post(
            '/api/v1/auth/users/',
            {
                'email': email,
                'username': username,
                'password': password,
                'confirm_password': password,
            },
            format='json',
            HTTP_ORIGIN=origin,
        )
        self._ensure_status(response, 201, 'register user')
        logger.info('auth_smoke_registered email=%s username=%s', email, username)

    def _login(self, client: APIClient, origin: str, email: str, password: str) -> str:
        """Log in without a CSRF token and return the issued DRF token."""
        response = client.post(
            '/api/v1/auth/users/login/',
            {'email': email, 'password': password},
            format='json',
            HTTP_ORIGIN=origin,
        )
        self._ensure_status(response, 200, 'login user')
        token = response.data.get('token')
        if not token:
            raise CommandError(f'Login did not return a token: {response.data}')
        logger.info('auth_smoke_login_ok email=%s token_prefix=%s', email, token[:8])
        return token

    def _read_current_user(self, client: APIClient, token: str, expected_email: str) -> None:
        """Read the current user with token authentication."""
        response = client.get('/api/v1/auth/users/me/', HTTP_AUTHORIZATION=f'Token {token}')
        self._ensure_status(response, 200, 'read current user')
        if response.data.get('email') != expected_email:
            raise CommandError(f'Current-user payload returned wrong email: {response.data}')
        logger.info('auth_smoke_me_ok email=%s', expected_email)

    def _logout(self, client: APIClient, token: str) -> None:
        """Revoke the token through the logout endpoint."""
        response = client.post('/api/v1/auth/users/logout/', HTTP_AUTHORIZATION=f'Token {token}')
        self._ensure_status(response, 200, 'logout user')
        logger.info('auth_smoke_logout_ok token_prefix=%s', token[:8])

    def _assert_token_revoked(self, client: APIClient, token: str) -> None:
        """Ensure the revoked token can no longer access authenticated routes."""
        if Token.objects.filter(key=token).exists():
            raise CommandError('Logout did not delete the token row.')

        response = client.get('/api/v1/auth/users/me/', HTTP_AUTHORIZATION=f'Token {token}')
        self._ensure_status(response, 401, 'verify revoked token')
        logger.info('auth_smoke_token_revoked token_prefix=%s', token[:8])

    def _cleanup_user_rows(self, user_id) -> None:
        """Remove smoke auth rows without cascading through unrelated app tables."""
        table_names = set(connection.introspection.table_names())
        cleanup_tables = [
            ('authtoken_token', 'user_id'),
            ('user_profiles', 'user_id'),
            (get_user_model()._meta.db_table, 'id'),
        ]

        with connection.cursor() as cursor:
            for table_name, column_name in cleanup_tables:
                if table_name in table_names:
                    cursor.execute(f'DELETE FROM {table_name} WHERE {column_name} = %s', [str(user_id)])

    @staticmethod
    def _ensure_status(response, expected_status: int, step: str) -> None:
        """Raise a command error with response details when a smoke step fails."""
        if response.status_code != expected_status:
            data = getattr(response, 'data', None)
            if data is None:
                data = response.content.decode('utf-8', errors='replace')[:500]
            raise CommandError(f'Auth smoke failed during {step}: status={response.status_code} data={data}')
