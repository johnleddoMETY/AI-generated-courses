#!/usr/bin/env bash
# Walks the full backend API end-to-end against a running dev server.
# Usage: ./demo_api.sh (from backend/, with `python manage.py runserver` already running)
set -euo pipefail

BASE_URL="http://127.0.0.1:8000/api"
step() { printf "\n\033[1;36m== %s ==\033[0m\n" "$1"; }

# Real Supabase projects sign session tokens asymmetrically (ES256, via a
# JWKS endpoint) — there's no shared secret to self-sign a fake token with
# anymore, so this logs in for real. Needs a Supabase test user + these vars
# in the repo-root .env (see backend/.env.example): SUPABASE_URL,
# SUPABASE_ANON_KEY, SUPABASE_DEMO_EMAIL, SUPABASE_DEMO_PASSWORD.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$REPO_ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$REPO_ROOT/.env"
  set +a
fi

step "0. Log in to Supabase for a real auth token (the frontend does this via supabase-js)"
: "${SUPABASE_URL:?Set SUPABASE_URL in .env}"
: "${SUPABASE_ANON_KEY:?Set SUPABASE_ANON_KEY in .env}"
: "${SUPABASE_DEMO_EMAIL:?Set SUPABASE_DEMO_EMAIL in .env to an existing Supabase test user}"
: "${SUPABASE_DEMO_PASSWORD:?Set SUPABASE_DEMO_PASSWORD in .env for that test user}"

TOKEN=$(curl -s -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$SUPABASE_DEMO_EMAIL\", \"password\": \"$SUPABASE_DEMO_PASSWORD\"}" \
  | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "Failed to get a Supabase token — check SUPABASE_* vars in .env and that the demo user exists (Auth > Users, 'Auto Confirm User' checked)." >&2
  exit 1
fi
AUTH_HEADER="Authorization: Bearer $TOKEN"

step "1. Create a syllabus"
curl -s "$BASE_URL/syllabus/" -X POST -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d '{"topic": "Cloud Architecture", "certification": "AWS Solutions Architect Associate SAA-C03"}' \
  -o /tmp/demo_syllabus.json
jq '{syllabus_id, topic, certification, domains: [.domains[].name]}' /tmp/demo_syllabus.json
SYLLABUS_ID=$(jq -r '.syllabus_id' /tmp/demo_syllabus.json)

step "2. Generate an assessment (note: no correct_option_id / explanation in this response)"
curl -s "$BASE_URL/syllabus/$SYLLABUS_ID/assessment/" -X POST -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d '{"num_questions": 4}' \
  -o /tmp/demo_assessment.json
jq '{assessment_id, questions: [.questions[] | {question_id, stem, options}]}' /tmp/demo_assessment.json
ASSESSMENT_ID=$(jq -r '.assessment_id' /tmp/demo_assessment.json)
Q1=$(jq -r '.questions[0].question_id' /tmp/demo_assessment.json)
Q2=$(jq -r '.questions[1].question_id' /tmp/demo_assessment.json)

step "3. Grade the assessment (server re-loads the real answer key — client never had it)"
curl -s "$BASE_URL/assessment/$ASSESSMENT_ID/grade/" -X POST -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d "{\"answers\": [{\"question_id\": \"$Q1\", \"selected_option_id\": \"A\"}, {\"question_id\": \"$Q2\", \"selected_option_id\": null}]}" \
  -o /tmp/demo_graded.json
jq '{overall_score_percent, domain_scores: [.domain_scores[] | {domain_id, score_percent, proficiency}]}' /tmp/demo_graded.json

step "4. Generate the gap-targeted roadmap"
curl -s "$BASE_URL/assessment/$ASSESSMENT_ID/roadmap/" -X POST -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  -d '{}' \
  -o /tmp/demo_roadmap.json
jq '{total_estimated_hours, skipped_domains, items: [.items[] | {title, priority, estimated_hours}]}' /tmp/demo_roadmap.json

step "Done — cleaning up temp files"
rm -f /tmp/demo_syllabus.json /tmp/demo_assessment.json /tmp/demo_graded.json /tmp/demo_roadmap.json
