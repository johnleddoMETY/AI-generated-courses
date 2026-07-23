# Backend

A Django + MySQL REST API that wraps the `llm_engine` pipeline (see the
[repo-root README](../README.md) for what that pipeline does). This app
owns persistence and HTTP concerns only — every piece of actual pipeline
logic (allocation math, grading, gap-targeting) stays inside `llm_engine`.
Views just reconstruct `llm_engine` Pydantic objects from stored JSON and
call straight into its service functions.

## Stack

| Layer | Tech |
|---|---|
| Framework | Django 5 + Django REST Framework |
| Database | MySQL 8 (via `mysqlclient`) |
| CORS | `django-cors-headers` (for a separate frontend origin) |
| Tests | `pytest` + `pytest-django` |

Install with the `backend` extra defined in the repo-root `pyproject.toml`:

```bash
pip install -e ".[backend]"
```

## Project layout

```
backend/
├── config/            # Django project: settings, URL root, ASGI/WSGI
├── courses/           # the one Django app — models, views, serializers, admin
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── exceptions.py
│   ├── migrations/
│   └── tests/
├── manage.py
├── pytest.ini
├── conftest.py         # makes the sibling llm_engine package importable
└── demo_api.sh          # walks the full API end-to-end against a running server
```

## Running it

1. Start MySQL (root `docker-compose.yml` spins up a local instance):
   ```bash
   docker compose up -d mysql
   ```
2. Copy env vars — Django reads the repo-root `.env`, so add the keys
   documented in `backend/.env.example` (Django secret key, debug flag,
   allowed hosts, MySQL credentials, CORS origins) alongside the existing
   `LLM_*` / `OPENAI_API_KEY` vars.
3. Migrate and run:
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```
4. Optionally walk the whole pipeline against the running server:
   ```bash
   ./demo_api.sh
   ```

## Data model

Every pipeline object (`Syllabus`, `Assessment`, `GradedAssessment`,
`Roadmap`) is stored as one row keyed on the same UUID `llm_engine`
already generates for it. The full `model_dump(mode="json")` of the
object goes into a `payload` JSON column; a handful of fields are pulled
out as real columns purely so they're queryable/joinable. Before a stored
object goes back into an `llm_engine` service function, it's rebuilt with
`Model.model_validate(row.payload)`.

```
Syllabus(syllabus_id, topic, certification, exam_code, payload)
  └── Assessment(assessment_id, syllabus FK, payload)
        ├── GradedAssessment(assessment FK/PK, payload)
        └── Roadmap(roadmap_id, assessment FK, syllabus FK, payload)
```

**Security rule:** `Assessment.payload` includes `correct_option_id` and
`explanation` for every question — this row must never be returned to a
client directly. Every read goes through
`courses.serializers.serialize_assessment_public`, which strips both
fields. Grading never trusts a client-submitted assessment either — it
always reloads the server-stored `Assessment` for the given
`assessment_id` before calling `grade_assessment`.

## API

All endpoints live under `/api/` (see `courses/urls.py`).

| Method | Path | Does |
|---|---|---|
| `POST` | `/api/syllabus/` | Generate a syllabus for a topic + certification |
| `POST` | `/api/syllabus/<syllabus_id>/assessment/` | Generate a practice assessment from a stored syllabus |
| `GET` | `/api/assessment/<assessment_id>/` | Fetch a stored assessment (answer key stripped) |
| `POST` | `/api/assessment/<assessment_id>/grade/` | Grade submitted answers against the server-stored assessment |
| `POST` | `/api/assessment/<assessment_id>/roadmap/` | Generate a gap-targeted study roadmap from grading results |

### `POST /api/syllabus/`
```json
// request
{ "topic": "Cloud Architecture", "certification": "AWS Solutions Architect Associate SAA-C03" }
```
Returns the full `Syllabus` payload, `201`.

### `POST /api/syllabus/<syllabus_id>/assessment/`
```json
// request
{ "num_questions": 12, "exam_date": null }
```
Returns the `Assessment` payload with `correct_option_id`/`explanation`
stripped from every question, `201`.

### `GET /api/assessment/<assessment_id>/`
Returns the same public-shaped `Assessment` payload, `200`.

### `POST /api/assessment/<assessment_id>/grade/`
```json
// request
{ "answers": [ { "question_id": "...", "selected_option_id": "A" } ] }
```
Returns the `GradedAssessment` payload (overall score, per-domain scores
and proficiency), `201`.

### `POST /api/assessment/<assessment_id>/roadmap/`
```json
// request
{ "exam_date": null }
```
Requires a `GradedAssessment` to already exist for that assessment.
Returns the `Roadmap` payload, `201`.

## Request validation & error handling

- Every endpoint validates its request body through a DRF `Serializer` in
  `courses/serializers.py` before touching the database or calling
  `llm_engine` (`SyllabusCreateRequestSerializer`,
  `AssessmentCreateRequestSerializer`, `GradeRequestSerializer`,
  `RoadmapCreateRequestSerializer`).
- `courses/exceptions.py` registers a global DRF exception handler
  (`llm_engine_exception_handler`) that maps `llm_engine`'s typed
  exceptions to HTTP responses:
  - `LLMCallError` → `502 Bad Gateway`
  - `StructuredOutputError` → `500 Internal Server Error`
  - `ValueError` (e.g. grading with an unknown `question_id`) → `400 Bad Request`

## Admin

All four models are registered in `courses/admin.py`, giving a
browsable/searchable view of every stored syllabus, assessment, graded
result, and roadmap at `/admin/` — useful for debugging without writing
any throwaway scripts.

## Tests

```bash
cd backend
pytest
```

`courses/tests/` covers all four endpoints
(`test_syllabus_api.py`, `test_assessment_api.py`, `test_grading_api.py`,
`test_roadmap_api.py`), with shared fixtures in `tests/conftest.py`
building fake `llm_engine` objects and an isolated `APIClient` (LLM-related
env vars are cleared per-test so real credentials never leak into test
runs).

## Known gaps / next steps

- No auth — any client can read/write any `syllabus_id`/`assessment_id`.
  Needed before this is multi-user safe.
- No list endpoints (e.g. "all syllabuses for a user") — only
  create/retrieve by ID.
- The `llm_engine` pipeline now has a 5th stage, **course generation**
  (`generate_course(roadmap) -> Course`), added after this backend was
  built. It isn't wired up here yet. Per the pipeline README, it's a
  slow, expensive call (one LLM call per roadmap item) and should run as
  a background job rather than inside a synchronous request — unlike
  `Assessment`, `Lesson` content has no answer key to strip and is safe
  to return to the client whole.
- Django is running via `manage.py runserver`; only MySQL is
  containerized so far (`docker-compose.yml`) — the Django app itself
  isn't in that compose file yet.
- Settings are dev-only (`DEBUG=true`, a placeholder `SECRET_KEY`
  default) — no prod/dev split yet.
