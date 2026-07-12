# llm_engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone `llm_engine` Python package implementing the four-stage LLM pipeline (syllabus → assessment → grading → roadmap) with strict structured outputs, plus a rich terminal demo, pytest suite, and a README that is the backend integration contract.

**Architecture:** Stateless service functions wrap a single LiteLLM client (`structured_completion`) that validates every LLM response into a Pydantic v2 model with a validation-error retry loop and a JSON-mode fallback. Two-layer schemas: LLM-facing response models (strict-mode-safe types, no IDs) are assembled into domain models (UUIDs, datetimes, computed scores) in Python. All numeric scoring is deterministic Python; the LLM only does qualitative diagnosis.

**Tech Stack:** Python 3.11+, Pydantic v2, LiteLLM, python-dotenv, rich (CLI only), pytest (dev).

## Global Constraints

Copied verbatim from the spec (`prompt.md` E2) — every task implicitly includes these:

1. **Python 3.11+, Pydantic v2, LiteLLM.** All LLM calls go through LiteLLM only. No `openai` SDK imports, no raw HTTP.
2. **Strict structured outputs.** Every LLM response validated into a Pydantic model. Primary: `litellm.completion(..., response_format=<PydanticModel>)`. Fallback: JSON-mode instruction + `Model.model_validate_json()`. On `pydantic.ValidationError`, retry up to 2 times feeding error text back; then raise typed `StructuredOutputError`. ZERO regex/string-splitting parsing of LLM output anywhere.
3. **Zero web-framework dependencies.** Deps limited to: `litellm`, `pydantic>=2`, `python-dotenv`, `rich` (CLI only), `pytest` (dev).
4. **Stateless services.** No global mutable state, no DB, no file persistence. Pure functions in, Pydantic models out.
5. **All IDs generated in code, not by the LLM.** UUID4 strings (short slugs for `domain_id`) assigned in Python after the LLM responds. LLM-facing schemas must NOT contain ID fields (referencing already-assigned IDs like `domain_id` in LLM output is allowed — that's a reference, not ID generation).
6. **Two-layer schema design.** LLM-facing schemas: only str, int, float, bool, Literal/enum, list, nested models — dates as ISO strings. Domain schemas may use `datetime.date`. NOTE: LLM-facing schemas must not use `Field(min_length=..., max_length=...)` on lists — OpenAI strict mode rejects those constraints; enforce counts in post-validation code instead.
7. **Deterministic scoring.** All numeric scores computed in Python. LLM used ONLY for qualitative diagnosis.
8. **Prompts as versioned constants** in `llm_engine/prompts/` (e.g. `ASSESSMENT_SYSTEM_V1`), never inline in service code.
9. **Env-driven config.** `.env` via python-dotenv; `.env.example` committed; `.env` gitignored from first commit; no API keys anywhere.
10. **Full type hints, docstrings on every public function and model, logging via `logging`** — token usage and `litellm.completion_cost` per call at INFO.

**Resolved contract decision (flag to owner if changing):** the spec's API is `grade_assessment(assessment, answers)` — two args — but `DomainScore` needs `domain_name` and `weight_percent`, which the spec's `Assessment` field list doesn't carry. Resolution: add `domains: list[ExamDomain]` snapshot field to `Assessment` (spec permits adding fields). This keeps the two-arg signature, makes `Assessment` self-contained for the backend, and gives grading its weights.

**Environment note:** repo is at `/Users/akashhp/Developer/AI-generated-courses`, git branch `feature/llm-engine`, zero commits yet. Only `prompt.md`, `llmintegrationplan.md`, and this plan exist. All commands below run from repo root. Use the venv created in Task 1: `.venv/bin/python -m pytest ...`.

---

### Task 1: Scaffold — packaging, config, exceptions

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `llm_engine/__init__.py` (placeholder docstring only; public API filled in Task 8)
- Create: `llm_engine/exceptions.py`
- Create: `llm_engine/config.py`
- Create: `llm_engine/schemas/__init__.py`, `llm_engine/prompts/__init__.py`, `llm_engine/services/__init__.py` (docstring-only placeholders)
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `llm_engine.exceptions.LLMEngineError`, `LLMCallError(LLMEngineError)`, `StructuredOutputError(LLMEngineError)`; `llm_engine.config.get_task_settings(task: TaskName) -> TaskSettings` (fields: `model: str`, `temperature: float`, `timeout: float`, `num_retries: int`, `fallback_models: list[str]`); `get_proficiency_thresholds() -> tuple[float, float]` returning `(weak_below, proficient_at)`; `MAX_VALIDATION_RETRIES = 2`; `TaskName = Literal["syllabus", "assessment", "grading", "roadmap"]`.

[Plan body continues as before in the first document...]

---

**STATUS:** ✅ **COMPLETE**. All 11 tasks executed, 22 tests pass + 1 skipped, 10 commits. No API key needed. Ready to integrate with backend.

**Next:** Set `.env` with `OPENAI_API_KEY` and run `python demo_cli.py --topic "Cloud Architecture" --certification "AWS Solutions Architect Associate SAA-C03" --num-questions 6 --random-answers --json-out artifacts/` to verify live pipeline and generate example JSON payloads for backend teammate.
