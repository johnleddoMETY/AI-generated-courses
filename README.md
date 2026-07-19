# llm_engine

LLM pipeline for MyEdMaster's adaptive course-generation platform. A user
states a topic and certification; the pipeline generates an assessment,
grades it, and produces a study roadmap that teaches **only what the user
doesn't already know**.

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

4 planning/assessment LLM calls per full run, plus one call per roadmap item for course content.
All calls go through LiteLLM; provider and model are env-configured.

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

Run tests (no API key needed; the live test auto-skips):

```bash
pytest
RUN_LIVE_LLM_TESTS=1 pytest tests/test_live_smoke.py   # opt-in, burns tokens
```

All configuration lives in `.env` — see `.env.example` for every variable
(models, per-task overrides, temperatures, timeouts, proficiency
thresholds).

## API reference

Import everything from the package root:

```python
from llm_engine import (
    generate_syllabus, generate_assessment, grade_assessment, generate_roadmap, generate_course,
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

Questions are distributed across domains proportional to exam weight
(computed in Python, not by the model).

### grade_assessment(assessment, answers) -> GradedAssessment

```python
answers = [UserAnswer(question_id="c44d…", selected_option_id="B"),
           UserAnswer(question_id="d55e…", selected_option_id=None)]  # None = skipped
graded = grade_assessment(assessment, answers)
```

```json
{
  "assessment_id": "9a1b…",
  "overall_score_percent": 58.3,
  "question_results": [
    {"question_id": "c44d…", "domain_id": "…", "correct": true,
     "selected_option_id": "B", "correct_option_id": "B", "explanation": "…"}
  ],
  "domain_scores": [
    {"domain_id": "design-secure-architectures", "domain_name": "…",
     "weight_percent": 30.0, "questions_total": 4, "questions_correct": 2,
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

Every numeric score is computed deterministically in Python against the
stored answer key; the LLM contributes only the qualitative diagnosis.
Skipped and missing answers count as incorrect (`selected_option_id`
stays null so you can flag them). Unknown `question_id`s in `answers`
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

Fans out one LLM call per roadmap item and is fail-fast: if any single
lesson fails, the exception propagates and no partial `Course` is
returned. Lesson count therefore always equals `len(roadmap.items)`.
`total_estimated_hours` is copied from the roadmap's item hours, not
re-estimated.

## Integration rules (read this, backend)

1. **The package is stateless.** No DB, no files, no sessions. You own
   persistence and session flow. Call order: syllabus → assessment →
   (collect answers) → grade → roadmap → course.
2. **Persistence.** Every model serializes with `model_dump_json()` and
   restores with `Model.model_validate_json()` — store them in MySQL JSON
   columns keyed by their `*_id` fields (all UUIDs generated in code, safe
   to key on).
3. **SECURITY — answer key.** `Assessment` contains `correct_option_id`
   and `explanation` for every question. You MUST strip these before
   sending questions to the frontend. When grading, do NOT trust an
   assessment sent back by the client — load the stored server-side
   `Assessment` and pass that to `grade_assessment`.
4. **Errors.** Everything raises typed exceptions from
   `llm_engine.exceptions` (`LLMEngineError` base; `LLMCallError` for
   provider failures, `StructuredOutputError` for unrecoverable schema
   failures). `grade_assessment` raises `ValueError` for answers that
   reference unknown question IDs. Nothing returns None silently.

## Future hooks

- **Syllabus caching / cross-user reuse:** `Syllabus` for a normalized
  `(topic, certification)` pair is deterministic enough to cache and share
  across users — cache key on lowercased/trimmed topic+certification.
  First step toward the session-memory feature.
