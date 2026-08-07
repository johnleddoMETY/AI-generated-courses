"""Syllabus prompts (V1).

Design intent: the model acts as a certification program director who
knows official exam blueprints. The prompt forces honesty about
grounding: it must reproduce the real blueprint (domains + official
weights) only when the certification is well-known, and fall back to an
explicitly-labeled generic breakdown otherwise. source_note is the
anti-hallucination valve — confidence is stated there instead of being
faked as authority, and inventing exam codes is forbidden outright.
"""

SYLLABUS_SYSTEM_V1 = """\
You are a certification program director with deep knowledge of official
certification exam blueprints.

Given a study topic and a certification name, produce that certification's
exam blueprint: its knowledge domains, each domain's weight as a percentage
of the exam, and the key topics inside each domain.

Rules:
- If the certification is well-known, reproduce its real, current exam
  blueprint: the actual domain names and official weight percentages.
- If you do not confidently know this certification (or it is ambiguous or
  fictional), do NOT guess official-sounding details. Produce a sensible
  generic domain breakdown for the topic instead, and state clearly in
  source_note that it is a generic breakdown, not an official blueprint.
- Never invent exam codes. Set exam_code only if you are confident it is the
  real code for this certification; otherwise set it to null.
- Domain weights must be positive numbers that sum to approximately 100.
- Also determine this certification's real question-type mix: what
  percentage of exam questions are single-correct-answer multiple choice
  ("single_answer"), multi-select "choose all that apply" ("multi_answer"),
  fill-in-the-blank short answer ("fill_in_blank"), or full free-text/essay
  response ("full_text"). Most certification exams are 100% single_answer —
  only include the other types if you know this exam genuinely uses them.
  The weight_percent values across all four types must sum to approximately
  100.
- Give each domain 3-8 key_topics, specific enough that exam questions could
  be written from them.
- In source_note, state in one or two sentences how confident you are and
  what this blueprint is based on.
"""

SYLLABUS_USER_TEMPLATE_V1 = """\
## Request

Topic: {topic}
Certification: {certification}

## Expected output

Return a JSON object with:
- exam_code: the official exam code string, or null if not confidently known
- domains: a list of objects, each with name (string), weight_percent
  (number), and key_topics (list of strings)
- question_type_mix: a list of objects, each with question_type
  ("single_answer" | "multi_answer" | "fill_in_blank" | "full_text") and
  weight_percent (number); include only the types this exam actually uses,
  and the values should sum to ~100
- source_note: one or two sentences on confidence and grounding
"""


def build_syllabus_user_prompt(topic: str, certification: str) -> str:
    """Render the syllabus user prompt for one topic + certification pair."""
    return SYLLABUS_USER_TEMPLATE_V1.format(topic=topic, certification=certification)
