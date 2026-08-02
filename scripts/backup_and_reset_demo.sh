#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "--confirm" ]]; then
  echo "Usage: scripts/backup_and_reset_demo.sh --confirm" >&2
  echo "Moves local demo data into a recoverable .demo-backups directory." >&2
  exit 1
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
timestamp="$(date +%Y%m%d-%H%M%S)"
backup_root="$project_root/.demo-backups/$timestamp"
mkdir -p "$backup_root"

for relative_path in surveillance.db uploads policies reports; do
  target="$project_root/$relative_path"
  if [[ -e "$target" ]]; then
    mv "$target" "$backup_root/"
  fi
done

echo "Demo data moved to $backup_root"
echo "Restart the backend to create a fresh database."
