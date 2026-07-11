"""Grading prompts (V1).

Design intent: the model acts as an expert diagnostician of learner
knowledge, and its role is strictly qualitative — every numeric score is
computed in Python and handed to the model as ground truth. The prompt
demands concept-level specificity ("confuses NAT Gateway with Internet
Gateway egress behavior", never "weak on networking") and requires each
gap to cite evidence_question_ids, which the service cross-checks
against real question IDs.
"""

GRADING_SYSTEM_V1 = """\
You are an expert diagnostician of learner knowledge for certification
exam preparation.

You receive an assessment's questions, the learner's answers, and scores
that were already computed deterministically in code. Your job is purely
qualitative diagnosis. You never compute, correct, or restate numeric
scores — they are provided to you as ground truth context.

Rules:
- Identify knowledge gaps at the level of specific concepts, e.g.
  "confuses NAT Gateway with Internet Gateway egress behavior" — never
  vague statements like "weak on networking".
- Every gap must cite the exact question IDs that evidence it in
  evidence_question_ids, using only questions the learner answered
  incorrectly or skipped.
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
## Questions and learner answers

{questions_block}

## Computed scores (ground truth — do not recompute or restate as numbers)

Overall weighted score: {overall_score_percent}%
{domain_scores_block}

## Expected output

Return a JSON object with:
- gaps: a list of objects, each with domain_id, gap_summary (specific
  concept-level statement), severity ("minor" | "moderate" | "critical"),
  and evidence_question_ids (list of question ID strings)
- per_domain_notes: a list of objects with domain_id and note
- diagnostic_summary: string
- strengths_summary: string
"""


def build_grading_user_prompt(
    questions_block: str,
    domain_scores_block: str,
    overall_score_percent: float,
) -> str:
    """Render the grading user prompt from pre-formatted data blocks."""
    return GRADING_USER_TEMPLATE_V1.format(
        questions_block=questions_block,
        domain_scores_block=domain_scores_block,
        overall_score_percent=overall_score_percent,
    )
