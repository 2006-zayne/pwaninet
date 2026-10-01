"""Authenticated HTMX navigation load profile for an isolated staging system."""

import csv
import os
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from locust import HttpUser, between, events, task


def load_test_users():
    users_path = os.environ.get('PERF_USERS_FILE', '')
    if not users_path:
        raise RuntimeError('Set PERF_USERS_FILE to a local CSV with username,password columns.')

    path = Path(users_path).expanduser()
    if not path.is_file():
        raise RuntimeError(f'Performance user CSV does not exist: {path}')

    with path.open(newline='', encoding='utf-8-sig') as source:
        rows = [
            {'username': row.get('username', '').strip(), 'password': row.get('password', '')}
            for row in csv.DictReader(source)
        ]

    rows = [row for row in rows if row['username'] and row['password']]
    if not rows:
        raise RuntimeError('Performance user CSV has no usable username,password rows.')
    if len({row['username'] for row in rows}) != len(rows):
        raise RuntimeError('Performance user CSV must contain a unique account per virtual user.')
    return deque(rows)


TEST_USERS = load_test_users()


def enforce_nonproduction_target(host):
    hostname = (urlparse(host or '').hostname or '').lower()
    is_production = hostname in {'pwaninet.app', 'www.pwaninet.app', 'cdn.pwaninet.app'}
    if is_production and os.environ.get('PERF_ALLOW_PRODUCTION', '').lower() not in ('1', 'true', 'yes'):
        raise RuntimeError(
            'Refusing to load-test pwaninet.app. Use an isolated staging host; '
            'production requires PERF_ALLOW_PRODUCTION=1.'
        )


@events.test_start.add_listener
def validate_run(environment, **kwargs):
    global TEST_USERS
    TEST_USERS = load_test_users()
    enforce_nonproduction_target(environment.host)
    requested_users = environment.parsed_options.num_users if environment.parsed_options else None
    if requested_users and requested_users > len(TEST_USERS):
        raise RuntimeError(
            f'This run requests {requested_users} virtual users but only {len(TEST_USERS)} '
            'unique accounts are available in PERF_USERS_FILE.'
        )


class PwaniNetNavigationUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        enforce_nonproduction_target(self.host)
        try:
            self.credentials = TEST_USERS.popleft()
        except IndexError as exc:
            raise RuntimeError('Not enough unique test accounts for the configured virtual-user count.') from exc

        login_page = self.client.get('/login/?next=/', name='Auth setup · login page')
        if login_page.status_code != 200:
            raise RuntimeError(f'Could not open login page (HTTP {login_page.status_code}).')

        import re
        csrf_match = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]+)"', login_page.text)
        if not csrf_match:
            raise RuntimeError('Could not find Django CSRF token on login page.')

        login_url = f"{self.host.rstrip('/')}/login/"
        login_response = self.client.post(
            '/login/',
            data={
                'username': self.credentials['username'],
                'password': self.credentials['password'],
                'csrfmiddlewaretoken': csrf_match.group(1),
                'device_id': '',
                'next': '/',
            },
            headers={'Referer': login_url},
            name='Auth setup · submit login',
            allow_redirects=True,
        )
        final_path = urlparse(login_response.url).path
        if '/login/2fa' in final_path:
            raise RuntimeError(f"Test account {self.credentials['username']} has 2FA enabled; use a staging test account without 2FA.")
        if login_response.status_code >= 400 or final_path in ('/login/', '/accounts/login/'):
            raise RuntimeError(f"Test account {self.credentials['username']} could not sign in (HTTP {login_response.status_code}).")

        self.current_path = '/'

    def navigate(self, path, route_name):
        origin = self.host.rstrip('/')
        with self.client.get(
            path,
            headers={
                'HX-Request': 'true',
                'HX-Target': 'page-content-target',
                'HX-Current-URL': f'{origin}{self.current_path}',
            },
            name=route_name,
            catch_response=True,
        ) as response:
            final_path = urlparse(response.url).path
            content_type = response.headers.get('Content-Type', '')
            if response.status_code != 200:
                response.failure(f'HTTP {response.status_code}')
            elif '/login/' in final_path or '/accounts/login/' in final_path:
                response.failure('Session expired or authentication was not established')
            elif 'text/html' not in content_type:
                response.failure(f'Expected HTML, received {content_type}')
            else:
                self.current_path = path
                response.success()

    @task(5)
    def home_feed(self):
        self.navigate('/', 'Navigation · home feed')

    @task(3)
    def own_profile(self):
        username = self.credentials['username']
        self.navigate(f'/users/user/{username}/', 'Navigation · own profile')

    @task(2)
    def groups_dashboard(self):
        self.navigate('/groups/dashboard/', 'Navigation · groups dashboard')
