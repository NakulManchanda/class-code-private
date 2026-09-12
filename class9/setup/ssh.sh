#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  source "$ROOT/.env"
  set +a
fi
exec ssh -i "$LAMBDA_SSH_KEY" -o StrictHostKeyChecking=accept-new -t "$LAMBDA" \
  'mkdir -p ~/class9; cd ~/class9; exec bash -l'
