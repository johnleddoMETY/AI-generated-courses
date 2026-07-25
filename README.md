# llm_engine

LLM pipeline for MyEdMaster's adaptive course-generation platform. A user
states a topic and certification; the pipeline generates an assessment,
grades it, builds a study roadmap, and writes the course content for it —
teaching **only what the user doesn't already know**.

```
topic + certification (+ optional exam date)
        │
        ▼
generate_syllabus ──────► Syllabus        (exam domains + weights, 1 LLM call)
        │
        ▼
generate_assessment ────► Assessment      (weighted MCQs, 1 LLM call)
        │
        ▼
[user answers — backend/frontend collect these]
        │
        ▼
grade_assessment ───────► GradedAssessment (scores computed in Python,
        │                                   LLM diagnosis only, 1 LLM call)
        ▼
generate_roadmap ───────► Roadmap         (gap-targeted plan that skips
        │                                  proficient domains, 1 LLM call)
        ▼
generate_course ────────► Course          (one lesson per roadmap item,
                                           1 LLM call per item)
```

4 planning and assessment LLM calls per full run, plus one call per
roadmap item for course content. All calls go through LiteLLM; provider
and model are env-configured.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[cli,dev]"
cp .env.example .env       # then set OPENAI_API_KEY (or OPENROUTER_API_KEY)
```

Run the demo:

```bash
python demo_cli.py --topic "Cloud Architecture" \
  --certification "AWS Solutions Architect Associate SAA-C03" \
  --exam-date 2026-09-15 --num-questions 12
```

Flags: `--random-answers` (non-interactive), `--json-out artifacts/` (dump
every stage's JSON — use these as your example payloads).

Expect the demo to take a couple minutes. Stage 5 writes a full lesson per
roadmap item, one call each, run concurrently via a thread pool — it logs
`Generating lesson 2/6: <title>` per lesson at INFO so you can watch it
progress rather than wonder whether it hung (lines may interleave across
lessons since they run in parallel).

Run tests (no API key needed; the live test auto-skips):

```bash
pytest
RUN_LIVE_LLM_TESTS=1 pytest tests/test_live_smoke.py   # opt-in, burns tokens
```

All configuration lives in `.env` — see `.env.example` for every variable
(models, per-task overrides, temperatures, timeouts, proficiency
thresholds).

## What changed with course generation (backend, start here)

Course generation added a fifth stage. If you already integrated against
the four-stage pipeline, this is everything that affects you:

1. **BREAKING — `run_full_pipeline` now returns 5 values, not 4.**
   ```python
   # before
   syllabus, assessment, graded, roadmap = run_full_pipeline(...)
   # now
   syllabus, assessment, graded, roadmap, course = run_full_pipeline(...)
   ```
   Nothing else about the first four stages changed — same signatures,
   same schemas, same behavior.

2. **New call, safe to defer.** `generate_course(roadmap) -> Course` is a
   normal stage function. `run_full_pipeline` runs it automatically, but
   you can skip it and call it later (e.g. only after the learner accepts
   the roadmap) — it needs nothing but the stored `Roadmap`.

3. **New things to persist.** `Course` keyed by `course_id`, same JSON
   column pattern as everything else. `Course.roadmap_id` links back to
   the roadmap; each `Lesson.item_id` is a foreign key to the
   `RoadmapItem` it teaches. Lessons are returned in roadmap priority
   order — preserve that order, it is the intended reading order.

4. **No answer key to strip.** Unlike `Assessment`, `Lesson` is safe to
   send to the frontend whole. `practice_questions` are open-ended
   (`question`/`answer`/`explanation`) and intended to be shown with
   their answers as study material — there is nothing to hide and no
   client-trust issue, because nothing here is scored.

5. **Cost and latency change shape.** The first four stages are a fixed 4
   LLM calls. Course generation is one call per roadmap item (typically
   3–8, since proficient domains are already skipped), run concurrently
   via a thread pool, producing a full textbook-length lesson each. This
   is still by far the slowest and most expensive stage — treat it as a
   background job, not something to run inside a request/response cycle.

6. **Fail-fast, so retry the whole call.** If any single lesson fails,
   the exception propagates and no partial `Course` comes back. Lessons
   already in flight when the failure surfaces are not cancelled, but
   their results are discarded either way. There is no partial state to
   reconcile — just re-call `generate_course` with the same roadmap.

## API reference

Import everything from the package root:

```python
from llm_engine import (
    generate_syllabus, generate_assessment, grade_assessment, generate_roadmap,
    generate_course, generate_lesson,
    Syllabus, Assessment, UserAnswer, GradedAssessment, Roadmap, Course, Lesson,
)
```

### generate_syllabus(topic: str, certification: str) -> Syllabus

```python
syllabus = generate_syllabus("Cloud Architecture", "AWS Solutions Architect Associate SAA-C03")
```

```json
{
  "syllabus_id": "5f0c…",
  "topic": "Cloud Architecture",
  "certification": "AWS Solutions Architect Associate SAA-C03",
  "exam_code": "SAA-C03",
  "domains": [
    {
      "domain_id": "design-secure-architectures",
      "name": "Design Secure Architectures",
      "weight_percent": 30.0,
      "key_topics": ["IAM", "KMS", "VPC security"]
    }
  ],
  "question_type_mix": [
    {"question_type": "single_answer", "weight_percent": 90.0},
    {"question_type": "multi_answer", "weight_percent": 10.0}
  ],
  "source_note": "Based on the official SAA-C03 exam guide.",
  "created_at": "2026-07-11T19:00:00Z"
}
```

`source_note` states how grounded the blueprint is; unknown certifications
get a generic breakdown and say so. `exam_code` is null unless confidently
known.

### generate_assessment(syllabus, num_questions=12, exam_date=None) -> Assessment

```python
assessment = generate_assessment(syllabus, num_questions=12)
```

```json
{
  "assessment_id": "9a1b…",
  "syllabus_id": "5f0c…",
  "domains": [ … syllabus domain snapshot … ],
  "questions": [
    {
      "question_type": "single_answer",
      "question_id": "c44d…",
      "domain_id": "design-secure-architectures",
      "difficulty": "medium",
      "stem": "A company needs…",
      "options": [
        {"option_id": "A", "text": "…"},
        {"option_id": "B", "text": "…"},
        {"option_id": "C", "text": "…"},
        {"option_id": "D", "text": "…"}
      ],
      "correct_option_id": "B",
      "explanation": "B is correct because… A is wrong because…"
    }
  ],
  "num_questions": 12,
  "created_at": "2026-07-11T19:00:30Z"
}
```

Each question is one of four types, tagged by `question_type`:
`single_answer` (shape above), `multi_answer` (`options` +
`correct_option_ids: list[str]`, 2+ correct), `fill_in_blank`
(`accepted_answers: list[str]`, no `options`), `full_text` (`rubric: str`,
no `options`). The mix of types is inferred per-certification during
syllabus generation (`Syllabus.question_type_mix`) — most certifications
are 100% `single_answer`; some mix in the others.

Questions are distributed across domains and question types proportional to exam weight
(computed in Python, not by the model).

### grade_assessment(assessment, answers) -> GradedAssessment

```python
answers = [UserAnswer(question_id="c44d…", selected_option_id="B"),
           UserAnswer(question_id="d55e…", selected_option_id=None)]  # None = skipped
