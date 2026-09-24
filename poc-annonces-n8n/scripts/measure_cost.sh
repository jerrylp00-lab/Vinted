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

curl -sf -H "X-VFN-Secret: ${VFN_SECRET}" "$BASE/job-status?id=$JOB_ID" \
  | python3 -c 'import json,sys; j=json.load(sys.stdin); print(f"statut={j.get(\"statut\")}, cout_texte={j.get(\"cout_texte\")}, cout_images={j.get(\"cout_images\")}, cout_total={j.get(\"cout_total\")}"); print("plans:"); [print(f"  {p[\"plan\"]}: {p.get(\"cout\")} ({p.get(\"fournisseur\")})") for p in j.get("plans",[])]'
