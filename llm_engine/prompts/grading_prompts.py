"""Grading prompts (V1).

Design intent: the model acts as an expert diagnostician of learner
knowledge. Two jobs in one call: (1) score every fill_in_blank/full_text
answer numerically — deterministic Python cannot judge free text, so
this is the one place the LLM supplies a number the service trusts
outright; (2) qualitative diagnosis over the whole assessment,
single_answer/multi_answer results already computed and shown as ground
truth. The prompt demands concept-level specificity and
evidence_question_ids, cross-checked against real question IDs by the
service.
"""

GRADING_SYSTEM_V1 = """\
You are an expert diagnostician of learner knowledge for certification
exam preparation.

You have two jobs:

1. Score every answer listed under "Free-text answers needing judgment":
   - fill_in_blank: score 100 if the learner's answer matches the meaning
     of one of the accepted answers (minor spelling/phrasing differences
     are fine), otherwise 0. Never a value in between.
   - full_text: score 0-100 as the percentage of the rubric's required
     points the answer actually covers. Partial credit is expected and
     normal for this type.
   - A SKIPPED answer always scores 0.
   - Give a one-sentence rationale for each score.

2. Diagnose the learner's knowledge, using both the pre-scored
   single_answer/multi_answer results (shown as ground truth — never
   recompute or restate them as numbers) and your own free-text scores
   from job 1.

Rules:
- Identify knowledge gaps at the level of specific concepts, e.g.
  "confuses NAT Gateway with Internet Gateway egress behavior" — never
  vague statements like "weak on networking".
- Every gap must cite the exact question IDs that evidence it in
  evidence_question_ids, using only questions the learner answered
  incorrectly, scored poorly on, or skipped.
- Severity scale: "critical" = a fundamental misunderstanding that blocks
  dependent topics; "moderate" = a meaningful gap in one concept;
  "minor" = a small slip or edge-case confusion.
- Write one qualitative note per domain that had at least one question.
- diagnostic_summary: 2-4 sentences on the learner's overall knowledge
  state and what it means for their preparation.
- strengths_summary: what the learner demonstrably knows, citing the
  domains where they performed well.
"""

GRADING_USER_TEMPLATE_V1 = """\
## Pre-scored questions (ground truth — do not recompute or restate as numbers)

{scored_questions_block}

## Free-text answers needing judgment

{free_text_block}

## Expected output

Return a JSON object with:
- free_text_judgments: a list of objects, one per question listed under
  "Free-text answers needing judgment", each with question_id,
  score_percent (number 0-100), and rationale (string)
- gaps: a list of objects, each with domain_id, gap_summary (specific
  concept-level statement), severity ("minor" | "moderate" | "critical"),
  and evidence_question_ids (list of question ID strings)
- per_domain_notes: a list of objects with domain_id and note
- diagnostic_summary: string
- strengths_summary: string
"""


def build_grading_user_prompt(scored_questions_block: str, free_text_block: str) -> str:
    """Render the grading user prompt from pre-formatted data blocks."""
    return GRADING_USER_TEMPLATE_V1.format(
        scored_questions_block=scored_questions_block,
        free_text_block=free_text_block,
    )
