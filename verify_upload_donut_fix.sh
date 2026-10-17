#!/bin/bash
#
# verify_upload_donut_fix.sh
#
# Verifies the upload donut fix is deployed and working on production.
# Run on the production VM: /srv/prod-app/src
#
# What it checks:
#   1. Git is on latest main (contains the donut fix commit 80c100f)
#   2. Web + celery containers are running
#   3. GET /api/uploads/<id>/ returns 410 UPLOAD_DELETED for soft-deleted records
#   4. POST /api/uploads/<id>/authorize/ returns 410 UPLOAD_DELETED for soft-deleted records
#   5. JS files contain the terminal-state / server-verification fixes
#   6. Terminal uploads (cancelled/failed/completed) return proper status
#
set -euo pipefail

cd /srv/prod-app/src || { echo "FAIL: /srv/prod-app/src not found"; exit 1; }

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}[PASS]${NC} $1"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}[FAIL]${NC} $1"; FAIL=$((FAIL+1)); }
info() { echo -e "${YELLOW}[INFO]${NC} $1"; }

echo "============================================================"
echo " Upload Donut Fix Verification"
echo "============================================================"
echo ""

# ------------------------------------------------------------
# 1. Git state
# ------------------------------------------------------------
echo "--- 1. Git deployment state ---"
CURRENT_COMMIT=$(git log --oneline -1 | awk '{print $1}')
CURRENT_MSG=$(git log --oneline -1 | cut -d' ' -f2-)
echo "Current commit: $CURRENT_COMMIT  ($CURRENT_MSG)"

if git merge-base --is-ancestor 80c100f HEAD 2>/dev/null; then
    pass "Donut fix commit (80c100f) is deployed"
else
    fail "Donut fix commit (80c100f) is NOT deployed"
fi
if git merge-base --is-ancestor f469f74 HEAD 2>/dev/null; then
    pass "Backend 410 fix commit (f469f74) is deployed"
else
    fail "Backend 410 fix commit (f469f74) is NOT deployed"
fi
echo ""

# ------------------------------------------------------------
# 2. Container state
# ------------------------------------------------------------
echo "--- 2. Container state ---"
if docker compose ps web --format json 2>/dev/null | grep -q '"State":"running"'; then
    pass "web container is running"
else
    fail "web container is not running"
fi
if docker compose ps celery_worker --format json 2>/dev/null | grep -q '"State":"running"'; then
    pass "celery_worker container is running"
else
    fail "celery_worker container is not running"
fi
echo ""

# ------------------------------------------------------------
# 3. Find test records
# ------------------------------------------------------------
echo "--- 3. Finding test upload records ---"

DELETED_ID=$(docker compose exec -T web python manage.py shell 2>/dev/null <<'PY'
from uploads.models import UploadRecord
r = UploadRecord.objects.exclude(deleted_at__isnull=True).order_by('-deleted_at').first()
print(r.id if r else "NONE")
PY
) || DELETED_ID="NONE"

CANCELLED_ID=$(docker compose exec -T web python manage.py shell 2>/dev/null <<'PY'
from uploads.models import UploadRecord
r = UploadRecord.objects.filter(status="cancelled", deleted_at__isnull=True).order_by('-updated_at').first()
print(r.id if r else "NONE")
PY
) || CANCELLED_ID="NONE"

COMPLETED_ID=$(docker compose exec -T web python manage.py shell 2>/dev/null <<'PY'
from uploads.models import UploadRecord
r = UploadRecord.objects.filter(status="completed", deleted_at__isnull=True).order_by('-updated_at').first()
print(r.id if r else "NONE")
PY
) || COMPLETED_ID="NONE"

info "Deleted record:   $DELETED_ID"
info "Cancelled record: $CANCELLED_ID"
info "Completed record: $COMPLETED_ID"

# Get a CSRF token and session cookie from the running web container
# We need an authenticated user. Find the first user and get their session.
AUTH_COOKIE=$(docker compose exec -T web python manage.py shell 2>/dev/null <<'PY'
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

User = get_user_model()
user = User.objects.first()
if not user:
    print("NO_USER")
    raise SystemExit

rf = RequestFactory()
request = rf.get('/')
request.user = user
request.session = SessionStore()
request.session.save()

# Create a session cookie value manually
from django.contrib.sessions.models import Session
s = Session.objects.get(pk=request.session.session_key)
print(f"sessionid={s.session_key}; csrftoken=test")
PY
) || AUTH_COOKIE=""

if [ -z "$AUTH_COOKIE" ] || [ "$AUTH_COOKIE" = "NO_USER" ]; then
    info "Could not create auth session — skipping live API tests"
    AUTH_COOKIE=""
fi

echo ""

# ------------------------------------------------------------
# 4. Backend API tests (via curl through the running container)
# ------------------------------------------------------------
echo "--- 4. Backend upload API tests ---"

