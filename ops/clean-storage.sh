#!/usr/bin/env bash
#
# Storage maintenance for the Pwaninet production VM.
#
# Only regenerable artefacts are removed: Docker build cache, dangling
# images, stopped containers, the apt cache, old journal entries and expired
# database backups. Application data (Postgres, media, uploads, the live
# database backups) is never touched.
#
set -uo pipefail

COMPOSE_FILE="/srv/prod-app/src/docker-compose.prod.yml"
BACKUP_DIR="/srv/prod-app/backups"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
DRY_RUN=false

usage() {
  cat <<'EOF'
Usage: ops-clean [--dry-run]

  --dry-run   Show what would be reclaimed without deleting anything.

Reclaims:
  - Docker build cache (the biggest win: ~3.7 GB after a deploy)
  - Dangling (untagged) Docker images
  - Stopped containers
  - apt package cache
  - systemd journal entries beyond 50 MB
  - Database backups older than BACKUP_KEEP_DAYS (default 14)
EOF
}

for arg in "$@"; do
  case "$arg" in
    --dry-run|-n) DRY_RUN=true ;;
    --help|-h) usage; exit 0 ;;
    *) echo "[!] Unknown argument: $arg"; usage; exit 1 ;;
  esac
done

run() {
  if $DRY_RUN; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

disk_before=$(df -h / | awk 'NR==2 {print $4}')
used_before=$(df -h / | awk 'NR==2 {print $3}')

echo "=================================================="
echo " [vasto] storage cleanup"
echo "=================================================="
echo "[i] Disk before: ${used_before} used, ${disk_before} free"
echo ""

echo "[1/5] Docker build cache"
docker builder prune -af 2>&1 | tail -2

echo ""
echo "[2/5] Dangling Docker images"
docker image prune -f 2>&1 | tail -2

echo ""
echo "[3/5] Stopped containers"
docker container prune -f 2>&1 | tail -2

echo ""
echo "[4/5] apt cache and journal"
run sudo apt-get clean -y
run sudo journalctl --vacuum-size=50M

echo ""
echo "[5/5] Database backups older than ${BACKUP_KEEP_DAYS} days"
if [ -d "$BACKUP_DIR" ]; then
  old_backups=$(find "$BACKUP_DIR" -name '*.sql.gz' -type f -mtime "+${BACKUP_KEEP_DAYS}" 2>/dev/null)
  if [ -z "$old_backups" ]; then
    echo "[i] No backups older than ${BACKUP_KEEP_DAYS} days."
  else
    echo "$old_backups" | while read -r f; do
      if $DRY_RUN; then
        echo "[dry-run] would remove $f ($(du -h "$f" | cut -f1))"
      else
        rm -f "$f" && echo "[+] removed $f"
      fi
    done
  fi
else
  echo "[i] No backup directory at ${BACKUP_DIR}."
fi

echo ""
echo "=================================================="
echo " [vasto] storage summary"
echo "=================================================="
df -h / | tail -1
echo ""
docker system df
echo ""
echo "[i] Largest directories on /"
sudo du -xh --max-depth=1 / 2>/dev/null | sort -rh | head -6
echo "=================================================="
