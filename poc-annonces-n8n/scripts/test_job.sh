#!/usr/bin/env bash
# Test de bout en bout de l'étape 2 : crée une fiche depuis des photos, puis interroge son statut.
# Usage : VFN_SECRET=<secret> ./scripts/test_job.sh <genre> <type> photo1.jpg [photo2.jpg ...]
# Exemple : VFN_SECRET=... ./scripts/test_job.sh femme jupe ~/Desktop/jupe1.jpg ~/Desktop/jupe2.jpg
set -euo pipefail

BASE="${VFN_BASE:-https://178-105-102-54.sslip.io/webhook/vfn}"
: "${VFN_SECRET:?Définis VFN_SECRET (valeur du credential Header Auth)}"
GENRE="${1:?genre}"; TYPE="${2:?type}"; shift 2
[ "$#" -ge 1 ] || { echo "Au moins une photo requise" >&2; exit 1; }

ARGS=(-F "user=Jeremy" -F "genre=$GENRE" -F "type_vetement=$TYPE")
i=0; for f in "$@"; do ARGS+=(-F "photo$i=@$f"); i=$((i+1)); done

RESP=$(curl -sS -m 60 -X POST -H "X-VFN-Secret: $VFN_SECRET" "${ARGS[@]}" "$BASE/job")
echo "création : $RESP"
JOB_ID=$(printf '%s' "$RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin)["job_id"])')

for _ in $(seq 1 40); do
  STATUS=$(curl -sS -m 20 -H "X-VFN-Secret: $VFN_SECRET" "$BASE/job-status?id=$JOB_ID")
  S=$(printf '%s' "$STATUS" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("statut",""))')
  echo "statut : $S"
  if [ "$S" != "texte_en_cours" ]; then printf '%s\n' "$STATUS" | python3 -m json.tool; break; fi
  sleep 3
done
