# Exam-Day Load Simulation (2,000 Students)

This guide runs a realistic load simulation for **about 2,000 concurrent students** one day before exams.

## What this test simulates

Traffic mix from logged-in students:

- home feed refreshes
- infinite feed pagination (`/feed/page/`)
- notifications list and unread badge polling
- groups dashboard and group detail visits
- post detail opens
- search activity

Implemented with Locust profile: `loadtesting/locustfile.py`.

## Prerequisites

1. Use your project virtual environment.
2. Install app dependencies + Locust:

```bash
pip install -r requirements.txt
pip install locust
```

3. Ensure test accounts exist using this pattern:
   - usernames: `student0001` ... `student2000`
   - same password for all (default in profile: `Pass1234!`)
4. Start the Django app so Locust can hit it (example):

```bash
python manage.py runserver 0.0.0.0:8000
```

## Run the simulation

From the `pwaninet` directory:

```bash
LOAD_USER_PREFIX=student \
LOAD_USER_PASSWORD='Pass1234!' \
LOAD_USER_POOL_SIZE=2000 \
POST_ID_SPAN=3000 \
GROUP_ID_SPAN=300 \
locust -f loadtesting/locustfile.py --host http://127.0.0.1:8000
```

Open Locust UI at `http://127.0.0.1:8089` and start test.

The built-in shape ramps to 2,000 users and holds peak traffic.

## Headless run (CI or scripted)

```bash
LOAD_USER_PREFIX=student \
LOAD_USER_PASSWORD='Pass1234!' \
LOAD_USER_POOL_SIZE=2000 \
locust -f loadtesting/locustfile.py \
  --host http://127.0.0.1:8000 \
  --headless \
  --csv exam_day_2k \
  --run-time 40m
```

This exports:

- `exam_day_2k_stats.csv`
- `exam_day_2k_failures.csv`
- `exam_day_2k_stats_history.csv`

## Readiness thresholds (suggested)

Treat exam readiness as pass when:

- p95 response time under 800ms on core pages
- error rate below 1%
- no sustained 5xx spikes during 2,000-user hold phase

## Notes

- First run locally at 200-500 users, then 1,000, then 2,000.
- If login fails heavily, verify account pool and password.
- If many 404s on `post/<id>` or `groups/<id>`, adjust `POST_ID_SPAN` and `GROUP_ID_SPAN` to match your seeded data.
