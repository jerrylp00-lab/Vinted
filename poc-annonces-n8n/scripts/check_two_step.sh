#!/usr/bin/env bash
# Vérifie, sans image payante, que le statut premiere_prete et l'endpoint /job/suite existent.
# Usage : VFN_SECRET=... ./scripts/check_two_step.sh <job_id_de_test_en_premiere_prete>
set -euo pipefail
BASE="${BASE:-https://178-105-102-54.sslip.io/webhook/vfn}"
JOB="${1:?job_id manquant}"
H=(-H "X-VFN-Secret: ${VFN_SECRET:?VFN_SECRET manquant}" -H "Content-Type: application/json")
echo "== statut du job"; curl -s "${H[@]}" "$BASE/job-status?id=$JOB" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["statut"], [ (p["plan"],p["statut"]) for p in d["plans"] ])'
echo "== /job/suite sur un job inexistant (attendu 409)"; curl -s -o /dev/null -w "%{http_code}\n" -X POST "${H[@]}" -d '{"job_id":"inexistant"}' "$BASE/job/suite"
echo "== /job/plan cintre quand premiere_prete (attendu 409)"; curl -s -o /dev/null -w "%{http_code}\n" -X POST "${H[@]}" -d "{\"job_id\":\"$JOB\",\"plan\":\"cintre\"}" "$BASE/job/plan"
