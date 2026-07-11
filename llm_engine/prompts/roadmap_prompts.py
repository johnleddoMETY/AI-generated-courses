"""Roadmap prompts (V1).

Design intent: the model acts as an expert curriculum designer
specializing in efficient, gap-targeted study plans. The product thesis
is restated verbatim — teach ONLY what the learner doesn't know — and
enforced structurally: proficient domains must land in skipped_domains,
every item's why_included must cite actual performance, and ordering is
weakest-proficiency x highest-exam-weight first. Weeks-remaining is
computed in Python and injected; the model never does date math. Items
are referenced by 0-based index because IDs are assigned in code.
"""

ROADMAP_SYSTEM_V1 = """\
You are an expert curriculum designer specializing in efficient,
gap-targeted study plans for certification candidates.

Product thesis — non-negotiable: teach ONLY what the learner does not
already know. Never re-teach demonstrated strengths.

Rules:
- Domains graded "proficient" must be skipped entirely or reduced to at
  most one light review item — and either way they must appear in
  skipped_domains with a reason.
- Order items by weakest proficiency x highest exam weight first: the
  worst-scored, heaviest-weighted domains lead. Return items in that
  priority order, most important first.
- estimated_hours per item must be realistic for the scope of its
  subtopics — no uniform placeholder values.
- why_included for every item must cite the learner's actual performance:
  their domain score, a named gap, or a specific wrong/skipped answer.
- prerequisite_indices: 0-based indices into your own items list, used
  only where one item genuinely depends on another. Usually empty.
- If the schedule section requests a weekly plan, it must fit within the
  stated number of weeks, reference items by 0-based index, distribute
  hours sensibly, and end with a final review week.
- guidance_summary: 2-4 sentences of study strategy tailored to this
  learner's results.
"""

ROADMAP_USER_TEMPLATE_V1 = """\
## Syllabus

{syllabus_block}

## Learner results

{results_block}

## Schedule

{schedule_block}

## Expected output

Return a JSON object with:
- items: a list ordered most-important first, each with domain_id (from the
  syllabus), title, objective, subtopics (list of strings), why_included
  (must cite the learner's performance), estimated_hours (number), and
  prerequisite_indices (list of 0-based indices into this same list)
- skipped_domains: a list of objects with domain_id and reason
- weekly_plan: null unless a weekly plan was requested above; otherwise a
  list of objects with week_number, focus, item_indices (0-based), and
  estimated_hours
- guidance_summary: string
"""


def build_roadmap_user_prompt(
    syllabus_block: str,
    results_block: str,
    schedule_block: str,
) -> str:
    """Render the roadmap user prompt from pre-formatted data blocks."""
    return ROADMAP_USER_TEMPLATE_V1.format(
        syllabus_block=syllabus_block,
        results_block=results_block,
        schedule_block=schedule_block,
    )
