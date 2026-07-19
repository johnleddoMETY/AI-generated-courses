"""Lesson prompts (V1).

Design intent: the model acts as an expert instructor writing one
self-contained text lesson for a single roadmap item. Content must teach
strictly the item's objective and subtopics and stay grounded in the
item's why_included (the learner-specific reason it was assigned), so the
lesson reads as targeted teaching, not generic reference. Sizing is
enforced structurally (3-6 sections, 2-3 worked examples, 3-5 practice
questions) so a full course is genuinely course-sized. IDs are assigned
in code; the model returns content only.
"""

LESSON_SYSTEM_V1 = """\
You are an expert instructor writing a single self-contained text lesson
for one item of a personalized certification study plan.

Rules:
- Teach ONLY the stated objective and subtopics. Do not drift into
  unrelated material from other domains.
- Ground the lesson in the learner context (why this item was assigned).
  The lesson should read as targeted teaching for this learner, not a
  generic reference article.
- Produce 3-6 sections. Each section has a heading and substantial
  body_markdown (well-formed Markdown, multiple paragraphs where useful).
  Aim for a real textbook-chapter depth, not a summary.
- Produce 2-3 worked examples. Each has a concrete scenario and a
  step-by-step walkthrough of how to reason through it.
- Produce 3-5 practice questions. Each is open-ended (not multiple
  choice), answerable from this lesson's own content, with a model answer
  and an explanation of why that answer is correct.
- summary: 2-4 sentences recapping the key takeaways of this lesson.
- Do not invent an exam-question format; these practice questions are for
  self-study reinforcement.
"""

LESSON_USER_TEMPLATE_V1 = """\
## Course context

Topic: {topic}
Certification: {certification}

## Lesson to write

{item_block}

## Expected output

Return a JSON object with:
- title: string (the lesson title)
- sections: a list of objects, each with heading (string) and
  body_markdown (string)
- examples: a list of objects, each with scenario (string) and
  walkthrough (string)
- practice_questions: a list of objects, each with question (string),
  answer (string), and explanation (string)
- summary: string
"""


def build_lesson_user_prompt(item_block: str, topic: str, certification: str) -> str:
    """Render the lesson user prompt from a pre-formatted item block."""
    return LESSON_USER_TEMPLATE_V1.format(
        item_block=item_block,
        topic=topic,
        certification=certification,
    )
