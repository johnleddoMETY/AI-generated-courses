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

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   (or any Docker runtime) and make sure it's running.
2. Start MySQL — the root `docker-compose.yml` spins up a local instance,
   no local MySQL install needed:
   ```bash
   docker compose up -d mysql
   ```
3. Copy env vars — Django reads the repo-root `.env`, so add the keys
   documented in `backend/.env.example` (Django secret key, debug flag,
   allowed hosts, MySQL credentials, CORS origins) alongside the existing
   `LLM_*` / `OPENAI_API_KEY` vars.
4. Migrate and run:
   ```bash
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```
5. Optionally walk the whole pipeline against the running server:
   ```bash
   ./demo_api.sh
   ```

**Running the test suite against this container:** `pytest` spins up its
own `test_<db>` database per run. The default `llm_engine` MySQL user
(created by the official `mysql` image from `MYSQL_USER`/`MYSQL_PASSWORD`)
only has privileges on the `llm_engine` database, not on arbitrary
databases, so the first time you run tests you need to grant it rights on
the test DB too:
```bash
docker exec ai-generated-courses-mysql-1 mysql -uroot -proot -e \
  "GRANT ALL PRIVILEGES ON \`test_llm_engine\`.* TO 'llm_engine'@'%'; FLUSH PRIVILEGES;"
```
(swap `-proot` for your `MYSQL_ROOT_PASSWORD` if you changed it from the
`docker-compose.yml` default). One-time setup per fresh container.

## Data model

Every pipeline object (`Syllabus`, `Assessment`, `GradedAssessment`,
`Roadmap`, `Course`) is stored as one row keyed on the same UUID
`llm_engine` already generates for it. The full `model_dump(mode="json")`
of the object goes into a `payload` JSON column; a handful of fields are
pulled out as real columns purely so they're queryable/joinable. Before a
stored object goes back into an `llm_engine` service function, it's
rebuilt with `Model.model_validate(row.payload)`.

```
Syllabus(syllabus_id, topic, certification, exam_code, payload)
  └── Assessment(assessment_id, syllabus FK, payload)
        ├── GradedAssessment(assessment FK/PK, payload)
        └── Roadmap(roadmap_id, assessment FK, syllabus FK, payload)
              └── Course(course_id, roadmap FK, payload)
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
| `POST` | `/api/roadmap/<roadmap_id>/course/` | Generate a full text course (one lesson per roadmap item) |
| `GET` | `/api/course/<course_id>/` | Fetch a stored course |
| `POST` | `/api/course/<course_id>/lesson/<item_id>/regenerate/` | Regenerate one lesson and swap it into the stored course |

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

### `POST /api/roadmap/<roadmap_id>/course/`
No request body. Generates one lesson per roadmap item — `llm_engine`
now fans these out concurrently via a thread pool rather than one at a
time, but it's still by far the slowest and most expensive call in the
pipeline (one LLM call per item, "textbook-length" output each). Returns
the full `Course` payload, `201`.

> **Caveat:** this still runs synchronously inside the request — the view
> blocks until every lesson comes back, same as the other endpoints,
> purely to match the existing pattern. Concurrency inside `llm_engine`
> makes it faster, but doesn't change that; the pipeline README still
> recommends treating course generation as a background job. Worth
> moving to one (e.g. Celery/RQ) before this is client-facing, so a
> slow/failed generation doesn't hold open an HTTP connection.

### `GET /api/course/<course_id>/`
Returns the stored `Course` payload, `200`. No stripping needed here —
unlike `Assessment`, `Lesson.practice_questions` are open-ended study
material meant to be shown with their answers.

### `POST /api/course/<course_id>/lesson/<item_id>/regenerate/`
No request body. Regenerates a single lesson (one LLM call, via
`generate_lesson`) and swaps it into the stored `Course.payload` by
matching `item_id`, without touching the rest of the course. Returns the
regenerated `Lesson` payload, `200`. Useful for refreshing stale content
or retrying one lesson that came out bad — much cheaper than regenerating
the whole course. 404s if the course doesn't exist or if `item_id` isn't
one of the roadmap items the course was built from.

## Auth

Every endpoint requires a valid **Supabase-issued JWT** — `DEFAULT_PERMISSION_CLASSES`
is set to `IsAuthenticated` project-wide, so nothing is reachable
unauthenticated by default.

- **Login/registration happen entirely on the frontend** via `supabase-js`
  — Django has no register/login endpoints of its own and never sees a
  password. The frontend sends the access token Supabase returns as
  `Authorization: Bearer <token>` on every request.
- `courses/authentication.py`'s `SupabaseJWTAuthentication` verifies the
  token's signature against `SUPABASE_JWT_SECRET` (from your Supabase
  project: Project Settings → API → JWT Secret) and checks
  `aud == "authenticated"`. On success it sets `request.user` to a
  lightweight, non-persisted `SupabaseUser` (just `id`/`email` from the
  token claims) — no local `User` row is created or required.
- **No per-resource ownership yet.** This is purely an
  authenticated-or-not gate — any authenticated user can still read/write
  any `syllabus_id`/`assessment_id`/etc. Tying records to the calling
  user is a deliberate fast-follow, not done here.
- Missing/invalid tokens get `401` with a `WWW-Authenticate: Bearer`
  header.
- **Tests and `demo_api.sh` don't need a real Supabase project** — both
  mint their own token locally, signed with `SUPABASE_JWT_SECRET` (which
  defaults to a fixed dev value unless overridden), so the whole suite
  and the demo script run standalone.

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

All five models are registered in `courses/admin.py`, giving a
browsable/searchable view of every stored syllabus, assessment, graded
result, roadmap, and course at `/admin/` — useful for debugging without
writing any throwaway scripts.

## Tests

```bash
cd backend
pytest
```

`courses/tests/` covers all eight endpoints plus the auth gate itself
(`test_syllabus_api.py`, `test_assessment_api.py`, `test_grading_api.py`,
`test_roadmap_api.py`, `test_course_api.py`, `test_authentication.py`),
with shared fixtures in `tests/conftest.py` building fake `llm_engine`
objects and an authenticated `APIClient` (LLM-related env vars are
cleared per-test so real credentials never leak into test runs). See the
"Running the test suite" note above for the one-time MySQL grant needed
against the Docker container.

## Known gaps / next steps

- Auth is authenticated-or-not only — any authenticated user can still
  read/write any `syllabus_id`/`assessment_id`/etc. Tying records to the
  calling user is the natural next step.
- No list endpoints (e.g. "all syllabuses for a user") — only
  create/retrieve by ID.
- Course generation (`POST /api/roadmap/<roadmap_id>/course/`) runs
  synchronously — see the caveat under that endpoint above. Should move
  to a background job queue before it's client-facing.
- Django is running via `manage.py runserver`; only MySQL is
  containerized so far (`docker-compose.yml`) — the Django app itself
  isn't in that compose file yet.
- Settings are dev-only (`DEBUG=true`, a placeholder `SECRET_KEY`
  default) — no prod/dev split yet.
- Parallel lesson fan-out (`generate_course`'s thread pool) is fail-fast:
  lessons already in flight when one fails are not cancelled but their
  results are discarded either way. No partial-course recovery — a
  failed `POST .../course/` needs a full retry, though individual lessons
  can be fixed after the fact via the regenerate endpoint.