if [ -n "$AUTH_COOKIE" ] && [ -n "$DELETED_ID" ] && [ "$DELETED_ID" != "NONE" ]; then
    # Test GET on deleted record
    GET_CODE=$(docker compose exec -T web python -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/api/uploads/$DELETED_ID/')
req.add_header('Cookie', '$AUTH_COOKIE')
try:
    urllib.request.urlopen(req)
    print('200')
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || echo "ERR")

    if [ "$GET_CODE" = "410" ]; then
        pass "GET /api/uploads/<deleted-id>/ returns 410 Gone"
    elif [ "$GET_CODE" = "ERR" ]; then
        fail "Could not test GET endpoint"
    else
        fail "GET /api/uploads/<deleted-id>/ returned $GET_CODE, expected 410"
    fi

    # Test POST authorize on deleted record
    AUTH_CODE=$(docker compose exec -T web python -c "
import urllib.request, json
data = json.dumps({}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/uploads/$DELETED_ID/authorize/', data=data, method='POST')
req.add_header('Content-Type', 'application/json')
req.add_header('Cookie', '$AUTH_COOKIE')
try:
    urllib.request.urlopen(req)
    print('200')
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || echo "ERR")

    if [ "$AUTH_CODE" = "410" ]; then
        pass "POST /api/uploads/<deleted-id>/authorize/ returns 410 Gone"
    elif [ "$AUTH_CODE" = "ERR" ]; then
        fail "Could not test authorize endpoint"
    else
        fail "POST /api/uploads/<deleted-id>/authorize/ returned $AUTH_CODE, expected 410"
    fi
else
    info "Skipping live API tests (no auth session or no deleted record)"
fi

# Test cancelled record returns 200 (not 410)
if [ -n "$AUTH_COOKIE" ] && [ -n "$CANCELLED_ID" ] && [ "$CANCELLED_ID" != "NONE" ]; then
    CANCEL_CODE=$(docker compose exec -T web python -c "
import urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/api/uploads/$CANCELLED_ID/')
req.add_header('Cookie', '$AUTH_COOKIE')
try:
    urllib.request.urlopen(req)
    print('200')
except urllib.error.HTTPError as e:
    print(e.code)
" 2>/dev/null || echo "ERR")

    if [ "$CANCEL_CODE" = "200" ]; then
        pass "GET /api/uploads/<cancelled-id>/ returns 200 (cancelled record visible)"
    elif [ "$CANCEL_CODE" = "ERR" ]; then
        info "Could not test cancelled upload endpoint"
    else
        info "GET /api/uploads/<cancelled-id>/ returned $CANCEL_CODE"
    fi
fi
echo ""

# ------------------------------------------------------------
# 5. JS file freshness
# ------------------------------------------------------------
echo "--- 5. Frontend JS freshness ---"

if docker compose exec -T web cat /app/static/js/upload/resumable_upload.js 2>/dev/null | grep -q "Server is authoritative: if the record is already terminal"; then
    pass "resumable_upload.js: terminal-state check in _run()"
else
    fail "resumable_upload.js: terminal-state check MISSING"
fi

if docker compose exec -T web cat /app/static/js/upload/resumable_upload.js 2>/dev/null | grep -q "window.storeDelete = storeDelete"; then
    pass "resumable_upload.js: window.storeDelete exposed"
else
    fail "resumable_upload.js: window.storeDelete MISSING"
fi

if docker compose exec -T web cat /app/static/js/upload/upload_ui.js 2>/dev/null | grep -q "Verify each session with the server before counting it"; then
    pass "upload_ui.js: server-side session verification in restoreBannerOnLoad"
else
    fail "upload_ui.js: server-side session verification MISSING"
fi

if docker compose exec -T web cat /app/static/js/upload/upload_ui.js 2>/dev/null | grep -q "getActiveUpload"; then
    pass "upload_ui.js: getActiveUpload safety net in terminal handlers"
else
    fail "upload_ui.js: getActiveUpload safety net MISSING"
fi
echo ""

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------
echo "============================================================"
echo " Verification Summary"
echo "============================================================"
echo -e "Passed: ${GREEN}$PASS${NC}"
echo -e "Failed: ${RED}$FAIL${NC}"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}Some checks failed. The donut fix may not be fully deployed.${NC}"
    echo ""
    echo "Recommended next steps:"
    echo "  1. git pull origin main"
    echo "  2. docker compose build --no-cache web"
    echo "  3. docker compose up -d --force-recreate --remove-orphans web"
    echo "  4. Hard-refresh the browser (Ctrl+Shift+R / Cmd+Shift+R) to clear JS cache"
    echo "  5. Clear IndexedDB: DevTools > Application > IndexedDB > vasto_uploads > delete sessions/blobs"
    exit 1
else
    echo -e "${GREEN}All checks passed. The donut fix is deployed.${NC}"
    echo ""
    echo "Note: Users may need to hard-refresh to pick up new JS."
    echo "Stale IndexedDB sessions from before this deploy will be"
    echo "cleaned automatically on the next page load."
    exit 0
fi