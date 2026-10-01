# PwaniNet performance test kit

This kit separates the two timing questions:

- **Browser navigation probe:** records HTMX request, response, swap, settle, next-paint timings, long main-thread tasks, and `Server-Timing` headers for a few manual clicks.
- **Locust load profile:** signs in unique staging test accounts and generates authenticated Home, Profile, and Groups HTMX navigation traffic. The default target guard refuses the production app and CDN hostnames.

Do not run a load test against production. Use an isolated staging environment with representative data and adequate monitoring.

## 1. Enable server timing

Deploy this branch to staging, then set:

```text
PERFORMANCE_TIMING_ENABLED=1
```

Restart the web app. Each response will include `Server-Timing` and `X-Request-ID` headers. Application logs will include one `performance` line per request with total app time, cumulative database time, and query count. This timing excludes static files served directly by WhiteNoise, Nginx, or the CDN; browser Resource Timing covers those.

Turn the flag off after measurement. Avoid leaving per-request INFO timing logs enabled during normal traffic.

## 2. Prepare test users

Create at least as many dedicated test accounts as virtual users. For a 60-user run, use 60 unique accounts with:

- 2FA disabled, completed onboarding, and permission to access Home, Profile, and Groups.
- No access to real user data or privileged roles.
- Profile data and related rows appropriate for the staging dataset.

Save their credentials locally in `tests/performance/users.csv` with this format; do not commit or paste the file into chat:

```csv
username,password
perf_student_001,replace-with-local-secret
perf_student_002,replace-with-local-secret
```

The load script rejects duplicate usernames and fails if the requested virtual-user count exceeds the number of accounts.

## 3. Run Locust from the repository root

Use a staging URL and a gradual ramp. For a first 60-user run:

```bash
PERF_USERS_FILE=tests/performance/users.csv locust -f tests/performance/locustfile.py --host https://YOUR-STAGING-HOST --users 60 --spawn-rate 5 --run-time 8m --headless --csv tests/performance/results/nav-60
```

If you prefer the Locust web interface, omit `--headless`, `--run-time`, and `--csv`, then open `http://localhost:8089`. Set users to 60 and spawn rate to 5. Run from one Locust process; the test credential pool is intentionally not shared across distributed workers.

Run a smaller 5-user / 2-minute warm-up first. Stop if staging starts returning errors, the database or Redis saturates, or the environment affects anyone outside the test. Let the target rest between runs so cache state is clear.

The CSV report files are ignored by Git. Preserve the reports and note the staging build, database snapshot/date, run time, virtual-user count, spawn rate, and cache state for comparison.

## 4. Measure browser rendering

Use a normal browser signed into a staging test account (one user is enough):

1. Open DevTools Console and paste the contents of `tests/performance/browser_probe.js`.
2. Click Home, Profile, and Groups a few times, including one cold load if relevant.
3. Run `PwaniNetPerfProbe.download()` in the Console.
4. Keep the downloaded JSON together with the matching Locust and server logs.

The JSON contains URLs, timings, browser details, response byte lengths, request IDs, and long-task durations. Review it before sharing; it may reveal the test username and staging route names.

## 5. What to return for analysis

Send the Locust summary or CSV files, matching `performance` log lines, and the browser JSON. Include whether the run used cold or warm caches and the deployed web/DB/Redis instance sizes. Do not send passwords, cookies, session IDs, or production secrets.
