import itertools
import os
import random
from urllib.parse import quote_plus

from locust import HttpUser, LoadTestShape, between, task


_user_counter = itertools.count(1)


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class ExamDayStudentUser(HttpUser):
    """
    Simulates a student on exam-eve:
    - logs in
    - refreshes feed
    - checks notifications/groups
    - runs search
    - opens posts
    """

    wait_time = between(1, 5)

    # These are overwritten in on_start per user.
    username = ""
    password = ""

    # Candidate IDs to spread traffic across common objects.
    post_id_span = _env_int("POST_ID_SPAN", 3000)
    group_id_span = _env_int("GROUP_ID_SPAN", 300)

    def on_start(self):
        prefix = os.getenv("LOAD_USER_PREFIX", "student")
        password = os.getenv("LOAD_USER_PASSWORD", "Pass1234!")
        pool_size = _env_int("LOAD_USER_POOL_SIZE", 2000)

        idx = next(_user_counter)
        user_number = ((idx - 1) % max(pool_size, 1)) + 1
        self.username = f"{prefix}{user_number:04d}"
        self.password = password
        self._login()

    def _login(self):
        # 1) Get login page to initialize csrftoken cookie.
        self.client.get("/accounts/login/", name="auth.login.page")
        csrf = self.client.cookies.get("csrftoken", "")

        payload = {
            "username": self.username,
            "password": self.password,
            "csrfmiddlewaretoken": csrf,
            "next": "/",
        }
        headers = {"Referer": "/accounts/login/"}
        self.client.post(
            "/accounts/login/",
            data=payload,
            headers=headers,
            name="auth.login.submit",
            allow_redirects=True,
        )

    @task(30)
    def home_feed(self):
        self.client.get("/", name="feed.home")

    @task(20)
    def feed_next_page(self):
        page = random.randint(2, 10)
        self.client.get(f"/feed/page/?page={page}", name="feed.next_page")

    @task(10)
    def groups_dashboard(self):
        self.client.get("/groups/dashboard/", name="groups.dashboard")

    @task(10)
    def group_detail(self):
        group_id = random.randint(1, max(self.group_id_span, 1))
        self.client.get(f"/groups/{group_id}/", name="groups.detail")

    @task(10)
    def notifications(self):
        self.client.get("/notifications/", name="notifications.list")

    @task(8)
    def open_post(self):
        post_id = random.randint(1, max(self.post_id_span, 1))
        self.client.get(f"/post/{post_id}/", name="post.detail")

    @task(7)
    def search(self):
        term = random.choice(
            [
                "math",
                "exam",
                "revision",
                "group",
                "python",
                "signals",
                "assignment",
                "past paper",
            ]
        )
        self.client.get(f"/search/?q={quote_plus(term)}", name="search.query")

    @task(5)
    def unread_notification_count(self):
        self.client.get(
            "/notifications/unread-count/",
            headers={"X-Requested-With": "XMLHttpRequest"},
            name="notifications.unread_count",
        )


class ExamDayTwoThousandShape(LoadTestShape):
    """
    Ramp to 2,000 users in stages, hold peak, then recover.
    Override with env vars if needed.
    """

    stages = [
        # (seconds, users, spawn_rate)
        (120, 200, 20),
        (300, 500, 35),
        (600, 1000, 50),
        (900, 1500, 60),
        (1200, 2000, 80),
        (1800, 2000, 20),  # hold 10 minutes
        (2100, 500, 100),
        (2400, 0, 100),
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage_time, users, spawn_rate in self.stages:
            if run_time < stage_time:
                return (users, spawn_rate)
        return None
