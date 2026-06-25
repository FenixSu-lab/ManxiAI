"""Diagnose the configured embedding HTTP endpoint."""

import json
import logging
import socket
import time
from urllib.parse import urlparse, urlunparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from requests import RequestException

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Check TCP reachability, health URL, and OpenAI-compatible embeddings POST."""

    help = 'Diagnose EMBEDDING_API_URL reachability and OpenAI-compatible response shape.'

    def add_arguments(self, parser):
        """Register endpoint diagnostic options."""
        parser.add_argument(
            '--url',
            default='',
            help='Override EMBEDDING_API_URL for a one-off check.',
        )
        parser.add_argument(
            '--health-path',
            default='/health',
            help='Health path to test on the same scheme/host/port as the embedding URL.',
        )
        parser.add_argument(
            '--timeout',
            type=float,
            default=10.0,
            help='Network timeout in seconds for TCP and HTTP checks.',
        )
        parser.add_argument(
            '--warn-only',
            action='store_true',
            help='Print failures instead of exiting with an error.',
        )

    def handle(self, *args, **options):
        """Run endpoint diagnostics against the configured embedding service."""
        endpoint_url = options['url'] or settings.EMBEDDING_API_URL
        if not endpoint_url:
            raise CommandError('EMBEDDING_API_URL is empty.')

        timeout = options['timeout']
        parsed = urlparse(endpoint_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
            raise CommandError(f'Invalid embedding URL: {endpoint_url}')

        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        logger.info(
            'embedding_endpoint_check_start url=%s host=%s port=%s model=%s',
            endpoint_url,
            parsed.hostname,
            port,
            settings.EMBEDDING_MODEL,
        )

        try:
            tcp_ms = self._check_tcp(parsed.hostname, port, timeout)
            self.stdout.write(self.style.SUCCESS(f'TCP connect OK. host={parsed.hostname} port={port} latency_ms={tcp_ms}'))

            health_url = self._build_health_url(endpoint_url, options['health_path'])
            self._check_get(health_url, timeout)
            self._check_post_embeddings(endpoint_url, timeout)
        except CommandError as exc:
            if options['warn_only']:
                self.stdout.write(self.style.WARNING(str(exc)))
                return
            raise

        self.stdout.write(self.style.SUCCESS(f'Embedding endpoint OK. url={endpoint_url} model={settings.EMBEDDING_MODEL}'))
        logger.info('embedding_endpoint_check_success url=%s', endpoint_url)

    def _check_tcp(self, host: str, port: int, timeout: float) -> int:
        """Measure raw TCP connection latency before testing HTTP semantics."""
        started_at = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                pass
        except OSError as exc:
            logger.error('embedding_endpoint_tcp_failed host=%s port=%s error=%s', host, port, exc)
            raise CommandError(f'TCP connection failed. host={host} port={port} error={exc}') from exc
        return self._elapsed_ms(started_at)

    def _check_get(self, url: str, timeout: float) -> None:
        """Check whether the service exposes a basic HTTP health endpoint."""
        started_at = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout)
        except RequestException as exc:
            logger.error('embedding_endpoint_health_failed url=%s error=%s', url, exc)
            self.stdout.write(self.style.WARNING(f'Health GET failed. url={url} error={exc}'))
            return

        latency_ms = self._elapsed_ms(started_at)
        self.stdout.write(
            self.style.SUCCESS(
                f'Health GET responded. url={url} status={response.status_code} latency_ms={latency_ms}'
            )
        )

    def _check_post_embeddings(self, url: str, timeout: float) -> None:
        """POST one embedding request and verify OpenAI-compatible response shape."""
        payload = {
            'input': 'embedding endpoint runtime check',
            'model': settings.EMBEDDING_MODEL,
        }
        headers = {'Content-Type': 'application/json'}
        if getattr(settings, 'EMBEDDING_API_KEY', ''):
            headers['Authorization'] = f'Bearer {settings.EMBEDDING_API_KEY}'

        started_at = time.perf_counter()
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except RequestException as exc:
            logger.error('embedding_endpoint_post_failed url=%s error=%s', url, exc)
            raise CommandError(
                f'Embedding POST failed. url={url} error={exc}. '
                'The service must accept OpenAI-compatible POST /v1/embeddings JSON.'
            ) from exc
        except json.JSONDecodeError as exc:
            logger.error('embedding_endpoint_post_non_json url=%s error=%s', url, exc)
            raise CommandError(f'Embedding POST returned non-JSON response. url={url} error={exc}') from exc

        vector = self._extract_vector(data, url)
        if not vector:
            raise CommandError(f'Embedding POST returned an empty vector. url={url}')

        latency_ms = self._elapsed_ms(started_at)
        self.stdout.write(
            self.style.SUCCESS(
                f'Embedding POST OK. url={url} dimensions={len(vector)} latency_ms={latency_ms}'
            )
        )

    def _build_health_url(self, endpoint_url: str, health_path: str) -> str:
        """Build a health URL from the embedding endpoint scheme, host, and port."""
        parsed = urlparse(endpoint_url)
        path = health_path if health_path.startswith('/') else f'/{health_path}'
        return urlunparse((parsed.scheme, parsed.netloc, path, '', '', ''))

    def _extract_vector(self, data: dict, url: str) -> list[float]:
        """Extract the first vector from an OpenAI-compatible embeddings response."""
        try:
            return data['data'][0]['embedding']
        except (KeyError, IndexError, TypeError) as exc:
            keys = sorted(data.keys()) if isinstance(data, dict) else '<non-dict>'
            raise CommandError(
                f'Embedding POST response is not OpenAI-compatible. url={url} response_keys={keys}'
            ) from exc

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        """Return elapsed milliseconds since the provided monotonic timestamp."""
        return int((time.perf_counter() - started_at) * 1000)
