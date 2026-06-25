"""Check database connectivity and connection latency for local diagnostics."""

import logging
import socket
import time

import psycopg2
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Measure database connection and query latency for the configured backend."""

    help = 'Check database connectivity, PostgreSQL handshake latency, and query latency.'

    def add_arguments(self, parser):
        """Register latency threshold options."""
        parser.add_argument(
            '--max-connect-ms',
            type=int,
            default=3000,
            help='Maximum acceptable PostgreSQL connection latency in milliseconds.',
        )
        parser.add_argument(
            '--max-query-ms',
            type=int,
            default=500,
            help='Maximum acceptable SELECT 1 query latency in milliseconds.',
        )
        parser.add_argument(
            '--warn-only',
            action='store_true',
            help='Print warnings instead of failing when thresholds are exceeded.',
        )
        parser.add_argument(
            '--compare-client-modes',
            action='store_true',
            help='Compare common libpq sslmode/gssencmode combinations for slow connection diagnosis.',
        )

    def handle(self, *args, **options):
        """Run latency checks for the configured Django database."""
        database = settings.DATABASES['default']
        engine = database['ENGINE']
        logger.info('db_latency_check_start engine=%s', engine)

        if 'postgresql' not in engine:
            query_ms = self._measure_django_query()
            self.stdout.write(self.style.WARNING(f'Non-PostgreSQL engine={engine}; only Django query latency checked.'))
            self.stdout.write(self.style.SUCCESS(f'Django query OK. query_ms={query_ms}'))
            return

        host = database.get('HOST') or 'localhost'
        port = int(database.get('PORT') or 5432)
        tcp_ms = self._measure_tcp_connect(host, port)
        connect_ms = self._measure_postgres_connect(database)
        query_ms = self._measure_django_query()
        reuse_query_ms = self._measure_django_query()

        self.stdout.write(self.style.SUCCESS(f'TCP connect OK. host={host} port={port} latency_ms={tcp_ms}'))
        self.stdout.write(
            self.style.SUCCESS(
                f'PostgreSQL handshake OK. latency_ms={connect_ms} '
                f'options={self._safe_option_summary(database)}'
            )
        )
        self.stdout.write(self.style.SUCCESS(f'Django query OK. first_query_ms={query_ms} reuse_query_ms={reuse_query_ms}'))
        logger.info(
            'db_latency_check_result host=%s port=%s tcp_ms=%s connect_ms=%s query_ms=%s reuse_query_ms=%s',
            host,
            port,
            tcp_ms,
            connect_ms,
            query_ms,
            reuse_query_ms,
        )

        if options['compare_client_modes']:
            self._compare_client_modes(database)

        self._enforce_threshold(
            label='PostgreSQL connection',
            actual_ms=connect_ms,
            max_ms=options['max_connect_ms'],
            warn_only=options['warn_only'],
        )
        self._enforce_threshold(
            label='Django query',
            actual_ms=query_ms,
            max_ms=options['max_query_ms'],
            warn_only=options['warn_only'],
        )

    def _measure_tcp_connect(self, host: str, port: int) -> int:
        """Measure raw TCP connection time to the configured database host."""
        started_at = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=10):
                pass
        except OSError as exc:
            logger.exception('db_latency_tcp_failed host=%s port=%s error=%s', host, port, exc)
            raise CommandError(f'TCP connection to database failed: host={host} port={port} error={exc}') from exc
        return self._elapsed_ms(started_at)

    def _measure_postgres_connect(self, database: dict) -> int:
        """Measure psycopg2 connection time, including PostgreSQL authentication."""
        started_at = time.perf_counter()
        try:
            conn = psycopg2.connect(**self._postgres_connect_params(database))
            conn.close()
        except Exception as exc:
            logger.exception('db_latency_postgres_connect_failed error=%s', exc)
            raise CommandError(f'PostgreSQL connection failed: {exc}') from exc
        return self._elapsed_ms(started_at)

    def _postgres_connect_params(self, database: dict, extra_options: dict | None = None) -> dict:
        """Build psycopg2 connection parameters from Django settings without logging secrets."""
        options = dict(database.get('OPTIONS') or {})
        if extra_options:
            options.update(extra_options)
        params = {
            'dbname': database['NAME'],
            'user': database['USER'],
            'password': database.get('PASSWORD', ''),
            'host': database.get('HOST') or 'localhost',
            'port': database.get('PORT') or 5432,
            'connect_timeout': options.pop('connect_timeout', 30),
        }
        params.update(options)
        return params

    def _compare_client_modes(self, database: dict) -> None:
        """Print connection latency for common libpq SSL/GSS mode combinations."""
        variants = [
            {'sslmode': 'prefer'},
            {'sslmode': 'disable'},
            {'sslmode': 'prefer', 'gssencmode': 'disable'},
            {'sslmode': 'disable', 'gssencmode': 'disable'},
        ]
        self.stdout.write('Client mode comparison:')
        for variant in variants:
            label = ' '.join(f'{key}={value}' for key, value in variant.items())
            started_at = time.perf_counter()
            try:
                conn = psycopg2.connect(**self._postgres_connect_params(database, variant))
                conn.close()
                latency_ms = self._elapsed_ms(started_at)
                self.stdout.write(self.style.SUCCESS(f'  {label} latency_ms={latency_ms}'))
            except Exception as exc:
                latency_ms = self._elapsed_ms(started_at)
                self.stdout.write(self.style.WARNING(f'  {label} failed latency_ms={latency_ms} error={exc}'))
                logger.warning('db_latency_client_mode_failed label=%s latency_ms=%s error=%s', label, latency_ms, exc)

    def _safe_option_summary(self, database: dict) -> str:
        """Return non-secret libpq options that influence PostgreSQL connection latency."""
        options = dict(database.get('OPTIONS') or {})
        allowed_keys = ['connect_timeout', 'sslmode', 'gssencmode', 'application_name']
        return ','.join(f'{key}={options.get(key)}' for key in allowed_keys if key in options) or 'none'

    def _measure_django_query(self) -> int:
        """Measure a simple query through Django's configured connection."""
        started_at = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        return self._elapsed_ms(started_at)

    def _enforce_threshold(self, label: str, actual_ms: int, max_ms: int, warn_only: bool) -> None:
        """Warn or fail when measured latency exceeds the configured threshold."""
        if actual_ms <= max_ms:
            return

        message = f'{label} latency is high: {actual_ms}ms > {max_ms}ms.'
        logger.warning('db_latency_threshold_exceeded label=%s actual_ms=%s max_ms=%s', label, actual_ms, max_ms)
        if warn_only:
            self.stdout.write(self.style.WARNING(message))
            return
        raise CommandError(message)

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        """Return elapsed milliseconds since the provided monotonic timestamp."""
        return int((time.perf_counter() - started_at) * 1000)