# multi_answer: UserAnswer(question_id="…", selected_option_ids=["A", "C"])
# fill_in_blank / full_text: UserAnswer(question_id="…", text_answer="…")
graded = grade_assessment(assessment, answers)
```

```json
{
  "assessment_id": "9a1b…",
  "overall_score_percent": 58.3,
  "question_results": [
    {"question_id": "c44d…", "domain_id": "…", "question_type": "single_answer", "correct": true,
     "score_percent": 100.0, "selected_option_id": "B", "correct_option_id": "B", "explanation": "…"}
  ],
  "domain_scores": [
    {"domain_id": "design-secure-architectures", "domain_name": "…",
     "weight_percent": 30.0, "questions_total": 4, "questions_correct": 2.0,
     "score_percent": 50.0, "proficiency": "developing"}
  ],
  "gaps": [
    {"domain_id": "…", "gap_summary": "Confuses NAT Gateway with Internet Gateway egress behavior.",
     "severity": "moderate", "evidence_question_ids": ["d55e…"]}
  ],
  "diagnostic_summary": "…",
  "strengths_summary": "…",
  "graded_at": "2026-07-11T19:05:00Z"
}
```

`single_answer`/`multi_answer` scores are computed deterministically in
Python (multi-answer is all-or-nothing: the selected set must exactly
match the correct set). `fill_in_blank`/`full_text` answers can't be
graded by exact match, so the LLM scores them in the same call that
produces the qualitative diagnosis — `fill_in_blank` is binary (0 or
100), `full_text` gets partial credit (0-100). `DomainScore.score_percent`
is the mean of `score_percent` across a domain's questions regardless of
type; `questions_correct` is the fractional-equivalent count
(`sum(score_percent)/100`), so it's no longer always a whole number once
a domain contains a partially-scored `full_text` answer. Skipped and
missing answers count as incorrect. Unknown `question_id`s in `answers`
raise `ValueError`. Proficiency thresholds: <50 weak, 50–79 developing,
≥80 proficient (env-configurable).

### generate_roadmap(syllabus, graded, exam_date=None) -> Roadmap

```python
roadmap = generate_roadmap(syllabus, graded, exam_date=date(2026, 9, 15))
```

```json
{
  "roadmap_id": "e66f…",
  "exam_date": "2026-09-15",
  "items": [
    {"item_id": "f77a…", "domain_id": "…", "title": "…", "objective": "…",
     "subtopics": ["…"], "why_included": "You scored 25% in this 30%-weight domain…",
     "priority": 1, "estimated_hours": 4.0, "prerequisites": []}
  ],
  "skipped_domains": [
    {"domain_id": "deploy-and-manage", "reason": "Scored 100% — proficient; not re-taught."}
  ],
  "total_estimated_hours": 18.5,
  "weekly_plan": [
    {"week_number": 1, "focus": "…", "item_ids": ["f77a…"], "estimated_hours": 6.0}
  ],
  "guidance_summary": "…",
  "created_at": "2026-07-11T19:06:00Z"
}
```

Proficient domains are skipped (or reduced to one light review item) and
listed in `skipped_domains` — this is the product's core behavior.
`weekly_plan` is null unless `exam_date` is provided.

### generate_course(roadmap) -> Course

```python
course = generate_course(roadmap)
```

```json
{
  "course_id": "g88b…",
  "roadmap_id": "e66f…",
  "topic": "Cloud Architecture",
  "certification": "AWS Solutions Architect Associate SAA-C03",
  "lessons": [
    {
      "lesson_id": "h99c…",
      "item_id": "f77a…",
      "title": "IAM permission boundaries deep dive",
      "sections": [
        {"heading": "What a permission boundary is",
         "body_markdown": "A boundary caps the maximum permissions…"}
      ],
      "examples": [
        {"scenario": "A developer needs S3 access but must never escalate to IAM admin.",
         "walkthrough": "Attach a boundary that allows s3:* and denies iam:*…"}
      ],
      "practice_questions": [
        {"question": "What is the effective permission when a boundary and an identity policy disagree?",
         "answer": "The intersection of the two — both must allow the action.",
         "explanation": "Boundaries do not grant permissions; they cap them…"}
      ],
      "summary": "Boundaries constrain the maximum permissions of an identity…",
      "created_at": "2026-07-11T19:07:00Z"
    }
  ],
  "total_estimated_hours": 18.5,
  "created_at": "2026-07-11T19:07:00Z"
}
```

Generates one `Lesson` per `Roadmap.items` entry, in roadmap priority
order, each grounded in that item's `objective`, `subtopics`, and
`why_included` so lessons teach the learner's actual gaps rather than
generic material. Each lesson targets 3–6 sections, 2–3 worked examples,
and 3–5 practice questions.

`practice_questions` are open-ended self-check questions (question + model
answer + explanation) — deliberately **not** the MCQ format used by
`Assessment`, since they are for study reinforcement, not scored
diagnosis. They carry no answer key to strip.

Fans out one LLM call per roadmap item via a thread pool (each lesson is
an independent call, so this is a latency win, not a CPU one) and is
fail-fast: if any single lesson fails, the exception propagates and no
partial `Course` is returned — lessons already in flight are not
cancelled, but their results are discarded either way. `Course.lessons`
is always returned in `roadmap.items` order regardless of which lesson
finished first, and lesson count therefore always equals
`len(roadmap.items)`. `total_estimated_hours` is copied from the
roadmap's item hours, not re-estimated.

Progress is logged at INFO on `llm_engine.services.course`
(`Generating lesson 2/6: <title>`). Lines may interleave across lessons
since they run concurrently. The raised exception names only the task,
not the item, so these lines are how you identify which item failed in a
long run.

### generate_lesson(item, topic, certification) -> Lesson

```python
lesson = generate_lesson(roadmap.items[0], roadmap.topic, roadmap.certification)
```

The single-lesson primitive that `generate_course` fans out over, exposed
so you can regenerate one lesson without rebuilding the whole course —
retrying the item that failed, or refreshing stale content. Returns the
same `Lesson` shape shown above. One LLM call.

## Integration rules (read this, backend)

1. **The package is stateless.** No DB, no files, no sessions. You own
   persistence and session flow. Call order: syllabus → assessment →
   (collect answers) → grade → roadmap → course.
2. **Persistence.** Every model serializes with `model_dump_json()` and
   restores with `Model.model_validate_json()` — store them in MySQL JSON
   columns keyed by their `*_id` fields (all UUIDs generated in code, safe
   to key on).
3. **SECURITY — answer key.** Every question in `Assessment` carries
   `explanation` plus a type-specific answer-revealing field:
   `correct_option_id` (single_answer), `correct_option_ids`
   (multi_answer), `accepted_answers` (fill_in_blank), or `rubric`
   (full_text). You MUST strip all of these before sending questions to
   the frontend. When grading, do NOT trust an
   assessment sent back by the client — load the stored server-side
   `Assessment` and pass that to `grade_assessment`. This applies to
   `Assessment` only: `Lesson.practice_questions` are study material and
   are meant to be shown with their answers.
4. **Errors.** Everything raises typed exceptions from
   `llm_engine.exceptions` (`LLMEngineError` base; `LLMCallError` for
   provider failures, `StructuredOutputError` for unrecoverable schema
   failures). `grade_assessment` raises `ValueError` for answers that
   reference unknown question IDs. Nothing returns None silently.

## Future hooks

- **Syllabus caching / cross-user reuse** (backend): `Syllabus` for a normalized
  `(topic, certification)` pair is deterministic enough to cache and share
  across users — cache key on lowercased/trimmed topic+certification.
  First step toward the session-memory feature.
The two course-generation hooks below are independent of each other. The
last two after them are larger, quality-focused initiatives rather than
incremental follow-ups.

- ~~**Parallel lesson fan-out**~~ — **done.** `generate_course` now fans
  out lessons via a thread pool instead of a sequential loop; see the
  `generate_course` API reference above.
- **Lesson-level regeneration** (mix — llm_engine primitive done, backend
  endpoint not built): `generate_lesson` is exported and every
  `Lesson` carries the `item_id` of the `RoadmapItem` it teaches, so one
  lesson can be regenerated and swapped into a stored `Course` — for
  refreshing stale content, or for retrying a single failed item. Note
  that `generate_course` is fail-fast and returns no partial `Course`, so
  failure-repair means running the per-item loop yourself over
  `generate_lesson` and keeping the successes. That is available today
  and needs no change to this package. Now more valuable than before:
  since lesson generation runs in parallel, a late failure discards every
  lesson already in flight, and this is what makes that acceptable.
- **Lesson caching** (backend): lessons for the same `(objective, subtopics,
  certification)` are largely reusable across learners. The catch: the
  prompt deliberately grounds each lesson in `why_included`, which is
  learner-specific ("you scored 25% here"), so a cache key including it
  never hits. Reuse means keying on the non-personalized fields and
  accepting less personalized lessons — a product tradeoff, not a free
  win.
- **Retrieval-grounded generation (RAG)** (mix — schema groundwork done in
  llm_engine, corpus/ingestion/retrieval is backend): many certifications publish an
  official exam guide; many do not — so this is conditional by nature,
  grounding where source material exists and falling back to today's
  generic path where it doesn't. The schema already models that
  distinction: `source_note` discloses how grounded a blueprint is, and
  `exam_code` stays null when the certification isn't confidently known.
  Highest leverage is `generate_syllabus`, because domain weights are not
  just one field — assessment question distribution and roadmap
  prioritization are both computed from them, so one hallucinated weight
  corrupts every downstream stage. Lessons and assessment benefit too;
  grading barely does, since its scores are already deterministic.
  Two design constraints. Keep retrieval **caller-side**: this package is
  stateless by contract, so the corpus, ingestion, and any vector store
  belong to the backend, and the stage functions should accept optional
  retrieved context as a parameter rather than owning a document store.
  And don't assume a vector database — an exam guide is often a dozen
  pages and fits in context whole; retrieval machinery only earns its
  keep on large corpora, such as full service documentation for lesson
  generation. Confirm licensing before ingesting vendor material:
  certification content is often restrictively licensed and generating
  derivative study material from it is a legal question, not a technical
  one. Worth settling before building the pipeline, since it can rule out
  specific vendors entirely.
- **Fine-tuned lesson model** (llm_engine): model choice is already per-task and
  env-driven (`LLM_MODEL_LESSON`), so a fine-tuned endpoint drops in with
  no code change. Sensible only as a cost play on the lesson task, which
  dominates spend — not for factual grounding, since the pipeline must
  serve arbitrary certifications and exam blueprints version over time
  (retrieval over official exam guides is the better tool there), and not
  for output structure, which `structured_completion` already enforces.
  Two hard prerequisites: enough real runs to build training data, and an
  eval harness — there is currently no way to measure lesson quality, so
  a regression would be invisible. Try the free experiment first: point
  `LLM_MODEL_LESSON` at a cheaper model and compare the `cost_usd` lines
  against the output you get.
