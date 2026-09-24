#!/usr/bin/env bash
# Mesure le coût d'un job VFN (texte, images, total)
# Usage : ./scripts/measure_cost.sh <job_id>
# Lit VFN_SECRET et VFN_BASE depuis .env ou l'environnement
set -euo pipefail

# Auto-load .env from poc-annonces-n8n directory
ENV_FILE="$(cd "$(dirname "$0")/.." && pwd)/.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  . "$ENV_FILE"
  set +a
fi

BASE="${VFN_BASE:-https://178-105-102-54.sslip.io/webhook/vfn}"

if [ -z "${VFN_SECRET:-}" ]; then
  echo "Définis VFN_SECRET" >&2
  exit 1
fi

JOB_ID="${1:?Usage: $0 <job_id>}"

# Fetch and save response to tempfile
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

curl -sS --fail-with-body -H "X-VFN-Secret: ${VFN_SECRET}" "$BASE/job-status?id=$JOB_ID" > "$TMPFILE" || {
  echo "Erreur lors de la requête à $BASE/job-status?id=$JOB_ID" >&2
  exit 1
}

# Parse JSON response
python3 - "$TMPFILE" <<'PY'
import json
import sys

tmpfile = sys.argv[1]
try:
    with open(tmpfile, 'r') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    print(f"Erreur de parsing JSON: {e}", file=sys.stderr)
    sys.exit(1)

# Output main status line
statut = data.get("statut", "")
cout_texte = data.get("cout_texte", 0)
cout_images = data.get("cout_images", 0)
cout_total = data.get("cout_total", 0)
print(f"statut={statut} cout_texte={cout_texte} cout_images={cout_images} cout_total={cout_total}")

# Output plan details
plans = data.get("plans", [])
for plan in plans:
    plan_name = plan.get("plan", "")
    plan_cost = plan.get("cout", 0)
    plan_provider = plan.get("fournisseur", "")
    print(f"{plan_name} {plan_cost} {plan_provider}")
PY

